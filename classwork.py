import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# ---------- Logging (file) ----------
LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"), maxBytes=1_000_000, backupCount=3
)
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
app.logger.setLevel(logging.INFO)
app.logger.addHandler(file_handler)


@app.after_request
def log_request(response):
    app.logger.info("%s %s -> %s", request.method, request.path, response.status_code)
    return response


@app.errorhandler(Exception)
def handle_error(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception("Unhandled error")
    return {"message": "Internal server error"}, 500


# ---------- Data ----------
students = [
    {
        "id": 1,
        "FN": "Ali",
        "LN": "Mastouri",
        "reports": [
            {"title": "Sales Dashboard", "type": "Mini Senior Project"}
        ],
    }
]


# ---------- Routes ----------
@app.get("/students/")  # RETURNS ALL STUDENTS
def get_students():
    return {"students": students}


@app.post("/students/")  # ADDS A NEW STUDENT
def add_student():
    request_data = request.get_json()
    new_student = {
        "id": max((s["id"] for s in students), default=0) + 1,
        "FN": request_data.get("FN"),
        "LN": request_data.get("LN"),
        "reports": request_data.get("reports", []),
    }
    students.append(new_student)
    return {"message": "Student added successfully", "student": new_student}, 201


@app.post("/student/<int:student_id>/report")  # ADDS A REPORT TO A STUDENT
def add_report(student_id):
    request_data = request.get_json()
    student = next((s for s in students if s["id"] == student_id), None)
    if student is None:
        return {"message": "Student not found"}, 404
    new_report = {
        "title": request_data.get("title"),
        "type": request_data.get("type"),
    }
    student["reports"].append(new_report)
    return {"message": "Report added successfully", "report": new_report}, 201


@app.get("/student/<int:student_id>")  # RETURNS ONE STUDENT
def get_student(student_id):
    for student in students:
        if student["id"] == student_id:
            return {"student": student}
    return {"message": "Student not found"}, 404


@app.get("/student/<int:student_id>/report")  # RETURNS A STUDENT'S REPORTS
def get_student_reports(student_id):
    student = next((s for s in students if s["id"] == student_id), None)
    if student is None:
        return {"message": "Student not found"}, 404
    return {"reports": student["reports"]}


# ---------- Start ----------
if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )