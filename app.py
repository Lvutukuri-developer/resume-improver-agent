import os
import difflib
import re
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader
import markdown

load_dotenv()
app = Flask(__name__)

# ==========================
# Extract text from PDF
# ==========================
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

# ==========================
# Normalize original resume
# ==========================
def normalize_resume_text(text: str) -> str:
    if not text:
        return ""

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    merged = []
    buffer = ""

    for line in lines:
        if line.isupper() and len(line) < 40:
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            merged.append(line)
            continue

        if len(line) < 25:
            buffer += " " + line
        else:
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            merged.append(line)

    if buffer:
        merged.append(buffer.strip())

    return "\n".join(merged)

# ==========================
# Word-level diff highlighting
# ==========================
def generate_surgical_diff(orig, imp):
    orig_words = re.findall(r'\S+|\n', orig)
    imp_words = re.findall(r'\S+|\n', imp)
    
    sm = difflib.SequenceMatcher(None, orig_words, imp_words)
    output = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            output.append(" ".join(imp_words[j1:j2]))
        elif tag in ('replace', 'insert'):
            changed_text = " ".join(imp_words[j1:j2])
            output.append(f'<span class="hl">{changed_text}</span>')
        # we ignore deletions in the improved view

    return markdown.markdown(" ".join(output).replace(" \n ", "\n"))

# ==========================
# HTML (Premium UI)
# ==========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Resume Optimizer Pro</title>
    <style>
        :root {
            --apple-blue: #007AFF;
            --bg: #F5F5F7;
            --card: #FFFFFF;
            --text: #1D1D1F;
            --highlight: rgba(255, 229, 100, 0.4);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }
        .container {
            width: 90%;
            max-width: 1100px;
            margin: 40px auto;
        }
        .drop-zone {
            border: 2px dashed #007AFF;
            border-radius: 18px;
            padding: 36px;
            text-align: center;
            font-size: 18px;
            color: #007AFF;
            transition: 0.2s ease;
            cursor: pointer;
            background: var(--card);
        }
        .drop-zone:hover {
            background: #fff;
            border-color: #0051D4;
        }
        .drop-zone.dragover {
            background: #e8f2ff;
            border-color: #0051D4;
        }
        textarea {
            width: 100%;
            height: 120px;
            margin-top: 20px;
            padding: 14px;
            border-radius: 14px;
            border: 1px solid #d2d2d7;
            font-size: 15px;
        }
        .btn {
            background: var(--apple-blue);
            color: white;
            border: none;
            padding: 14px 0;
            font-size: 16px;
            font-weight: 600;
            border-radius: 980px;
            width: 100%;
            margin-top: 20px;
            cursor: pointer;
        }
        .btn:hover {
            background: #0051D4;
        }
        #spinner {
            display: none;
            margin-top: 16px;
            text-align: center;
            color: var(--apple-blue);
            font-weight: 600;
        }
        .workspace {
            display: flex;
            gap: 30px;
            margin-top: 40px;
        }
        .page-preview {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            min-height: 500px;
            overflow-x: auto;
            font-size: 14px;
            line-height: 1.6;
        }
        .page-header {
            font-weight: 700;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            font-size: 13px;
            color: #666;
        }
        .hl {
            background-color: var(--highlight);
            padding: 0 2px;
            border-radius: 2px;
            border-bottom: 1px solid rgba(255, 221, 88, 0.6);
        }
    </style>
</head>
<body>

<div class="container">
    <div class="drop-zone" id="dropZone">
        Drag & drop your PDF here
        <input type="file" name="resume_pdf" accept=".pdf" style="display:none;">
    </div>

    <textarea name="resume_text" form="mainForm" placeholder="Or paste your resume text here..."></textarea>

    <button class="btn" form="mainForm">Refine Resume</button>
    <div id="spinner">Optimizing with AI...</div>

    {% if diff_html %}
    <div class="workspace">
        <div class="page-preview">
            <div class="page-header">Original</div>
            {{ original | safe }}
        </div>
        <div class="page-preview">
            <div class="page-header">Optimized (AI Changes Highlighted)</div>
            {{ diff_html | safe }}
        </div>
    </div>
    {% endif %}
</div>

<script>
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

dropZone.querySelector("input[type=file]").addEventListener("change", function() {
    const evt = new Event("submit", { bubbles: true });
    document.forms[0].dispatchEvent(evt);
});
</script>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    original, diff_html, error = None, None, None

    if request.method == "POST":
        text = request.form.get("resume_text", "").strip()
        pdf_file = request.files.get("resume_pdf")

        if pdf_file and pdf_file.filename:
            text = extract_text_from_pdf(pdf_file)

        if text:
            try:
                improved_text = improve_resume(text)

                clean_original = normalize_resume_text(text)
                original = markdown.markdown(clean_original)

                diff_html = generate_surgical_diff(clean_original, improved_text)

            except Exception as e:
                error = str(e)

    return render_template_string(HTML_TEMPLATE, original=original, diff_html=diff_html, error=error)

# =========================
# Render port binding
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)