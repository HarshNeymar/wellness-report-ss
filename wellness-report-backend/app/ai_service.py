import json

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from . import config
from .schemas import PERSONALITY_TYPES, WELLNESS_LABELS, AIReport, TeacherInput


class AIGenerationError(Exception):
    pass


PRONOUNS = {"male": "he / him / his", "female": "she / her", "other": "they / them / their"}

SYSTEM_PROMPT = f"""You write warm, encouraging wellness and personality reports that schools send to parents.

Rules:
- Use ONLY the information provided. Do not invent achievements, competitions, marks or activities.
- Be positive and constructive. Never negative, never diagnostic, never mention medical or psychological conditions.
- Simple English that any parent can understand. Refer to the student by first name and the given pronouns.
- Strong zones must come from the highest-rated wellness areas, the selected traits and the teacher's observation.
- Hidden potential should point to an emerging talent the inputs suggest, phrased as "with the right guidance...".

Return ONLY a JSON object, no markdown, no extra text, with exactly these keys:
{{
  "personality_type": one of {json.dumps(PERSONALITY_TYPES)},
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


def build_user_prompt(data: TeacherInput) -> str:
    ratings = {WELLNESS_LABELS[k]: v for k, v in data.wellness.model_dump().items()}
    top_areas = [label for label, _ in sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)[:3]]

    # Only first name + class are sent: roll number and surname are not needed by the AI
    payload = {
        "first_name": data.student.name.split()[0],
        "pronouns": PRONOUNS[data.student.gender],
        "class": data.student.class_name,
        "nature_traits": data.nature_traits,
        "wellness_ratings_out_of_5": ratings,
        "highest_rated_areas": top_areas,
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
    contents = [_content("user", build_user_prompt(data))]
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
            return AIReport.model_validate_json(_extract_json(text))
        except (ValueError, ValidationError) as e:
            last_error = e
            contents += [
                _content("model", text),
                _content("user", f"That output was invalid: {e}\nReturn only the corrected JSON."),
            ]

    raise AIGenerationError(f"AI returned invalid output twice: {last_error}")
