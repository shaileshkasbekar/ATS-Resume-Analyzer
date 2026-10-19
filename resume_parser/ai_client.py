import os
import re
import json

from dotenv import load_dotenv
from groq import Groq


# -----------------------------------------
# Load environment variables
# -----------------------------------------

load_dotenv()

MODEL = "openai/gpt-oss-20b"

api_key = os.getenv("GROQ_API_KEY")


# The app still runs without a key;
# AI analysis is simply skipped.

client = Groq(api_key=api_key) if api_key else None


if not client:

    print("WARNING: GROQ_API_KEY not found in .env. AI analysis disabled.")


# -----------------------------------------
# Ask the AI and get JSON back
# -----------------------------------------

def ask_ai_for_json(system_message, prompt):
    """
    Returns the AI response as a dict,
    or None if the AI is unavailable or fails.
    """

    if not client:

        return None

    try:

        response = client.chat.completions.create(

            model=MODEL,

            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],

            temperature=0.1,

            timeout=60
        )

        ai_text = response.choices[0].message.content or ""

    except Exception as e:

        print("AI Request Error:", e)

        return None

    # Remove ```json ... ``` fences if the model adds them

    ai_text = re.sub(r"^\s*```(?:json)?|```\s*$", "", ai_text.strip())

    try:

        result = json.loads(ai_text)

    except json.JSONDecodeError:

        print("AI returned invalid JSON:")
        print(ai_text)

        return None

    if not isinstance(result, dict):

        return None

    return result


# -----------------------------------------
# Read a 0-100 score from the AI result
# -----------------------------------------

def get_score(ai_result, key):
    """
    Handles values like 85, "85", "85%" or missing keys.
    """

    value = ai_result.get(key, 0)

    try:

        score = float(str(value).replace("%", "").strip())

    except ValueError:

        score = 0

    return min(max(score, 0), 100)
