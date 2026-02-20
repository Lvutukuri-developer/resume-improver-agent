import os
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from agent import improve_resume

# ================================
# Load environment variables
# ================================
load_dotenv()

app = Flask(__name__)

# ================================
# Modern UI Template
# ================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Resume Improver</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }

        .container {
            background: #111827;
            padding: 40px;
            border-radius: 16px;
            width: 90%;
            max-width: 700px;
            box-shadow: 0 0 30px rgba(99,102,241,0.4);
        }

        h1 {
            text-align: center;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #9ca3af;
            margin-bottom: 25px;
        }

        textarea {
            width: 100%;
            height: 180px;
            padding: 12px;
            border-radius: 10px;
            border: none;
            margin-bottom: 15px;
            font-size: 14px;
        }

        input[type="file"] {
            margin-bottom: 20px;
            color: #d1d5db;
        }

        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.25s;
        }

        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 0 20px rgba(139,92,246,0.6);
        }

        .output {
            margin-top: 25px;
            background: #020617;
            padding: 15px;
            border-radius: 10px;
            white-space: pre-wrap;
        }

        .error {
            margin-top: 20px;
            color: #f87171;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AI Resume Improver</h1>
        <p class="subtitle">Paste your resume or upload a PDF</p>

        <form method="POST" enctype="multipart/form-data">
            <textarea name="resume_text" placeholder="Paste your resume bullet here..."></textarea>

            <p>Or upload your resume (PDF):</p>
            <input type="file" name="resume_pdf" accept=".pdf">

            <button type="submit">✨ Improve Resume</button>
        </form>

        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}

        {% if improved %}
        <div class="output">
{{ improved }}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# ================================
# Helper: extract text from PDF
# ================================
def extract_text_from_pdf(file_storage):
    try:
        reader = PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception:
        return ""

# ================================
# Routes
# ================================
@app.route("/", methods=["GET", "POST"])
def home():
    improved = None
    error = None

    if request.method == "POST":
        resume_text = request.form.get("resume_text", "").strip()
        pdf_file = request.files.get("resume_pdf")

        # Priority: PDF if uploaded
        if pdf_file and pdf_file.filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(pdf_file)

        if not resume_text:
            error = "Please paste text or upload a PDF."
        else:
            try:
                improved = improve_resume(resume_text)
            except Exception as e:
                error = f"Error: {str(e)}"

    return render_template_string(
        HTML_TEMPLATE,
        improved=improved,
        error=error
    )

# ================================
# 🚨 CRITICAL: Render-compatible run
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
