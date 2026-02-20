import os
import base64
import difflib
import re
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader
import markdown

load_dotenv()
app = Flask(__name__)

def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

# ==========================================
# NEW: Surgical Word-Level Diff for HTML
# ==========================================
def generate_highlighted_html(orig, imp):
    # Strip markdown artifacts before diffing to avoid highlighting syntax
    imp_clean = imp.replace("```markdown", "").replace("```", "").strip()
    
    orig_words = orig.split()
    imp_words = imp_clean.split()
    
    sm = difflib.SequenceMatcher(None, orig_words, imp_words)
    output = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        word_block = " ".join(imp_words[j1:j2])
        if tag in ('replace', 'insert'):
            # Wrap specific word changes in our highlight class
            output.append(f'<span class="hl">{word_block}</span>')
        else:
            output.append(word_block)

    # Join words and then convert to Markdown to handle headers/bullets
    combined_text = " ".join(output)
    return markdown.markdown(combined_text)

# ==========================
# Apple Flagship UI (V3)
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
            --text-primary: #1d1d1f;
            --text-secondary: #86868b;
            --glass: rgba(255, 255, 255, 0.8);
            /* Soft Amber Highlight - subtle and premium */
            --hl-bg: rgba(255, 214, 0, 0.25);
            --hl-border: rgba(255, 184, 0, 0.4);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            margin: 0;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 60px 20px; }
        .header-section { text-align: center; margin-bottom: 50px; }
        h1 { font-size: 56px; font-weight: 700; letter-spacing: -0.02em; margin: 0; }
        .subtitle { font-size: 24px; color: var(--text-secondary); margin-top: 10px; }

        .input-card {
            background: var(--glass);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 30px;
            border: 1px solid rgba(0,0,0,0.05);
            box-shadow: 0 10px 30px rgba(0,0,0,0.02);
            margin-bottom: 50px;
        }
        .drop-zone {
            border: 2px dashed #d2d2d7;
            border-radius: 18px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            background: white;
            transition: 0.3s;
        }
        .drop-zone:hover { border-color: var(--apple-blue); }
        
        textarea {
            width: 100%; height: 100px; margin-top: 20px; padding: 15px;
            border-radius: 14px; border: 1px solid #d2d2d7; font-family: inherit;
            resize: none; box-sizing: border-box;
        }
        .btn {
            background: var(--apple-blue); color: white; border: none;
            padding: 16px 0; font-size: 17px; font-weight: 600;
            border-radius: 980px; width: 100%; margin-top: 20px;
            cursor: pointer; transition: 0.2s;
        }

        .workspace { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 40px; }
        .viewer-box { display: flex; flex-direction: column; }
        .label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
        .paper {
            background: white; border-radius: 12px; border: 1px solid #d2d2d7;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05); height: 800px; overflow: hidden;
        }
        
        /* The Highlight Style */
        .hl {
            background-color: var(--hl-bg);
            border-bottom: 1.5px solid var(--hl-border);
            border-radius: 2px;
            padding: 1px 0;
            transition: background-color 0.3s ease;
        }
        .hl:hover { background-color: rgba(255, 214, 0, 0.4); }

        .improved-content {
            padding: 50px; overflow-y: auto; height: 100%;
            font-family: "Times New Roman", Times, serif; font-size: 15px;
            line-height: 1.6; color: #111; box-sizing: border-box;
        }
        #spinner { display: none; text-align: center; margin-top: 15px; color: var(--apple-blue); font-weight: 600; }
    </style>
</head>
<body>

<div class="container">
    <div class="header-section">
        <h1>Your resume, perfected.</h1>
        <p class="subtitle">Highlighting impact. Maximizing visibility.</p>
    </div>

    <div class="input-card">
        <form id="mainForm" method="POST" enctype="multipart/form-data">
            <div class="drop-zone" onclick="document.getElementById('pdf-input').click()">
                <p id="file-name">Drop your PDF here</p>
                <span>or click to browse</span>
                <input type="file" id="pdf-input" name="resume_pdf" hidden accept=".pdf">
            </div>
            <textarea name="resume_text" placeholder="Or paste your resume content here..."></textarea>
            <button type="submit" class="btn" onclick="showLoad()">Refine Resume</button>
        </form>
        <div id="spinner">✨ Polishing your details...</div>
    </div>

    {% if improved_html %}
    <div class="workspace">
        <div class="viewer-box">
            <span class="label">Original Document</span>
            <div class="paper">
                <iframe src="data:application/pdf;base64,{{ pdf_base64 }}" width="100%" height="100%" frameborder="0"></iframe>
            </div>
        </div>
        <div class="viewer-box">
            <span class="label">Optimized Result (Changes Highlighted)</span>
            <div class="paper">
                <div class="improved-content">
                    {{ improved_html | safe }}
                </div>
            </div>
        </div>
    </div>
    {% endif %}
</div>

<script>
    const fileInput = document.getElementById('pdf-input');
    const fileName = document.getElementById('file-name');
    fileInput.onchange = () => { if(fileInput.files[0]) fileName.innerText = fileInput.files[0].name; };
    function showLoad() { document.getElementById('spinner').style.display = 'block'; }
</script>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    improved_html, pdf_base64 = None, None

    if request.method == "POST":
        pdf_file = request.files.get("resume_pdf")
        text = request.form.get("resume_text", "").strip()

        if pdf_file and pdf_file.filename:
            raw_content = pdf_file.read()
            pdf_base64 = base64.b64encode(raw_content).decode('utf-8')
            pdf_file.seek(0)
            text = extract_text_from_pdf(pdf_file)

        if text:
            # 1. Get AI raw output
            raw_improved = improve_resume(text)
            # 2. Generate HTML with surgical highlights
            improved_html = generate_highlighted_html(text, raw_improved)

    return render_template_string(HTML_TEMPLATE, 
                                 improved_html=improved_html, 
                                 pdf_base64=pdf_base64)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)