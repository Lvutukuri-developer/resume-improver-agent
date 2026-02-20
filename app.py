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
        # Extract text while attempting to preserve basic line structure
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

# ==========================
# Normalize original resume (Improved Formatting)
# ==========================
def normalize_resume_text(text: str) -> str:
    if not text:
        return ""
    # Remove excessive whitespace but keep single newlines for structure
    lines = [line.strip() for line in text.splitlines()]
    # Join with double newlines for Markdown to recognize paragraphs
    return "\n\n".join([l for l in lines if l])

# ==========================
# Word-level diff highlighting (Surgical Fix)
# ==========================
def generate_surgical_diff(orig, imp):
    # Split by whitespace but keep track of words
    orig_words = orig.split()
    imp_words = imp.split()
    
    sm = difflib.SequenceMatcher(None, orig_words, imp_words)
    output = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            output.append(" ".join(imp_words[j1:j2]))
        elif tag in ('replace', 'insert'):
            # Only wrap the SPECIFIC changed words in the hl span
            changed_text = " ".join(imp_words[j1:j2])
            output.append(f'<span class="hl">{changed_text}</span>')
        # Deletions are skipped to show the final "Improved" version

    # Convert the joined string to Markdown, then handle line breaks
    final_text = " ".join(output)
    return markdown.markdown(final_text).replace("\n", "<br>")

# ==========================
# Apple Flagship UI (HTML/CSS)
# ==========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume AI | Flagship Edition</title>
    <style>
        :root {
            --apple-blue: #007AFF;
            --bg: #F5F5F7;
            --card: #FFFFFF;
            --text: #1D1D1F;
            --secondary-text: #86868B;
            --highlight: rgba(255, 214, 0, 0.3);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .nav {
            width: 100%;
            height: 50px;
            background: rgba(245, 245, 247, 0.8);
            backdrop-filter: blur(20px);
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: 600;
            font-size: 14px;
        }
        .container {
            width: 90%;
            max-width: 1200px;
            margin: 60px auto;
        }
        h1 {
            font-size: 48px;
            font-weight: 700;
            letter-spacing: -1.2px;
            text-align: center;
            margin-bottom: 40px;
        }
        /* Hide default file input but keep it functional */
        .file-input-container {
            position: relative;
            width: 100%;
        }
        #hidden-file-input {
            position: absolute;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }
        .drop-zone {
            border: 2px dashed #D2D2D7;
            border-radius: 20px;
            padding: 60px;
            text-align: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: var(--card);
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }
        .drop-zone.dragover {
            border-color: var(--apple-blue);
            background: rgba(0, 122, 255, 0.05);
            transform: scale(1.01);
        }
        .drop-zone p {
            font-size: 20px;
            font-weight: 500;
            color: var(--secondary-text);
        }
        .drop-zone span {
            color: var(--apple-blue);
            text-decoration: none;
        }
        textarea {
            width: 100%;
            height: 120px;
            margin-top: 24px;
            padding: 20px;
            border-radius: 18px;
            border: 1px solid #d2d2d7;
            font-size: 16px;
            box-sizing: border-box;
            background: var(--card);
            font-family: inherit;
            resize: none;
        }
        .btn {
            background: var(--apple-blue);
            color: white;
            border: none;
            padding: 16px 32px;
            font-size: 17px;
            font-weight: 600;
            border-radius: 980px;
            width: 100%;
            margin-top: 24px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn:hover {
            background: #0071e3;
            transform: scale(1.01);
        }
        .workspace {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-top: 80px;
        }
        .page-preview {
            background: white;
            padding: 50px;
            border-radius: 24px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.08);
            min-height: 600px;
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            border: 1px solid #E5E5E7;
        }
        .page-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--secondary-text);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 20px;
            display: block;
        }
        .hl {
            background-color: var(--highlight);
            padding: 2px 0;
            border-bottom: 2px solid #FFD600;
            border-radius: 2px;
        }
        #spinner {
            display: none;
            text-align: center;
            margin-top: 20px;
            font-weight: 500;
            color: var(--apple-blue);
        }
    </style>
</head>
<body>

<div class="nav">Resume Optimizer Pro</div>

<div class="container">
    <h1>Refine your narrative.</h1>

    <form id="mainForm" method="POST" enctype="multipart/form-data">
        <div class="file-input-container">
            <div class="drop-zone" id="dropZone">
                <p>Drag your PDF here or <span>browse</span></p>
                <input type="file" name="resume_pdf" id="hidden-file-input" accept=".pdf">
            </div>
        </div>

        <textarea name="resume_text" placeholder="Or paste your professional summary..."></textarea>

        <button type="submit" class="btn" onclick="showLoading()">Refine Resume</button>
    </form>
    
    <div id="spinner">✨ Polishing your details...</div>

    {% if diff_html %}
    <div class="workspace">
        <div class="page-preview">
            <span class="page-label">Current Version</span>
            <div style="white-space: pre-wrap;">{{ original | safe }}</div>
        </div>
        <div class="page-preview">
            <span class="page-label">AI Optimized</span>
            <div>{{ diff_html | safe }}</div>
        </div>
    </div>
    {% endif %}
</div>

<script>
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("hidden-file-input");

    dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    ["dragleave", "drop"].forEach(type => {
        dropZone.addEventListener(type, () => dropZone.classList.remove("dragover"));
    });

    fileInput.addEventListener("change", function() {
        if (this.files.length > 0) {
            dropZone.querySelector('p').innerHTML = "Selected: <span>" + this.files[0].name + "</span>";
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
                # Agent logic
                improved_text = improve_resume(text)

                # Format Original for visual clarity
                clean_original = normalize_resume_text(text)
                original = clean_original # Kept as string for pre-wrap

                # Surgical Diffing
                diff_html = generate_surgical_diff(clean_original, improved_text)

            except Exception as e:
                error = str(e)

    return render_template_string(HTML_TEMPLATE, original=original, diff_html=diff_html, error=error)

if __name__ == "__main__":
    # Ensure Render deployment works by binding to 0.0.0.0 and dynamic port
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)