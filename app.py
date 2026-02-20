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

# ==========================
# Text Extraction
# ==========================
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

# ==========================================
# Surgical Word-Level Diff (Structured)
# ==========================================
def generate_highlighted_html(orig, imp):
    # 1. Clean up AI markdown artifacts
    imp_clean = imp.replace("```markdown", "").replace("```", "").strip()
    
    # 2. Split by lines to preserve Markdown structure (headers, bullets)
    orig_lines = [line.strip() for line in orig.splitlines() if line.strip()]
    imp_lines = imp_clean.splitlines()
    
    final_output_lines = []
    
    for line in imp_lines:
        stripped_line = line.strip()
        if not stripped_line:
            final_output_lines.append("")
            continue
            
        # If the exact line exists in the original, keep it clean
        if stripped_line in orig_lines:
            final_output_lines.append(line)
        else:
            # If changed, highlight words but protect Markdown symbols
            words = line.split()
            processed_words = []
            for word in words:
                # Don't highlight structural symbols like ###, -, or **
                if re.match(r'^(#+|\*+|-)$', word) or word.startswith('**') or word.endswith('**'):
                    processed_words.append(word)
                else:
                    processed_words.append(f'<span class="hl">{word}</span>')
            final_output_lines.append(" ".join(processed_words))

    # 3. Convert reconstructed Markdown back to HTML
    combined_md = "\n".join(final_output_lines)
    return markdown.markdown(combined_md)

# ==========================
# Apple Flagship UI (V5)
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
            --hl-bg: rgba(0, 113, 227, 0.12);
            --hl-border: rgba(0, 113, 227, 0.3);
            --border-dark: #b1b1b6; 
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            margin: 0;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 1240px; margin: 0 auto; padding: 40px 20px; }
        .header-section { text-align: center; margin-bottom: 40px; }
        h1 { font-size: 52px; font-weight: 700; letter-spacing: -0.02em; margin: 0; }
        .subtitle { font-size: 22px; color: var(--text-secondary); margin-top: 10px; }

        .input-card {
            background: var(--glass);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 30px;
            border: 1px solid rgba(0,0,0,0.05);
            box-shadow: 0 10px 30px rgba(0,0,0,0.02);
            margin-bottom: 40px;
        }
        .drop-zone {
            border: 2px dashed #d2d2d7;
            border-radius: 18px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            background: white;
            transition: 0.3s;
        }
        .drop-zone:hover { border-color: var(--apple-blue); }
        
        textarea {
            width: 100%; height: 80px; margin-top: 20px; padding: 15px;
            border-radius: 14px; border: 1px solid #d2d2d7; font-family: inherit;
            resize: none; box-sizing: border-box; font-size: 15px;
        }
        .btn {
            background: var(--apple-blue); color: white; border: none;
            padding: 16px 0; font-size: 17px; font-weight: 600;
            border-radius: 980px; width: 100%; margin-top: 15px;
            cursor: pointer; transition: 0.2s;
        }
        .btn:hover { opacity: 0.9; transform: scale(1.005); }

        .workspace { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        .viewer-box { display: flex; flex-direction: column; }
        .label { font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
        .paper {
            background: white; border-radius: 14px; border: 1px solid #d2d2d7;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06); height: 850px; overflow: hidden;
        }
        
        .improved-content {
            padding: 50px; overflow-y: auto; height: 100%;
            font-family: "Times New Roman", Times, serif; font-size: 15px;
            line-height: 1.5; color: #111; box-sizing: border-box;
        }
        
        .improved-content h1, .improved-content h2, .improved-content h3 {
            font-family: -apple-system, sans-serif;
            color: #000; 
            border-bottom: 1.5px solid var(--border-dark); 
            padding-bottom: 4px; 
            margin-top: 24px;
            margin-bottom: 12px;
            letter-spacing: -0.01em;
        }
        
        .hl {
            background-color: var(--hl-bg);
            border-bottom: 1.5px solid var(--hl-border);
            border-radius: 2px;
            padding: 0 1px;
        }

        #spinner { display: none; text-align: center; margin-top: 15px; color: var(--apple-blue); font-weight: 600; }
    </style>
</head>
<body>

<div class="container">
    <div class="header-section">
        <h1>Your resume, perfected.</h1>
        <p class="subtitle">Premium AI-driven career optimization.</p>
    </div>

    <div class="input-card">
        <form id="mainForm" method="POST" enctype="multipart/form-data">
            <div class="drop-zone" onclick="document.getElementById('pdf-input').click()">
                <p id="file-name">Drop your PDF here</p>
                <span>or click to browse</span>
                <input type="file" id="pdf-input" name="resume_pdf" hidden accept=".pdf">
            </div>
            <textarea name="resume_text" placeholder="Or paste your resume text..."></textarea>
            <button type="submit" class="btn" onclick="showLoad()">Refine Resume</button>
        </form>
        <div id="spinner">✨ Enhancing your professional profile...</div>
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
            raw_pdf_data = pdf_file.read()
            pdf_base64 = base64.b64encode(raw_pdf_data).decode('utf-8')
            pdf_file.seek(0)
            text = extract_text_from_pdf(pdf_file)

        if text:
            raw_improved = improve_resume(text)
            improved_html = generate_highlighted_html(text, raw_improved)

    return render_template_string(HTML_TEMPLATE, 
                                 improved_html=improved_html, 
                                 pdf_base64=pdf_base64)

if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    # '0.0.0.0' is required for Render to reach the container
    app.run(host="0.0.0.0", port=port)