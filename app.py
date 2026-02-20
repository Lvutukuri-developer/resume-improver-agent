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
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            background: linear-gradient(180deg, #f5f7fb 0%, #eef2f7 100%);
            margin: 0;
            padding: 40px 16px;
            color: #0f172a;
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
            font-size: 40px;
            margin-bottom: 8px;
        }

        .subtitle {
            text-align: center;
            color: #64748b;
            margin-bottom: 30px;
        }

        textarea {
            width: 100%;
            height: 180px;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            font-size: 15px;
            resize: vertical;
        }

        .drop-zone {
            margin-top: 16px;
            padding: 24px;
            border: 2px dashed #cbd5e1;
            border-radius: 14px;
            text-align: center;
            color: #64748b;
            transition: all 0.2s ease;
        }

        .drop-zone.dragover {
            background: #f1f5f9;
            border-color: #6366f1;
        }

        .btn {
            margin-top: 20px;
            width: 100%;
            padding: 16px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 14px;
            color: white;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            cursor: pointer;
        }

        .spinner {
            display: none;
            text-align: center;
            margin-top: 20px;
            font-weight: 600;
            color: #6366f1;
        }

        .result-box {
            margin-top: 30px;
            padding: 24px;
            border-radius: 14px;
            background: #f8fafc;
            white-space: pre-wrap;
            line-height: 1.6;
            font-size: 15px;
        }

        .section-title {
            margin-top: 30px;
            font-weight: 700;
            font-size: 18px;
        }
    </style>
</head>

<body>
<div class="container">

    <h1>✨ AI Resume Improver</h1>
    <div class="subtitle">
        Transform your resume bullets into strong, recruiter-ready statements.
    </div>

    <form method="POST" enctype="multipart/form-data" onsubmit="showSpinner()">

        <textarea name="resume_text" placeholder="Paste your resume text here..."></textarea>

        <div class="drop-zone" id="dropZone">
            Drag & drop your resume PDF here<br>
            or click below to upload
            <br><br>
            <input type="file" name="resume_pdf" accept=".pdf">
        </div>

        <button class="btn">🚀 Improve My Resume</button>
    </form>

    <div class="spinner" id="spinner">
        ⚡ AI is analyzing your resume…
    </div>

    {% if original %}
        <div class="section-title">📝 Your Original</div>
        <div class="result-box">{{ original }}</div>
    {% endif %}

    {% if improved %}
        <div class="section-title">✨ AI Improved Version</div>
        <div class="result-box">{{ improved }}</div>
    {% endif %}

</div>

<script>
function showSpinner() {
    document.getElementById("spinner").style.display = "block";
}

const dropZone = document.getElementById("dropZone");

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const fileInput = dropZone.querySelector("input[type=file]");
    fileInput.files = e.dataTransfer.files;
});
</script>

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
