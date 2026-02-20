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
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #f5f7fb;
            margin: 0;
            padding: 0;
            color: #111827;
        }

        .wrapper {
            max-width: 900px;
            margin: 80px auto;
            padding: 0 20px;
            text-align: center;
        }

        h1 {
            font-size: 40px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #6b7280;
            margin-bottom: 40px;
            font-size: 18px;
        }

        .card {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            text-align: left;
        }

        textarea {
            width: 100%;
            height: 180px;
            padding: 14px;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            font-size: 14px;
            margin-bottom: 20px;
            resize: vertical;
        }

        input[type="file"] {
            margin-bottom: 24px;
        }

        button {
            width: 100%;
            padding: 14px;
            background: #111827;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        button:hover {
            background: #000;
            transform: translateY(-1px);
        }

        .output {
            margin-top: 30px;
            background: #f9fafb;
            padding: 20px;
            border-radius: 12px;
            white-space: pre-wrap;
            border: 1px solid #e5e7eb;
        }

        .error {
            margin-top: 20px;
            color: #dc2626;
            text-align: center;
            font-weight: 500;
        }

        footer {
            margin-top: 40px;
            text-align: center;
            color: #9ca3af;
            font-size: 14px;
        }
    </style>
</head>
<body>

<div class="wrapper">
    <h1>AI Resume Improver</h1>
    <p class="subtitle">
        Instantly strengthen your resume bullets with AI.
    </p>

    <div class="card">
        <form method="POST" enctype="multipart/form-data">
            <textarea name="resume_text" placeholder="Paste your resume here..."></textarea>

            <p><strong>Or upload your resume (PDF):</strong></p>
            <input type="file" name="resume_pdf" accept=".pdf">

            <button type="submit">Improve Resume</button>
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

    <footer>
        Built by Lucky • AI-powered resume optimization
    </footer>
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
