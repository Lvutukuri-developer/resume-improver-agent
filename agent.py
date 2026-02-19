import os
from dotenv import load_dotenv
from openai import OpenAI
from prompts import SYSTEM_PROMPT

# 🔥 Force-load .env from this folder (Windows-safe)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

# Create OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
