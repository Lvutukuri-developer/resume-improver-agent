import os
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader
import markdown

# Load environment variables
load_dotenv()

app = Flask(__name__)

# =========================
# 📄 Helper: Extract PDF text
# =========================
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception:
        return ""

# =========================
# 🎨 FLAGSHIP HTML TEMPLATE
# =========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Resume Improver</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(180deg, #f9fafb 0%, #eef2ff 100%);
            margin: 0;
            padding: 40px 20px;
            color: #111827;
        }

        .container {
            max-width: 900px;
            margin: auto;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
        }

        h1 {
            text-align: center;
            font-size: 36px;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #6b7280;
            margin-bottom: 30px;
        }

        textarea {
            width: 100%;
            height: 180px;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            font-size: 14px;
            resize: vertical;
        }

        input[type=file] {
            margin-top: 10px;
        }

        button {
            width: 100%;
            margin-top: 20px;
            padding: 16px;
            border: none;
            border-radius: 12px;
            background: #4f46e5;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }

        button:hover {
            background: #4338ca;
        }

        .output {
            margin-top: 40px;
        }

        .card {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            padding: 20px;
            border-radius: 12px;
            line-height: 1.7;
            font-size: 15px;
        }

        .error {
            margin-top: 20px;
            padding: 12px;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 10px;
        }

        @media (max-width: 640px) {
            .container {
                padding: 24px;
            }
        }
    </style>
</head>

<body>

<div class="container">
    <h1>✨ AI Resume Improver</h1>
    <p class="subtitle">
        Transform your resume bullets into strong, recruiter-ready statements.
    </p>

    <form method="POST" enctype="multipart/form-data">
        <textarea name="resume_text" placeholder="Paste your resume text here..."></textarea>

        <p><strong>Or upload your resume (PDF):</strong></p>
        <input type="file" name="resume_pdf" accept=".pdf">

        <button type="submit">🚀 Improve My Resume</button>
    </form>

    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}

    {% if improved %}
    <div class="output">

        <div style="display:grid; gap:24px;">

            <div>
                <h3 style="margin-bottom:10px; color:#6b7280; font-weight:600;">
                    📝 Your Original
                </h3>
                <div class="card">
                    {{ original | safe }}
                </div>
            </div>

            <div>
                <h3 style="margin-bottom:10px; color:#111827; font-weight:700;">
                    ✨ AI Improved Version
                </h3>
                <div class="card">
                    {{ improved | safe }}
                </div>
            </div>

        </div>

    </div>
    {% endif %}
</div>

</body>
</html>
"""

# =========================
# 🚀 ROUTE
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    improved = None
    original = None
    error = None

    if request.method == "POST":
        resume_text = request.form.get("resume_text", "").strip()
        pdf_file = request.files.get("resume_pdf")

        # If PDF uploaded, override text
        if pdf_file and pdf_file.filename.endswith(".pdf"):
            extracted = extract_text_from_pdf(pdf_file)
            if extracted:
                resume_text = extracted
            else:
                error = "❌ Could not read the uploaded PDF."

        if not resume_text:
            error = "⚠️ Please paste resume text or upload a PDF."
        else:
            try:
                improved_raw = improve_resume(resume_text)

                # 🔥 Markdown rendering (BIG UX WIN)
                improved = markdown.markdown(improved_raw)
                original = markdown.markdown(resume_text)

            except Exception as e:
                error = f"Error: {str(e)}"

    return render_template_string(
        HTML_TEMPLATE,
        improved=improved,
        original=original,
        error=error
    )

# =========================
# 🔴 CRITICAL: Render port binding
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
