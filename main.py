
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4

app = FastAPI(
    title="Placement Hub",
    description="Evidence-based student placement platform",
    version="1.0.0"
)

# Temporary in-memory storage
students = {}
jobs = {}
applications = {}


# ---------- DATA MODELS ----------

class Student(BaseModel):
    name: str
    email: str
    degree: str
    graduation_year: int
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    github_url: Optional[str] = None


class Job(BaseModel):
    company: str
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    location: str = "Not specified"
    job_type: str = "Full-time"


class Application(BaseModel):
    student_id: str
    job_id: str
    status: str = "Applied"


# ---------- HOME ----------

@app.get("/")
def home():
    return {
        "message": "Welcome to Placement Hub API",
        "status": "running",
        "docs": "/docs"
    }


# ---------- STUDENT PROFILES ----------

@app.post("/students")
def create_student(student: Student):
    student_id = str(uuid4())

    students[student_id] = {
        "id": student_id,
        **student.model_dump(),
        "evidence": []
    }

    return {
        "message": "Student profile created",
        "student": students[student_id]
    }


@app.get("/students")
def get_students():
    return list(students.values())


@app.get("/students/{student_id}")
def get_student(student_id: str):
    if student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")
    return students[student_id]


@app.put("/students/{student_id}/evidence")
def add_evidence(student_id: str, evidence: dict):
    if student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")

    skill = evidence.get("skill")
    proof = evidence.get("proof")
    source = evidence.get("source", "Project")

    if not skill or not proof:
        raise HTTPException(
            status_code=400,
            detail="Provide both skill and proof"
        )

    record = {
        "skill": skill,
        "proof": proof,
        "source": source
    }

    students[student_id]["evidence"].append(record)

    if skill not in students[student_id]["skills"]:
        students[student_id]["skills"].append(skill)

    return {
        "message": "Evidence added",
        "evidence": record
    }


# ---------- JOB POSTINGS ----------

@app.post("/jobs")
def create_job(job: Job):
    job_id = str(uuid4())

    jobs[job_id] = {
        "id": job_id,
        **job.model_dump()
    }

    return {
        "message": "Job created",
        "job": jobs[job_id]
    }


@app.get("/jobs")
def get_jobs():
    return list(jobs.values())


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


# ---------- JOB MATCHING ----------

@app.get("/students/{student_id}/matches")
def get_matches(student_id: str):
    if student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")

    student = students[student_id]
    student_skills = {s.lower() for s in student["skills"]}
    evidence_skills = {
        item["skill"].lower() for item in student["evidence"]
    }

    results = []

    for job in jobs.values():
        required = {
            s.lower() for s in job["required_skills"]
        }
        preferred = {
            s.lower() for s in job["preferred_skills"]
        }

        matched_required = required & student_skills
        matched_preferred = preferred & student_skills
        missing_required = required - student_skills

        required_score = (
            len(matched_required) / len(required) * 70
            if required else 70
        )
        preferred_score = (
            len(matched_preferred) / len(preferred) * 20
            if preferred else 20
        )
        evidence_score = (
            len(matched_required & evidence_skills)
            / len(required) * 10
            if required else 10
        )

        score = round(
            min(100, required_score + preferred_score + evidence_score),
            2
        )

        results.append({
            "job_id": job["id"],
            "company": job["company"],
            "title": job["title"],
            "match_score": score,
            "matched_required_skills": sorted(matched_required),
            "matched_preferred_skills": sorted(matched_preferred),
            "missing_required_skills": sorted(missing_required),
            "explanation": (
                f"You match {len(matched_required)} of "
                f"{len(required)} required skills. "
                f"{len(missing_required)} required skills are missing."
            )
        })

    return sorted(
        results,
        key=lambda item: item["match_score"],
        reverse=True
    )


# ---------- APPLICATION TRACKER ----------

@app.post("/applications")
def create_application(application: Application):
    if application.student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")

    if application.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    application_id = str(uuid4())

    applications[application_id] = {
        "id": application_id,
        **application.model_dump()
    }

    return {
        "message": "Application created",
        "application": applications[application_id]
    }


@app.get("/applications")
def get_applications():
    return list(applications.values())


@app.patch("/applications/{application_id}")
def update_application(application_id: str, status: str):
    if application_id not in applications:
        raise HTTPException(status_code=404, detail="Application not found")

    allowed_statuses = [
        "Applied",
        "Assessment",
        "Interview",
        "Offer",
        "Rejected"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {allowed_statuses}"
        )

    applications[application_id]["status"] = status

    return {
        "message": "Application status updated",
        "application": applications[application_id]
    }


# ---------- BATCH RANKING ----------

@app.get("/jobs/{job_id}/rank-students")
def rank_students(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    required = {s.lower() for s in job["required_skills"]}
    preferred = {s.lower() for s in job["preferred_skills"]}

    rankings = []

    for student in students.values():
        skills = {s.lower() for s in student["skills"]}
        matched_required = skills & required
        matched_preferred = skills & preferred
        missing = required - skills

        required_score = (
            len(matched_required) / len(required) * 70
            if required else 70
        )
        preferred_score = (
            len(matched_preferred) / len(preferred) * 20
            if preferred else 20
        )

        score = round(
            min(100, required_score + preferred_score), 2
        )

        rankings.append({
            "student_id": student["id"],
            "name": student["name"],
            "degree": student["degree"],
            "match_score": score,
            "matched_skills": sorted(matched_required),
            "missing_skills": sorted(missing)
        })

    return sorted(
        rankings,
        key=lambda item: item["match_score"],
        reverse=True
    )


# ---------- RESUME GENERATOR ----------

@app.get("/students/{student_id}/resume")
def generate_resume(student_id: str):
    if student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")

    student = students[student_id]

    verified_skills = sorted({
        item["skill"] for item in student["evidence"]
    })

    return {
        "name": student["name"],
        "email": student["email"],
        "degree": student["degree"],
        "graduation_year": student["graduation_year"],
        "skills": student["skills"],
        "verified_skills": verified_skills,
        "projects": student["projects"],
        "github_url": student["github_url"],
        "note": (
            "Only list achievements you can substantiate. "
            "Verified skills are linked to submitted evidence."
        )
    }
