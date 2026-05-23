import os
import io
import json
from flask import Flask, request, render_template_string, send_file, session
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader
from weasyprint import HTML

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "resume-improver-dev-key")


def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        page_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                page_text.append(text)
        return "\n".join(page_text).strip()
    except Exception as exc:
        raise ValueError("We could not read text from that PDF. Try a text-based PDF instead of a scanned image.") from exc


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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume AI | Pro</title>
    <style>
        :root {
            --blue: #0071e3;
            --bg: #f5f5f7;
            --text: #1d1d1f;
            --muted: #767680;
            --line: #d6d6de;
            --card: #ffffff;
        }
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
        }
        .container {
            width: min(1550px, calc(100% - 48px));
            margin: 0 auto;
            padding: 42px 0 64px;
        }
        .hero {
            text-align: center;
            margin-bottom: 48px;
        }
        .hero h1 {
            font-size: clamp(42px, 4.5vw, 64px);
            line-height: 1.05;
            margin: 0 0 14px;
            letter-spacing: 0;
        }
        .hero p {
            color: var(--muted);
            font-size: clamp(22px, 2vw, 30px);
            margin: 0;
        }
        .input-card {
            background: var(--card);
            border: 1px solid #ececf1;
            border-radius: 28px;
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.04);
            padding: 38px;
            margin-bottom: 34px;
        }
        .drop-zone {
            align-items: center;
            border: 2px dashed #cfd1da;
            border-radius: 24px;
            color: var(--text);
            cursor: pointer;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 164px;
            margin-bottom: 26px;
            text-align: center;
            transition: border-color 160ms ease, background 160ms ease;
        }
        .drop-zone:hover,
        .drop-zone.dragging {
            background: #f8fbff;
            border-color: var(--blue);
        }
        .drop-zone input { display: none; }
        .drop-zone strong {
            display: block;
            font-size: 21px;
            font-weight: 400;
            margin-bottom: 18px;
        }
        .drop-zone span {
            color: #2b2b31;
            font-size: 20px;
        }
        .file-name {
            color: var(--blue);
            font-size: 15px;
            margin-top: 18px;
        }
        textarea {
            border: 1px solid var(--line);
            border-radius: 18px;
            color: var(--text);
            display: block;
            font: inherit;
            font-size: 18px;
            min-height: 100px;
            margin-bottom: 24px;
            outline: none;
            padding: 18px;
            resize: vertical;
            width: 100%;
        }
        textarea:focus {
            border-color: var(--blue);
            box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
        }
        .btn {
            background: var(--blue);
            border: none;
            border-radius: 999px;
            color: white;
            cursor: pointer;
            display: block;
            font-size: 21px;
            font-weight: 700;
            padding: 18px 28px;
            text-align: center;
            text-decoration: none;
            width: 100%;
        }
        .btn:hover { background: #0068d1; }
        .btn-download {
            background: #1d1d1f;
            margin-top: 20px;
        }
        .message {
            border-radius: 14px;
            font-size: 15px;
            margin-top: 18px;
            padding: 13px 16px;
        }
        .error {
            background: #fff2f2;
            border: 1px solid #ffd4d4;
            color: #b00020;
        }
        #spinner {
            color: var(--blue);
            display: none;
            font-size: 16px;
            margin-top: 18px;
            text-align: center;
        }
        .workspace {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        .viewer-box > .label {
            color: var(--muted);
            display: block;
            font-size: 14px;
            font-weight: 700;
            margin: 0 0 10px 4px;
            text-transform: uppercase;
        }
        .paper {
            background: white;
            border: 1px solid #d2d2d7;
            border-radius: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            height: 720px;
            overflow-y: auto;
            padding: 36px;
            white-space: pre-wrap;
        }
        .highlight {
            background: #fff3a3;
            border-radius: 4px;
            box-decoration-break: clone;
            -webkit-box-decoration-break: clone;
            padding: 1px 4px;
        }
        .paper h1 {
            font-size: 32px;
            margin: 0 0 8px;
        }
        .paper h2 {
            border-bottom: 1px solid #eee;
            color: var(--blue);
            font-size: 18px;
            margin-top: 24px;
            padding-bottom: 5px;
        }
        .muted-note {
            color: var(--muted);
            font-size: 14px;
            margin-bottom: 20px;
        }
        @media (max-width: 900px) {
            .container { width: min(100% - 28px, 720px); padding-top: 30px; }
            .input-card { padding: 24px; border-radius: 22px; }
            .workspace { grid-template-columns: 1fr; }
            .hero { margin-bottom: 32px; }
            .drop-zone { min-height: 150px; }
        }
    </style>
</head>
<body>
<div class="container">
    <header class="hero">
        <h1>Your resume, perfected.</h1>
        <p>Premium AI-driven career optimization.</p>
    </header>

    <div class="input-card">
        <form method="POST" enctype="multipart/form-data" onsubmit="showLoad()">
            <label class="drop-zone" id="drop-zone">
                <input id="resume_pdf" type="file" name="resume_pdf" accept=".pdf">
                <strong>Drop your PDF here</strong>
                <span>or click to browse</span>
                <div class="file-name" id="file-name"></div>
            </label>
            <textarea name="resume_text" placeholder="Or paste your resume text...">{{ resume_text or "" }}</textarea>
            <button type="submit" class="btn">Refine Resume</button>
        </form>
        <div id="spinner">Refining your resume...</div>
        {% if error %}
            <div class="message error">{{ error }}</div>
        {% endif %}
    </div>

    {% if data %}
    <div class="workspace">
        <div class="viewer-box">
            <span class="label">Original Document</span>
            <div class="paper">
                <div class="muted-note">Extracted from your original resume</div>
                {{ original_text }}
            </div>
        </div>
        <div class="viewer-box">
            <span class="label">Optimized Result</span>
            <div class="paper" id="resume-preview">
                <div class="muted-note">Yellow marks rewritten or newly improved sections</div>
                <h1>{{ data.name }}</h1>
                <p>{{ data.contact }}</p>
                <h2>Summary</h2>
                <p><span class="highlight">{{ data.summary }}</span></p>
                <h2>Experience</h2>
                {% for job in data.experience %}
                    <div style="margin-bottom:15px;">
                        <strong>{{ job.title }}</strong> | <em>{{ job.company }}</em>
                        {% if job.dates %}<div>{{ job.dates }}</div>{% endif %}
                        <p><span class="highlight">{{ job.desc }}</span></p>
                    </div>
                {% endfor %}
                {% if data.skills %}
                    <h2>Skills</h2>
                    <p><span class="highlight">{{ data.skills | join(", ") }}</span></p>
                {% endif %}
            </div>
            <a class="btn btn-download" href="/download" download>Download Executive PDF</a>
        </div>
    </div>
    {% endif %}
</div>
<script>
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('resume_pdf');
const fileName = document.getElementById('file-name');

function showLoad(){
    document.getElementById('spinner').style.display='block';
}

function showFileName(file) {
    fileName.textContent = file ? file.name : '';
}

fileInput.addEventListener('change', () => showFileName(fileInput.files[0]));

dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropZone.classList.add('dragging');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragging');
});

dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
    if (event.dataTransfer.files.length) {
        fileInput.files = event.dataTransfer.files;
        showFileName(fileInput.files[0]);
    }
});
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    data, error, original_text = None, None, ""
    resume_text = ""
    if request.method == "POST":
        pdf_file = request.files.get("resume_pdf")
        resume_text = (request.form.get("resume_text") or "").strip()
        try:
            if pdf_file and pdf_file.filename:
                raw_pdf_data = pdf_file.read()
                pdf_file.seek(0)
                text = extract_text_from_pdf(pdf_file)
                if not text:
                    raise ValueError("No readable text was found in that PDF. If it is scanned, export it with selectable text and try again.")
            elif resume_text:
                text = resume_text
            else:
                raise ValueError("Upload a PDF or paste your resume text to refine it.")

            original_text = text
            data = improve_resume(text)
            session["latest_resume_data"] = data
        except Exception as exc:
            error = str(exc) or "Something went wrong while refining the resume."

    return render_template_string(
        HTML_TEMPLATE,
        data=data,
        error=error,
        original_text=original_text,
        resume_text=resume_text,
    )


@app.route("/download", methods=["GET"])
def download():
    data = session.get("latest_resume_data")
    if not data:
        return "No optimized resume is available yet.", 400

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

    pdf_bytes = HTML(string=pdf_html).write_pdf()

    return send_file(
        io.BytesIO(pdf_bytes),
        download_name="Optimized_Resume.pdf",
        as_attachment=True,
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
