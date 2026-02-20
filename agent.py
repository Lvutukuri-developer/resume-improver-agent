import os
from dotenv import load_dotenv
from openai import OpenAI
from prompts import SYSTEM_PROMPT

# =============================
# 🔐 LOAD ENV VARIABLES
# =============================
# This makes .env work locally
load_dotenv()

# =============================
# 🤖 OPENAI CLIENT
# =============================
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key)


# =============================
# 🧠 RESUME IMPROVER FUNCTION
# =============================
def improve_resume(resume_text: str) -> str:
    """
    Sends resume text to the AI agent and returns improved version.
    """

    response = client.responses.create(
        model="gpt-4o-mini",
        instructions=SYSTEM_PROMPT,
        input=resume_text,
    )

    return response.output_text
