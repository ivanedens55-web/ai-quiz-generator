"""Quiz generation with the Google Gemini API.

This module builds the prompt, calls Gemini, and turns the raw response
into a clean, validated list of questions that the UI can rely on.
"""

import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash"
NUM_OPTIONS = 4


class QuizGenerationError(Exception):
    """Raised when a quiz cannot be generated. The message is safe to show to users."""


def get_client() -> genai.Client:
    """Create a Gemini client using the API key from the environment."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        raise QuizGenerationError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your API key."
        )
    return genai.Client(api_key=api_key)


def build_prompt(topic: str, num_questions: int, difficulty: str) -> str:
    """Build the instruction sent to Gemini."""
    return f"""Create a multiple-choice quiz.

Topic: {topic}
Number of questions: {num_questions}
Difficulty: {difficulty}

Rules:
- Write exactly {num_questions} questions.
- Each question must have exactly {NUM_OPTIONS} distinct answer options.
- Exactly one option is correct.
- "correct_answer" must be copied word-for-word from one of the options.
- "explanation" must be one or two sentences explaining why the answer is correct.
- Do not put letters or numbers (like "A)" or "1.") in front of the options.

Return only JSON in this exact format, with no extra text:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer": "...",
      "explanation": "..."
    }}
  ]
}}"""


def extract_json(text: str) -> dict:
    """Parse JSON from the model's text, tolerating Markdown code fences or extra text."""
    if not text or not text.strip():
        raise QuizGenerationError("The AI returned an empty response. Please try again.")

    cleaned = text.strip()

    # Remove ```json ... ``` fences if the model added them.
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: take everything between the first "{" and the last "}".
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise QuizGenerationError("The AI response was not valid JSON. Please try again.")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            raise QuizGenerationError("The AI response was not valid JSON. Please try again.")

    if not isinstance(data, dict):
        raise QuizGenerationError("The AI response had an unexpected format. Please try again.")
    return data


def _match_correct_answer(correct: str, options: list[str]) -> str | None:
    """Return the option that matches the stated correct answer, or None if none does."""
    # Exact match first.
    if correct in options:
        return correct

    # Case/whitespace-insensitive match.
    normalized = correct.strip().lower()
    for option in options:
        if option.strip().lower() == normalized:
            return option

    # The model sometimes answers with just a letter, e.g. "B" or "B)".
    letter = normalized.rstrip(").:").strip()
    if len(letter) == 1 and letter in "abcd":
        return options["abcd".index(letter)]

    return None


def validate_question(item: object) -> dict | None:
    """Return a cleaned question dict, or None if the item is unusable."""
    if not isinstance(item, dict):
        return None

    question = item.get("question")
    options = item.get("options")
    correct = item.get("correct_answer")
    explanation = item.get("explanation", "")

    if not isinstance(question, str) or not question.strip():
        return None
    if not isinstance(options, list) or len(options) != NUM_OPTIONS:
        return None
    if not all(isinstance(o, str) and o.strip() for o in options):
        return None

    options = [o.strip() for o in options]
    if len(set(o.lower() for o in options)) != NUM_OPTIONS:
        return None  # duplicate options would make the question ambiguous

    if not isinstance(correct, str):
        return None
    matched = _match_correct_answer(correct, options)
    if matched is None:
        return None

    if not isinstance(explanation, str):
        explanation = ""

    return {
        "question": question.strip(),
        "options": options,
        "correct_answer": matched,
        "explanation": explanation.strip() or "No explanation provided.",
    }


def parse_quiz(text: str, num_questions: int) -> list[dict]:
    """Parse and validate the model's response into a list of questions."""
    data = extract_json(text)

    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list):
        raise QuizGenerationError("The AI response did not contain a list of questions.")

    questions = [q for q in (validate_question(item) for item in raw_questions) if q]

    if not questions:
        raise QuizGenerationError(
            "The AI did not return any valid questions. Please try again or rephrase the topic."
        )

    # If the model returned extra questions, keep only the number requested.
    return questions[:num_questions]


def generate_quiz(topic: str, num_questions: int, difficulty: str) -> list[dict]:
    """Generate a validated quiz. Raises QuizGenerationError with a user-friendly message."""
    topic = topic.strip()
    if not topic:
        raise QuizGenerationError("Please enter a topic.")

    client = get_client()
    model = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL

    try:
        response = client.models.generate_content(
            model=model,
            contents=build_prompt(topic, num_questions, difficulty),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
                # We don't use tools, so turn off automatic function calling.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
    except errors.ClientError as e:
        # 4xx errors: bad key, unknown model, quota exceeded, etc.
        if e.code in (401, 403) or "API key" in str(e):
            raise QuizGenerationError("Gemini rejected the API key. Check GEMINI_API_KEY in your .env file.")
        if e.code == 404:
            raise QuizGenerationError(
                f"The model '{model}' was not found. Set GEMINI_MODEL in .env to an available model."
            )
        if e.code == 429:
            raise QuizGenerationError("Gemini rate limit or quota reached. Wait a minute and try again.")
        raise QuizGenerationError(f"Gemini request failed: {e.message or e}")
    except errors.ServerError:
        raise QuizGenerationError("Gemini is temporarily unavailable. Please try again shortly.")
    except errors.APIError as e:
        raise QuizGenerationError(f"Gemini request failed: {e.message or e}")
    except Exception as e:  # network problems, timeouts, etc.
        raise QuizGenerationError(f"Could not reach Gemini: {e}")

    # response.text can be None if the output was blocked by safety filters.
    return parse_quiz(response.text or "", num_questions)
