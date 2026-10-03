import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Path as PathParam, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config, storage
from .ai_service import AIGenerationError, generate_ai_report
from .database import Base, engine, get_db
from .models import Report
from .schemas import (
    NATURE_TRAITS, PERSONALITY_TYPES, WELLNESS_LABELS, AIReport, ReportOut, TeacherInput,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wellness & Personality Report API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=config.FRONTEND_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _to_out(r: Report) -> ReportOut:
    return ReportOut.model_validate({
        "id": r.id,
        "status": r.status,
        "teacher_input": r.teacher_input,
        "ai_output": r.ai_output,
        "photo_url": f"/media/{r.photo_path}" if r.photo_path else None,
        "error": r.error,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    })


def _get_report(db: Session, report_id: int) -> Report:
    r = db.get(Report, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


def _apply_input(r: Report, data: TeacherInput) -> None:
    r.student_name = data.student.name
    r.class_name = data.student.class_name
    r.academic_year = data.student.academic_year
    r.roll_number = data.student.roll_number
    r.teacher_input = data.model_dump()


@app.get("/api/meta/options")
def get_options():
    """Lists the frontend uses to build the teacher form."""
    return {
        "nature_traits": NATURE_TRAITS,
        "wellness_categories": [{"key": k, "label": v} for k, v in WELLNESS_LABELS.items()],
        "personality_types": PERSONALITY_TYPES,
    }


@app.post("/api/reports", response_model=ReportOut, status_code=201)
def create_report(data: TeacherInput, db: Session = Depends(get_db)):
    r = Report(status="draft")
    _apply_input(r, data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_out(r)


@app.get("/api/reports", response_model=list[ReportOut])
def list_reports(class_name: str | None = None, academic_year: str | None = None,
                 db: Session = Depends(get_db)):
    q = select(Report).order_by(Report.class_name, Report.roll_number)
    if class_name:
        q = q.where(Report.class_name == class_name)
    if academic_year:
        q = q.where(Report.academic_year == academic_year)
    return [_to_out(r) for r in db.scalars(q)]


@app.get("/api/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    return _to_out(_get_report(db, report_id))


@app.put("/api/reports/{report_id}", response_model=ReportOut)
def update_report(report_id: int, data: TeacherInput, db: Session = Depends(get_db)):
    """Teacher edits their input. The old AI text no longer matches, so it is cleared."""
    r = _get_report(db, report_id)
    _apply_input(r, data)
    r.ai_output, r.status, r.error = None, "draft", None
    db.commit()
    db.refresh(r)
    return _to_out(r)


@app.post("/api/reports/{report_id}/photo", response_model=ReportOut)
def upload_photo(report_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status_code=415, detail="Photo must be JPEG, PNG or WebP")
    content = file.file.read(config.MAX_PHOTO_BYTES + 1)
    if len(content) > config.MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo must be 2 MB or smaller")

    r = _get_report(db, report_id)
    filename = f"{report_id}_{uuid.uuid4().hex}{ext}"
    try:
        storage.upload(filename, content, file.content_type)
    except storage.StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if r.photo_path:
        storage.delete(r.photo_path)
    r.photo_path = filename
    db.commit()
    db.refresh(r)
    return _to_out(r)


@app.post("/api/reports/{report_id}/generate", response_model=ReportOut)
def generate_report(report_id: int, db: Session = Depends(get_db)):
    """Calls the AI. Takes roughly 5-20 seconds."""
    r = _get_report(db, report_id)
    data = TeacherInput.model_validate(r.teacher_input)
    try:
        ai = generate_ai_report(data)
    except AIGenerationError as e:
        r.status, r.error = "failed", str(e)
        db.commit()
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")

    r.ai_output, r.status, r.error = ai.model_dump(), "generated", None
    db.commit()
    db.refresh(r)
    return _to_out(r)


@app.put("/api/reports/{report_id}/ai-output", response_model=ReportOut)
def edit_ai_output(report_id: int, data: AIReport, db: Session = Depends(get_db)):
    """Teacher reviews and corrects the AI-written sections before finalising."""
    r = _get_report(db, report_id)
    if r.ai_output is None:
        raise HTTPException(status_code=409, detail="Generate the report before editing it")
    r.ai_output = data.model_dump()
    db.commit()
    db.refresh(r)
    return _to_out(r)


@app.delete("/api/reports/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    r = _get_report(db, report_id)
    if r.photo_path:
        storage.delete(r.photo_path)
    db.delete(r)
    db.commit()


@app.get("/media/{filename}")
def get_photo(filename: str = PathParam(pattern=r"^\d+_[0-9a-f]{32}\.(jpg|png|webp)$")):
    """Streams a student photo out of the private storage bucket."""
    try:
        photo = storage.download(filename)
    except storage.StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    content, content_type = photo
    # Each upload gets a new file name, so browsers may keep a photo for a day
    return Response(content, media_type=content_type, headers={"Cache-Control": "private, max-age=86400"})


# Serves the web pages (index.html, new.html, report.html). Must stay the LAST line,
# otherwise it would catch the /api routes above.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
