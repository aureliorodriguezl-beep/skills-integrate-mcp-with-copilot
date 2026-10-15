"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import secrets
import time
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")
teacher_credentials_file = Path(os.getenv(
    "TEACHER_CREDENTIALS_FILE", str(current_dir / "teachers.json")
))
teacher_sessions: dict[str, tuple[str, float]] = {}
session_lifetime_seconds = 8 * 60 * 60
password_hash_iterations = 310_000


class TeacherLogin(BaseModel):
    username: str
    password: str


def get_teacher_credentials():
    try:
        data = json.loads(teacher_credentials_file.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials are not configured",
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials could not be loaded",
        ) from error

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials have an invalid format",
        )
    return data["teachers"]


def require_teacher(authorization: str = Header(default="")) -> dict[str, str]:
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        raise HTTPException(status_code=401, detail="Teacher login required")

    session = teacher_sessions.get(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Teacher session is invalid")

    username, expires_at = session
    if expires_at <= time.time():
        teacher_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Teacher session has expired")

    return {"username": username, "token": token}


@app.post("/auth/login")
def teacher_login(credentials: TeacherLogin):
    if len(credentials.password) > 1024:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    teacher = next(
        (
            entry for entry in get_teacher_credentials()
            if isinstance(entry, dict) and entry.get("username") == credentials.username
        ),
        None,
    )
    if teacher is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    try:
        salt = bytes.fromhex(teacher["salt"])
        expected_hash = teacher["password_hash"]
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            credentials.password.encode("utf-8"),
            salt,
            password_hash_iterations,
        ).hex()
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail="Teacher credentials are invalid")

    if not isinstance(expected_hash, str) or not hmac.compare_digest(actual_hash, expected_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    now = time.time()
    for token, (_, expires_at) in list(teacher_sessions.items()):
        if expires_at <= now:
            teacher_sessions.pop(token, None)

    token = secrets.token_urlsafe(32)
    teacher_sessions[token] = (credentials.username, now + session_lifetime_seconds)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": credentials.username,
    }


@app.post("/auth/logout")
def teacher_logout(session: dict[str, str] = Depends(require_teacher)):
    teacher_sessions.pop(session["token"], None)
    return {"message": "Logged out"}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _: dict[str, str] = Depends(require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: dict[str, str] = Depends(require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
