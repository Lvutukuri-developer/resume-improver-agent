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

def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

def generate_surgical_diff(orig, imp):
    """
    Compares words rather than lines to provide 'Apple-level' precision highlighting.
    """
    output = []
    # Tokenize by whitespace but keep newlines
    orig_words = re.findall(r'\S+|\n', orig)
    imp_words = re.findall(r'\S+|\n', imp)
    
    sm = difflib.SequenceMatcher(None, orig_words, imp_words)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            output.append(" ".join(imp_words[j1:j2]))
        elif tag == 'replace' or tag == 'insert':
            # Wrap only the changed/new parts in a highlight span
            changed_text = " ".join(imp_words[j1:j2])
            output.append(f'<span class="hl">{changed_text}</span>')
        # 'delete' is ignored for the 'After' view to keep it clean
            
    return markdown.markdown(" ".join(output).replace(" \n ", "\n"))

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
            --highlight: rgba(52, 199, 89, 0.2); /* Soft Apple Green */
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            -webkit-font-smoothing: antialiased;
        }
        .nav { width: 100%; padding: 20px; text-align: center; background: rgba(255,255,255,0.7); backdrop-filter: blur(20px); position: sticky; top: 0; z-index: 10; border-bottom: 0.5px solid #d2d2d7; }
        
        .container { max-width: 1100px; width: 90%; margin: 40px 0; }
        
        /* Drag & Drop Apple Style */
        .drop-zone {
            position: relative;
            border: 2px dashed #d2d2d7;
            border-radius: 18px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            background: var(--card);
            cursor: pointer;
        }
        .drop-zone:hover { border-color: var(--apple-blue); background: #fff; }
        .drop-zone input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        
        .btn {
            background: var(--apple-blue);
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 500;
            border-radius: 980px;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s;
        }
        .btn:active { transform: scale(0.98); }

        /* Resume Workspace */
        .workspace {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 40px;
        }
        .page-preview {
            background: white;
            padding: 40px;
            border-radius: 4px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            min-height: 600px;
            font-size: 14px;
            line-height: 1.5;
            color: #333;
        }
        .page-header { font-weight: 600; margin-bottom: 10px; color: #86868b; text-transform: uppercase; font-size: 12px; }
        
        /* Surgical Highlight */
        .hl {
            background-color: var(--highlight);
            border-bottom: 1px solid rgba(52, 199, 89, 0.4);
            color: #1a4721;
            padding: 0 2px;
            border-radius: 2px;
        }
        
        #spinner { display: none; margin-top: 20px; color: var(--apple-blue); font-weight: 500; }
        
        textarea { width: 100%; height: 100px; border-radius: 12px; border: 1px solid #d2d2d7; padding: 15px; margin-top: 15px; font-family: inherit; }
    </style>
</head>
<body>

<div class="nav"><strong>Resume Optimizer</strong></div>

<div class="container">
    <form method="POST" enctype="multipart/form-data" onsubmit="document.getElementById('spinner').style.display='block'">
        <div class="drop-zone" id="dropZone">
            <div id="drop-text">Drag & drop your PDF here or click to browse</div>
            <input type="file" name="resume_pdf" accept=".pdf" onchange="updateFileName(this)">
        </div>
        
        <textarea name="resume_text" placeholder="Or paste your resume text here..."></textarea>
        
        <div style="text-align: center;">
            <button class="btn">Refine Resume</button>
            <div id="spinner">Optimizing with AI...</div>
        </div>
    </form>

    {% if diff_html %}
    <div class="workspace">
        <div>
            <div class="page-header">Original</div>
            <div class="page-preview">{{ original | safe }}</div>
        </div>
        <div>
            <div class="page-header">Optimized (AI Changes Highlighted)</div>
            <div class="page-preview">{{ diff_html | safe }}</div>
        </div>
    </div>
    {% endif %}
</div>

<script>
    function updateFileName(input) {
        const text = document.getElementById('drop-text');
        text.innerText = input.files[0] ? `Selected: ${input.files[0].name}` : "Drag & drop your PDF here";
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
                # Render original as Markdown for structure
                original = markdown.markdown(text)
                # Use our new word-level diffing engine
                diff_html = generate_surgical_diff(text, improved_text)
            except Exception as e:
                error = str(e)

    return render_template_string(HTML_TEMPLATE, original=original, diff_html=diff_html, error=error)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)