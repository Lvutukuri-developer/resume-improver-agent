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
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join([l for l in lines if l])

# ==========================
# Surgical Word-Level Diff
# ==========================
def generate_surgical_diff(orig, imp):
    orig_words = orig.split()
    imp_words = imp.split()
    
    sm = difflib.SequenceMatcher(None, orig_words, imp_words)
    output = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            output.append(" ".join(imp_words[j1:j2]))
        elif tag in ('replace', 'insert'):
            changed_text = " ".join(imp_words[j1:j2])
            output.append(f'<span class="hl">{changed_text}</span>')

    final_text = " ".join(output)
    # Convert double newlines to breaks for proper spacing
    return final_text.replace("\n", "<br>")

# ==========================
# Apple Flagship UI (V2)
# ==========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume AI | Pro</title>
    <style>
        :root {
            --apple-blue: #0071e3;
            --bg: #f5f5f7;
            --card-bg: rgba(255, 255, 255, 0.8);
            --text-primary: #1d1d1f;
            --text-secondary: #86868b;
            --highlight: rgba(255, 214, 0, 0.35);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            margin: 0;
            line-height: 1.47;
            -webkit-font-smoothing: antialiased;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 80px 20px;
        }
        h1 {
            font-size: 56px;
            font-weight: 700;
            letter-spacing: -0.015em;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 24px;
            color: var(--text-secondary);
            text-align: center;
            margin-bottom: 50px;
        }

        /* Apple Style Drag & Drop */
        .drop-zone {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 2px dashed #d2d2d7;
            border-radius: 20px;
            padding: 80px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }
        .drop-zone:hover {
            border-color: var(--apple-blue);
            background: #ffffff;
        }
        .drop-zone.dragover {
            background: rgba(0, 113, 227, 0.05);
            border-color: var(--apple-blue);
            transform: scale(1.01);
        }
        .drop-zone p {
            font-size: 21px;
            font-weight: 600;
            margin: 0;
        }
        .drop-zone span {
            color: var(--apple-blue);
            display: block;
            font-size: 16px;
            margin-top: 8px;
            font-weight: 400;
        }
        #file-input { display: none; }

        textarea {
            width: 100%;
            height: 100px;
            margin-top: 24px;
            padding: 20px;
            border-radius: 18px;
            border: 1px solid #d2d2d7;
            font-size: 17px;
            background: var(--card-bg);
            box-sizing: border-box;
            font-family: inherit;
            resize: none;
            outline: none;
        }
        textarea:focus { border-color: var(--apple-blue); }

        .btn {
            background: var(--apple-blue);
            color: white;
            border: none;
            padding: 18px 30px;
            font-size: 17px;
            font-weight: 600;
            border-radius: 980px;
            width: 100%;
            margin-top: 30px;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }
        .btn:hover { opacity: 0.9; }

        .workspace {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 60px;
        }
        .page-card {
            background: #ffffff;
            padding: 40px;
            border-radius: 24px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.04);
            font-size: 15px;
            line-height: 1.6;
            min-height: 500px;
            border: 1px solid #e5e5e7;
        }
        .label {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 24px;
            display: block;
        }
        .hl {
            background: var(--highlight);
            padding: 1px 0;
            border-radius: 2px;
            font-weight: 500;
        }
        #spinner {
            display: none;
            text-align: center;
            margin-top: 20px;
            color: var(--apple-blue);
            font-weight: 600;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Your resume, perfected.</h1>
    <p class="subtitle">AI-powered refinement for high-impact roles.</p>

    <form id="mainForm" method="POST" enctype="multipart/form-data">
        <div class="drop-zone" id="dropZone">
            <p id="drop-text">Drop your PDF here</p>
            <span>or click to browse your files</span>
            <input type="file" name="resume_pdf" id="file-input" accept=".pdf">
        </div>

        <textarea name="resume_text" placeholder="Or paste your resume content here..."></textarea>

        <button type="submit" class="btn" onclick="showLoading()">Refine Resume</button>
    </form>
    
    <div id="spinner">Analyzing your professional profile...</div>

    {% if diff_html %}
    <div class="workspace">
        <div class="page-card">
            <span class="label">Original</span>
            <div style="white-space: pre-wrap;">{{ original | safe }}</div>
        </div>
        <div class="page-card">
            <span class="label">Optimized Results</span>
            <div>{{ diff_html | safe }}</div>
        </div>
    </div>
    {% endif %}
</div>

<script>
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("file-input");
    const dropText = document.getElementById("drop-text");

    // 1. Click to Open File Explorer
    dropZone.addEventListener("click", () => fileInput.click());

    // 2. Handle File Selection via Explorer
    fileInput.addEventListener("change", function() {
        if (this.files.length > 0) {
            dropText.innerText = "File Selected: " + this.files[0].name;
            dropZone.style.borderColor = "var(--apple-blue)";
        }
    });

    // 3. Handle Drag & Drop Logic
    dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    ["dragleave", "drop"].forEach(type => {
        dropZone.addEventListener(type, () => dropZone.classList.remove("dragover"));
    });

    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files; // Assign dropped file to input
            dropText.innerText = "File Selected: " + e.dataTransfer.files[0].name;
            dropZone.style.borderColor = "var(--apple-blue)";
        }
    });

    function showLoading() {
        document.getElementById('spinner').style.display = 'block';
    }
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
                diff_html = generate_surgical_diff(clean_original, improved_text)
                original = clean_original
            except Exception as e:
                error = str(e)

    return render_template_string(HTML_TEMPLATE, original=original, diff_html=diff_html, error=error)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)