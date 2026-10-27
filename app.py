from flask import Flask, jsonify, request
from functools import wraps
import datetime
import jwt

app = Flask(__name__)

import os

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
ACCESS_MINUTES = int(os.getenv("ACCESS_MINUTES", "2"))
REFRESH_MINUTES = int(os.getenv("REFRESH_MINUTES", "10"))
USERS = [["rahma", "1234"]]       

MAX_STUDENTS_PER_REPORT = 2       # a report is written by 1 to 2 students


class Student:
    # Each student writes exactly one report (1,1) -> the student holds id_r
    def __init__(self, id_s, fn, ln, level, id_r, degree=None):
        self.id_s = id_s
        self.fn = fn
        self.ln = ln
        self.degree = degree      # [0,1] -> optional, can be None
        self.level = level
        self.id_r = id_r          # the report this student writes

    def to_list(self):
        return [self.id_s, self.fn, self.ln, self.degree, self.level, self.id_r]

class Report:
    # allowed values for the type attribute
    REPORT_TYPES = ["Mini Senior Project", "PhD Thesis", "Internship", "Master's Thesis"]

    def __init__(self, id_r, title, type, k1, k2, k3, report_date):
        if type not in Report.REPORT_TYPES:
            raise ValueError("Invalid type. Allowed: " + ", ".join(Report.REPORT_TYPES))
        self.id_r = id_r
        self.title = title
        self.type = type
        self.k1 = k1
        self.k2 = k2
        self.k3 = k3
        self.report_date = report_date

    def to_list(self):
        return [self.id_r, self.title, self.type, self.k1, self.k2,
                self.k3, self.report_date]


# List 1: students  (id_s, fn, ln, level, id_r, degree)
students = [
    Student(1, "Rahma", "Haddouchi", "Senior", 1),
    Student(2, "Maycem", "Azaza", "Senior", 1),                   
    Student(3, "Moemen", "Gharbi", "Senior", 2, "Bachelor"),
    Student(4, "Sara", "Trabelsi", "Master", 3, "Bachelor"),
    Student(5, "Yassine", "Ben Ali", "PhD", 4, "Master"),
]

# List 2: reports  (id_r, title, type, k1, k2, k3, report_date)
reports = [
    Report(1, "Sales Dashboard", "Mini Senior Project", "sales", "analytics", "dashboard", "2026-10-10"),
    Report(2, "Network Security Audit", "Internship", "firewall", "network", "security", "2026-10-12"),
    Report(3, "Credit Risk Models", "Master's Thesis", "credit", "risk", "machine learning", "2026-10-14"),
    Report(4, "Oil Shocks and Growth", "PhD Thesis", "oil", "panel data", "econometrics", "2026-10-16"),
]

# Increment: the next id is the current counter, then +1
next_student_id = 6
next_report_id = 5


# ---------- Error handling ----------
def error(msg, code):
    print("[ERROR " + str(code) + "] " + msg)      # message shown in the console
    return jsonify([msg]), code

def get_list(expected_length):
    """Reads the JSON body and checks it is a list with the right length.
    Returns (data, None) if OK, or (None, error_response) if not."""
    data = request.get_json(silent=True)           # None if the JSON is broken
    if data is None:
        return None, error("Body is missing or is not valid JSON", 400)
    if not isinstance(data, list):
        return None, error("JSON must be a list, e.g. [\"a\", \"b\"]", 400)
    if isinstance(expected_length, tuple):
        ok = len(data) in expected_length
    else:
        ok = len(data) == expected_length
    if not ok:
        return None, error("Wrong number of values: expected " + str(expected_length)
                           + ", received " + str(len(data)), 400)
    for value in data:
        if value is None or value == "":
            return None, error("Empty values are not allowed", 400)
    return data, None

def find_report(id_r):
    for r in reports:
        if r.id_r == id_r:
            return r
    return None

def count_students_of_report(id_r):
    count = 0
    for s in students:
        if s.id_r == id_r:
            count += 1
    return count


