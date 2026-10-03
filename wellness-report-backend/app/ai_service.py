import json

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from . import config
from .schemas import PERSONALITY_SIGNALS, WELLNESS_LABELS, AIReport, TeacherInput


class AIGenerationError(Exception):
    pass


PRONOUNS = {"male": "he / him / his", "female": "she / her", "other": "they / them / their"}

SYSTEM_PROMPT = f"""You write warm, encouraging wellness and personality reports that schools send to parents.

Rules:
- Use ONLY the information provided. Do not invent achievements, competitions, marks or activities.
- Be positive and constructive. Never negative, never diagnostic, never mention medical or psychological conditions.
- Simple English that any parent can understand. Refer to the student by first name and the given pronouns.
- personality_type MUST be one of "best_fit_types". They are ranked by how well they match the
  ratings and traits. Take the first one unless the teacher's observation clearly fits another one in that list better.
- Describe the student through their own traits and ratings, so two students never read the same.
  Do not call a student a leader unless leadership is one of their highest-rated areas.
- Strong zones must come from "highest_rated_areas", the selected traits and the teacher's observation.
- Growth recommendations must target "areas_to_grow" when it is not empty.
- Hidden potential should point to an emerging talent the inputs suggest, phrased as "with the right guidance...".
- The teacher's observation may be short, informal or not in English. Use only what it says about the student;
  if it says nothing useful, rely on the ratings and traits alone.

Return ONLY a JSON object, no markdown, no extra text, with exactly these keys:
{{
  "personality_type": one of the given "best_fit_types",
  "personality_description": "40-60 words describing why this type fits",
  "strong_zones": [{{"title": "1-3 words", "description": "max 12 words"}}, ... exactly 3, strongest first],
  "hidden_potential": "40-60 words",
  "growth_recommendations": ["max 10 words, actionable", ... exactly 3],
  "final_conclusion": "30-50 words summarising the student's strengths and future"
}}"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise AIGenerationError("GEMINI_API_KEY is not set on the server")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def best_fit_types(data: TeacherInput, n: int = 3) -> list[str]:
    """Ranks personality types by the student's ratings and traits, best first.
    Without this the AI picked "Future Leader" for almost every student."""
    ratings = data.wellness.model_dump()

    def score(t: str) -> float:
        areas, traits = PERSONALITY_SIGNALS[t]
        avg_rating = sum(ratings[a] for a in areas) / len(areas)
        return avg_rating + 1.5 * sum(tr in data.nature_traits for tr in traits)

    return sorted(PERSONALITY_SIGNALS, key=score, reverse=True)[:n]


def build_user_prompt(data: TeacherInput, candidates: list[str]) -> str:
    ratings = {WELLNESS_LABELS[k]: v for k, v in data.wellness.model_dump().items()}
    # Include ties, so a 5-star area isn't dropped just because of the order of the fields
    third_best = sorted(ratings.values(), reverse=True)[2]
    top_areas = [label for label, v in ratings.items() if v >= third_best]
    to_grow = [label for label, v in ratings.items() if v <= 3]

    # Only first name + class are sent: roll number and surname are not needed by the AI
    payload = {
        "first_name": data.student.name.split()[0],
        "pronouns": PRONOUNS[data.student.gender],
        "class": data.student.class_name,
        "nature_traits": data.nature_traits,
        "wellness_ratings_out_of_5": ratings,
        "highest_rated_areas": top_areas,
        "areas_to_grow": to_grow,
        "best_fit_types": candidates,
        "teacher_observation": data.teacher_observation,
    }
    return "Write the report sections for this student:\n" + json.dumps(payload, indent=2)


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in AI response")
    return text[start : end + 1]


def _content(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def generate_ai_report(data: TeacherInput) -> AIReport:
    client = _get_client()
    candidates = best_fit_types(data)
    contents = [_content("user", build_user_prompt(data, candidates))]
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",  # Gemini returns plain JSON, no markdown
        temperature=0.7,
    )
    last_error: Exception | None = None

    for _ in range(2):  # first try + one correction attempt
        try:
            resp = client.models.generate_content(
                model=config.AI_MODEL, contents=contents, config=gen_config
            )
        except errors.APIError as e:
            raise AIGenerationError(f"AI service error: {e}") from e

        text = resp.text or ""
        try:
            report = AIReport.model_validate_json(_extract_json(text))
            if report.personality_type not in candidates:
                raise ValueError(f"personality_type must be one of {candidates}")
            return report
        except (ValueError, ValidationError) as e:
            last_error = e
            contents += [
                _content("model", text),
                _content("user", f"That output was invalid: {e}\nReturn only the corrected JSON."),
            ]

    raise AIGenerationError(f"AI returned invalid output twice: {last_error}")
