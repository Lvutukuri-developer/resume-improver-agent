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
# Premium UI Template
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
            margin: 70px auto;
            padding: 0 20px;
            text-align: center;
        }

        h1 {
            font-size: 42px;
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

        .drop-zone {
            border: 2px dashed #d1d5db;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            color: #6b7280;
            margin-bottom: 20px;
            cursor: pointer;
            transition: 0.2s;
        }

        .drop-zone.dragover {
            border-color: #111827;
            background: #f9fafb;
        }

        input[type="file"] {
            display: none;
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

        .spinner {
            display: none;
            margin: 20px auto;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #111827;
            border-radius: 50%;
            width: 28px;
            height: 28px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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
        <form method="POST" enctype="multipart/form-data" id="resumeForm">

            <textarea name="resume_text" placeholder="Paste your resume here..."></textarea>

            <div class="drop-zone" id="dropZone">
                Drag & drop your PDF here or click to upload
            </div>

            <input type="file" name="resume_pdf" id="fileInput" accept=".pdf">

            <button type="submit">Improve Resume</button>

            <div class="spinner" id="spinner"></div>
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

<script>
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const form = document.getElementById("resumeForm");
const spinner = document.getElementById("spinner");

dropZone.addEventListener("click", () => fileInput.click());

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

    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        dropZone.textContent = "PDF uploaded ✓";
    }
});

form.addEventListener("submit", () => {
    spinner.style.display = "block";
});
</script>

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
                text += extracted + "\\n"
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

        # ✅ Robust PDF handling (FIXED)
        if pdf_file and pdf_file.filename:
            extracted = extract_text_from_pdf(pdf_file)
            if extracted:
                resume_text = extracted

        if not resume_text:
            error = "Please paste text or upload a valid PDF."
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
# Render-compatible run
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
