import os
import difflib
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader
import markdown

load_dotenv()
app = Flask(__name__)

# PDF text extractor
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except:
        return ""

# Diff highlighting
def highlight_diff(orig_html, improved_html):
    orig_lines = orig_html.splitlines()
    imp_lines = improved_html.splitlines()
    diff = difflib.ndiff(orig_lines, imp_lines)

    result = []
    for line in diff:
        if line.startswith("+ "):
            # highlight additions
            result.append(f"<div style='background: #fff9c4; padding:4px; border-radius:4px;'>{line[2:]}</div>")
        elif line.startswith("  "):
            result.append(line[2:])
        # removed lines aren't shown
    return "<br>".join(result)

# HTML
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
            padding: 0 16px;
            color: #111827;
        }
        .container {
            max-width: 960px;
            margin: 30px auto;
            background: #fff;
            padding: 40px;
            border-radius: 18px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
        }
        h1 {
            font-size: 38px;
            text-align: center;
            margin-bottom: 8px;
        }
        .subtitle {
            text-align: center;
            color: #64748b;
            margin-bottom: 30px;
            font-size: 16px;
        }
        textarea {
            width: 100%;
            height: 180px;
            padding: 14px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            font-size: 15px;
            margin-bottom: 16px;
            resize: vertical;
        }
        .drop-zone {
            padding: 22px;
            border: 2px dashed #cbd5e1;
            border-radius: 14px;
            text-align: center;
            color: #64748b;
            margin-bottom: 16px;
            cursor: pointer;
        }
        .drop-zone.dragover {
            background: #f1f5f9;
            border-color: #4f46e5;
        }
        .btn {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            color: white;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            cursor: pointer;
        }
        .spinner {
            text-align: center;
            margin-top: 16px;
            font-weight: 600;
            color: #6366f1;
            display: none;
        }
        .diff-container {
            display: flex;
            gap: 24px;
            margin-top: 36px;
        }
        .diff-col {
            width: 50%;
        }
        .diff-box {
            border: 1px solid #e5e7eb;
            overflow: auto;
            background: #fafafa;
            padding: 18px;
            border-radius: 12px;
            font-size: 15px;
            line-height: 1.6;
        }
    </style>
</head>

<body>
<div class="container">
    <h1>✨ AI Resume Improver</h1>
    <div class="subtitle">Transform your resume into recruiter-ready quality.</div>

    <form method="POST" enctype="multipart/form-data" onsubmit="showSpinner()">
        <textarea name="resume_text" placeholder="Paste your resume text here..."></textarea>

        <div class="drop-zone" id="dropZone">
            Drag & drop your resume PDF here<br>or click below to upload
            <br><br>
            <input type="file" name="resume_pdf" accept=".pdf">
        </div>

        <button class="btn">🚀 Improve + Highlight</button>
    </form>

    <div class="spinner" id="spinner">⚡ Analyzing...</div>

    {% if diff_html %}
    <div class="diff-container">
        <div class="diff-col">
            <h3 style="font-size:18px;color:#4b5563;">📝 Your Original</h3>
            <div class="diff-box">{{ original | safe }}</div>
        </div>
        <div class="diff-col">
            <h3 style="font-size:18px;color:#111827;">✨ AI Improved Highlights</h3>
            <div class="diff-box">{{ diff_html | safe }}</div>
        </div>
    </div>
    {% endif %}
</div>

<script>
function showSpinner() {
    document.getElementById("spinner").style.display = "block";
}
const dropZone = document.getElementById("dropZone");
dropZone.addEventListener("dragover", e => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});
dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const fileInput = dropZone.querySelector("input[type=file]");
    fileInput.files = e.dataTransfer.files;
});
</script>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    original = None
    diff_html = None
    error = None

    if request.method == "POST":
        text = request.form.get("resume_text", "").strip()
        pdf_file = request.files.get("resume_pdf")

        if pdf_file and pdf_file.filename:
            extracted = extract_text_from_pdf(pdf_file)
            if extracted:
                text = extracted

        if not text:
            error = "⚠️ Paste text or upload a PDF first."
        else:
            try:
                improved = improve_resume(text)

                # HTML-render the markdown
                original_html = markdown.markdown(text)
                improved_html = markdown.markdown(improved)

                diff_html = highlight_diff(original_html, improved_html)
                original = original_html

            except Exception as e:
                error = f"Error: {str(e)}"

    return render_template_string(
        HTML_TEMPLATE,
        original=original,
        diff_html=diff_html,
        error=error
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)