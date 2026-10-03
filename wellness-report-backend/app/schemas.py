from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Fixed option lists. The frontend gets these from GET /api/meta/options,
# so to add a trait or personality type you only change it here.
# ---------------------------------------------------------------------------
NATURE_TRAITS = [
    "Respectful", "Helpful", "Curious Learner", "Responsible", "Independent",
    "Friendly", "Disciplined", "Positive Attitude", "Creative", "Polite",
    "Calm", "Punctual", "Hardworking", "Cooperative", "Honest",
]

WELLNESS_LABELS = {
    "confidence": "Confidence",
    "communication": "Communication",
    "teamwork": "Teamwork",
    "leadership": "Leadership",
    "creativity": "Creativity",
    "responsibility": "Responsibility",
    "emotional_wellbeing": "Emotional Wellbeing",
}

# The AI must pick exactly one of these, so badges stay consistent across students.
# Each type lists the wellness areas and traits that point to it. The server scores
# every type against the student's input and lets the AI choose only among the best fits.
PERSONALITY_SIGNALS = {
    "Future Leader":          (["leadership", "confidence", "responsibility"], ["Responsible", "Independent", "Disciplined"]),
    "Creative Thinker":       (["creativity"], ["Creative", "Curious Learner"]),
    "Curious Explorer":       (["creativity", "confidence"], ["Curious Learner", "Independent"]),
    "Kind Helper":            (["emotional_wellbeing", "teamwork"], ["Helpful", "Polite", "Respectful", "Friendly"]),
    "Team Player":            (["teamwork", "communication"], ["Cooperative", "Friendly", "Helpful"]),
    "Confident Communicator": (["communication", "confidence"], ["Friendly", "Positive Attitude"]),
    "Disciplined Achiever":   (["responsibility"], ["Disciplined", "Hardworking", "Punctual", "Responsible"]),
    "Calm Thinker":           (["emotional_wellbeing"], ["Calm", "Honest", "Polite"]),
}
PERSONALITY_TYPES = list(PERSONALITY_SIGNALS)

Rating = Annotated[int, Field(ge=1, le=5)]


class CleanModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---------------------------- Teacher input --------------------------------
class StudentDetails(CleanModel):
    school_name: str = Field(min_length=2, max_length=100, examples=["Bright Future International School"])
    name: str = Field(min_length=2, max_length=80, examples=["Aarav Sharma"])
    gender: Literal["male", "female", "other"]  # used only for he/she/they in AI text
    class_name: str = Field(min_length=1, max_length=20, examples=["Grade 4 - A"])
    academic_year: str = Field(pattern=r"^\d{4}-\d{2}$", examples=["2024-25"])
    roll_number: str = Field(min_length=1, max_length=10, examples=["12"])


class WellnessProfile(CleanModel):
    confidence: Rating
    communication: Rating
    teamwork: Rating
    leadership: Rating
    creativity: Rating
    responsibility: Rating
    emotional_wellbeing: Rating


class TeacherInput(CleanModel):
    student: StudentDetails
    nature_traits: list[str] = Field(min_length=3, max_length=8)
    wellness: WellnessProfile
    teacher_observation: str = Field(min_length=30, max_length=800)

    @field_validator("nature_traits")
    @classmethod
    def check_traits(cls, v: list[str]) -> list[str]:
        unknown = [t for t in v if t not in NATURE_TRAITS]
        if unknown:
            raise ValueError(f"Unknown traits: {unknown}")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate traits are not allowed")
        return v


# ------------------------------ AI output ----------------------------------
class StrongZone(CleanModel):
    title: str = Field(min_length=2, max_length=30)
    description: str = Field(min_length=5, max_length=90)


class AIReport(CleanModel):
    personality_type: str
    personality_description: str = Field(min_length=40, max_length=450)
    strong_zones: list[StrongZone] = Field(min_length=3, max_length=3)
    hidden_potential: str = Field(min_length=40, max_length=450)
    growth_recommendations: list[Annotated[str, Field(min_length=5, max_length=80)]] = Field(
        min_length=3, max_length=3
    )
    final_conclusion: str = Field(min_length=40, max_length=350)

    @field_validator("personality_type")
    @classmethod
    def check_type(cls, v: str) -> str:
        if v not in PERSONALITY_TYPES:
            raise ValueError(f"personality_type must be one of {PERSONALITY_TYPES}")
        return v


# ------------------------------ API output ---------------------------------
class ReportOut(BaseModel):
    id: int
    status: Literal["draft", "generated", "failed"]
    teacher_input: TeacherInput
    ai_output: AIReport | None
    photo_url: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
