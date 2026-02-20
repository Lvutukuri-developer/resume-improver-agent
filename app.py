import os
import io
import json
import base64
from flask import Flask, request, render_template_string, send_file
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader
from weasyprint import HTML

load_dotenv()
app = Flask(__name__)

# ==========================
# 📄 PDF Text Extraction
# ==========================
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

# ==========================
# 🎨 Premium PDF Styles
# ==========================
RESUME_PDF_CSS = """
    body { font-family: 'Helvetica', sans-serif; padding: 50px; color: #1a1a1f; line-height: 1.4; }
    h1 { font-size: 28pt; margin-bottom: 5px; letter-spacing: -1px; }
    .contact { font-size: 10pt; color: #666; margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    h2 { font-size: 12pt; text-transform: uppercase; color: #0071e3; margin-top: 25px; margin-bottom: 10px; }
    .job { margin-bottom: 15px; }
    .job-title { font-weight: bold; font-size: 11pt; }
    .job-info { color: #555; font-size: 10pt; font-style: italic; }
    .skills-list { font-size: 10pt; }
"""

# ==========================
# 🖥️ Updated UI Template
# ==========================
# I kept your original HTML_TEMPLATE structure but added the 'Download' functionality
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Resume AI | Pro</title>
    <style>
        :root { --apple-blue: #0071e3; --bg: #f5f5f7; --text-primary: #1d1d1f; --text-secondary: #86868b; }
        body { font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text-primary); margin: 0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px; }
        .input-card { background: white; border-radius: 24px; padding: 30px; border: 1px solid #d2d2d7; margin-bottom: 30px; }
        .workspace { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .paper { background: white; border-radius: 12px; border: 1px solid #d2d2d7; height: 800px; overflow-y: auto; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        .btn { background: var(--apple-blue); color: white; border: none; padding: 15px 30px; border-radius: 980px; font-weight: 600; cursor: pointer; width: 100%; font-size: 16px; }
        .btn-download { background: #1d1d1f; margin-top: 20px; }
        #spinner { display: none; text-align: center; margin-top: 20px; color: var(--apple-blue); }
        h2 { border-bottom: 1px solid #eee; padding-bottom: 5px; color: var(--apple-blue); font-size: 18px; }
    </style>
</head>
<body>
<div class="container">
    <div class="input-card">
        <h1>Refine your Story.</h1>
        <form method="POST" enctype="multipart/form-data" onsubmit="showLoad()">
            <input type="file" name="resume_pdf" accept=".pdf" required>
            <button type="submit" class="btn">Optimize Resume</button>
        </form>
        <div id="spinner">✨ Crafting your professional profile...</div>
    </div>

    {% if data %}
    <div class="workspace">
        <div class="viewer-box">
            <span class="label">Original Document</span>
            <div class="paper">
                <iframe src="data:application/pdf;base64,{{ pdf_base64 }}" width="100%" height="100%" frameborder="0"></iframe>
            </div>
        </div>
        <div class="viewer-box">
            <span class="label">Optimized Result</span>
            <div class="paper" id="resume-preview">
                <h1>{{ data.name }}</h1>
                <p>{{ data.contact }}</p>
                <h2>Summary</h2>
                <p>{{ data.summary }}</p>
                <h2>Experience</h2>
                {% for job in data.experience %}
                    <div style="margin-bottom:15px;">
                        <strong>{{ job.title }}</strong> | <em>{{ job.company }}</em>
                        <p>{{ job.desc }}</p>
                    </div>
                {% endfor %}
            </div>
            <form action="/download" method="POST">
                <input type="hidden" name="json_data" value='{{ data | tojson }}'>
                <button type="submit" class="btn btn-download">Download Executive PDF</button>
            </form>
        </div>
    </div>
    {% endif %}
</div>
<script>function showLoad(){ document.getElementById('spinner').style.display='block'; }</script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    data, pdf_base64 = None, None
    if request.method == "POST":
        pdf_file = request.files.get("resume_pdf")
        if pdf_file:
            raw_pdf_data = pdf_file.read()
            pdf_base64 = base64.b64encode(raw_pdf_data).decode('utf-8')
            pdf_file.seek(0)
            text = extract_text_from_pdf(pdf_file)
            if text:
                data = improve_resume(text)
    
    return render_template_string(HTML_TEMPLATE, data=data, pdf_base64=pdf_base64)

@app.route("/download", methods=["POST"])
def download():
    # Retrieve the JSON data we sent from the hidden field
    json_str = request.form.get("json_data")
    data = json.loads(json_str)

    # Simple HTML template for the PDF
    pdf_html = f"""
    <html>
    <head><style>{RESUME_PDF_CSS}</style></head>
    <body>
        <h1>{data.get('name')}</h1>
        <div class="contact">{data.get('contact')}</div>
        <h2>Professional Summary</h2>
        <p>{data.get('summary')}</p>
        <h2>Work Experience</h2>
        {''.join([f'<div class="job"><div class="job-title">{j["title"]}</div><div class="job-info">{j["company"]}</div><p>{j["desc"]}</p></div>' for j in data.get('experience', [])])}
        <h2>Skills</h2>
        <p>{", ".join(data.get('skills', []))}</p>
    </body>
    </html>
    """
    
    # Generate PDF bytes
    pdf_bytes = HTML(string=pdf_html).write_pdf()
    
    return send_file(
        io.BytesIO(pdf_bytes),
        download_name="Optimized_Resume.pdf",
        as_attachment=True,
        mimetype='application/pdf'
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)