# ---------- Token ----------
def make_token(username, token_type, minutes):
    payload = {
        "sub": username,
        "type": token_type,
        "exp": datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(minutes=minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def check_token(expected_type):
    """Returns (username, None) if the token is valid, or (None, error_response)."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, error("Token missing (Authorization: Bearer <token>)", 401)
    token = header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None, error("Token expired", 401)
    except jwt.InvalidTokenError:
        return None, error("Invalid token", 401)
    if payload.get("type") != expected_type:
        return None, error("Wrong token type: a " + expected_type + " token is required", 401)
    return payload.get("sub"), None

def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username, err = check_token("access")
        if err:
            return err
        return f(*args, **kwargs)
    return wrapper


# ---------- Login and refresh ----------
@app.route("/login", methods=["POST"])
def login():
    data, err = get_list(2)                        # [username, password]
    if err:
        return err
    if [data[0], data[1]] not in USERS:
        return error("Wrong username or password", 401)
    return jsonify([make_token(data[0], "access", ACCESS_MINUTES),
                    make_token(data[0], "refresh", REFRESH_MINUTES)])
    # response: [access_token, refresh_token]

@app.route("/refresh", methods=["POST"])
def refresh():
    username, err = check_token("refresh")         # send the REFRESH token here
    if err:
        return err
    return jsonify([make_token(username, "access", ACCESS_MINUTES)])


# ---------- Students: GET all + GET one (token required) + POST ----------
@app.route("/students", methods=["GET"])
@token_required
def get_students():
    result = []
    for s in students:
        result.append(s.to_list())
    return jsonify(result)

@app.route("/students/<int:id_s>", methods=["GET"])
@token_required
def get_student(id_s):
    for s in students:
        if s.id_s == id_s:
            return jsonify(s.to_list())
    return error("Student " + str(id_s) + " not found", 404)

@app.route("/students", methods=["POST"])
def add_student():
    global next_student_id
    # [fn, ln, level, id_r]  or  [fn, ln, level, degree, id_r]   (id_r is always last)
    data, err = get_list((4, 5))
    if err:
        return err
    id_r = data[-1]
    degree = data[3] if len(data) == 5 else None
    if not isinstance(id_r, int):
        return error("id_r must be a number", 400)
    if find_report(id_r) is None:
        return error("Report " + str(id_r) + " does not exist", 404)
    if count_students_of_report(id_r) >= MAX_STUDENTS_PER_REPORT:
        return error("Report " + str(id_r) + " already has "
                     + str(MAX_STUDENTS_PER_REPORT) + " students (maximum)", 400)
    student = Student(next_student_id, data[0], data[1], data[2], id_r, degree)
    students.append(student)
    next_student_id += 1
    return jsonify(student.to_list()), 201


# ---------- Reports: GET all + GET one (no token) + POST ----------
@app.route("/reports", methods=["GET"])
def get_reports():
    result = []
    for r in reports:
        result.append(r.to_list())
    return jsonify(result)

@app.route("/reports/<int:id_r>", methods=["GET"])
def get_report(id_r):
    r = find_report(id_r)
    if r is None:
        return error("Report " + str(id_r) + " not found", 404)
    return jsonify(r.to_list())

@app.route("/reports", methods=["POST"])
def add_report():
    global next_report_id
    data, err = get_list(6)            # [title, type, k1, k2, k3, report_date]
    if err:
        return err
    try:
        datetime.datetime.strptime(data[5], "%Y-%m-%d")
    except (ValueError, TypeError):
        return error("report_date must have the format YYYY-MM-DD", 400)
    try:
        report = Report(next_report_id, data[0], data[1], data[2],
                        data[3], data[4], data[5])
    except ValueError as e:            # raised by the Report class if type is invalid
        return error(str(e), 400)
    reports.append(report)
    next_report_id += 1
    return jsonify(report.to_list()), 201


if __name__ == "__main__":
    app.run(debug=True)