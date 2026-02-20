import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key)

def improve_resume(resume_text: str):
    """
    Analyzes resume text and returns a structured JSON object for templating.
    """
    # Using the new response_format to guarantee valid JSON
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are a world-class resume optimizer. Rewrite the provided text into a high-impact, professional resume. Return ONLY a JSON object with these keys: name, contact, summary, experience (list of objects with title, company, dates, desc), and skills (list of strings)."
            },
            {"role": "user", "content": resume_text}
        ],
        response_format={"type": "json_object"}
    )

    # Parse the JSON string from the AI response
    return json.loads(response.choices[0].message.content)