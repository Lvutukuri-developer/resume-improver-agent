import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key, timeout=45.0)


def _normalize_resume_data(data):
    """Keep the UI from breaking if the model returns a slightly different shape."""
    if not isinstance(data, dict):
        raise ValueError("The AI response was not a JSON object.")

    experience = data.get("experience") or []
    if isinstance(experience, dict):
        experience = [experience]
    elif not isinstance(experience, list):
        experience = []

    normalized_jobs = []
    for job in experience:
        if isinstance(job, dict):
            normalized_jobs.append({
                "title": str(job.get("title") or ""),
                "company": str(job.get("company") or ""),
                "dates": str(job.get("dates") or ""),
                "desc": str(job.get("desc") or job.get("description") or ""),
            })
        else:
            normalized_jobs.append({
                "title": "",
                "company": "",
                "dates": "",
                "desc": str(job),
            })

    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [skill.strip() for skill in skills.split(",") if skill.strip()]
    elif not isinstance(skills, list):
        skills = []

    return {
        "name": str(data.get("name") or "Resume"),
        "contact": str(data.get("contact") or ""),
        "summary": str(data.get("summary") or ""),
        "experience": normalized_jobs,
        "skills": [str(skill) for skill in skills],
    }

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
                "content": "You are a world-class resume optimizer. Preserve truthful identity details from the resume, including name, contact information, job titles, companies, and dates when present. Rewrite only the professional summary, experience descriptions, and skills into stronger resume language. Return ONLY a JSON object with these keys: name, contact, summary, experience (list of objects with title, company, dates, desc), and skills (list of strings)."
            },
            {"role": "user", "content": resume_text}
        ],
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("The AI response was empty.")

    return _normalize_resume_data(json.loads(content))
