import os
import uuid
from pathlib import Path
from flask import Flask, request, render_template_string, send_file, session
from dotenv import load_dotenv
from agent import improve_resume
from markupsafe import escape
from PyPDF2 import PdfReader
from weasyprint import HTML

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "resume-improver-dev-key")
RESULT_DIR = Path(app.instance_path) / "resume_results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)


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
    .highlight { background: #fff3a3; border-radius: 3px; padding: 1px 3px; }
"""


def build_original_text_pdf(text):
    pdf_html = f"""
    <html>
    <head><style>{RESUME_PDF_CSS} pre {{ white-space: pre-wrap; font-family: 'Helvetica', sans-serif; }}</style></head>
    <body><pre>{escape(text)}</pre></body>
    </html>
    """
    return HTML(string=pdf_html).write_pdf()


def build_optimized_resume_pdf(data):
    jobs_html = []
    for job in data.get("experience", []):
        title = escape(job.get("title", ""))
        company = escape(job.get("company", ""))
        dates = escape(job.get("dates", ""))
        desc = escape(job.get("desc", ""))
        dates_html = f'<div class="job-info">{dates}</div>' if dates else ""
        jobs_html.append(
            f"""
            <div class="job">
                <div class="job-title">{title}</div>
                <div class="job-info">{company}</div>
                {dates_html}
                <p><span class="highlight">{desc}</span></p>
            </div>
            """
        )

    skills = ", ".join(data.get("skills", []))
    pdf_html = f"""
    <html>
    <head><style>{RESUME_PDF_CSS}</style></head>
    <body>
        <h1>{escape(data.get('name', ''))}</h1>
        <div class="contact">{escape(data.get('contact', ''))}</div>
        <h2>Professional Summary</h2>
        <p><span class="highlight">{escape(data.get('summary', ''))}</span></p>
        <h2>Work Experience</h2>
        {''.join(jobs_html)}
        <h2>Skills</h2>
        <p><span class="highlight">{escape(skills)}</span></p>
    </body>
    </html>
    """
    return HTML(string=pdf_html).write_pdf()


def result_pdf_path(result_id, name):
    try:
        uuid.UUID(result_id)
    except ValueError:
        return None
    return RESULT_DIR / f"{result_id}_{name}.pdf"


def save_result_pdfs(result_id, original_pdf_bytes, optimized_pdf_bytes):
    original_path = result_pdf_path(result_id, "original")
    optimized_path = result_pdf_path(result_id, "optimized")
    original_path.write_bytes(original_pdf_bytes)
    optimized_path.write_bytes(optimized_pdf_bytes)

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
            padding: 0;
        }
        .pdf-frame {
            border: 0;
            border-radius: 14px;
            height: 100%;
            width: 100%;
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
                <iframe class="pdf-frame" src="/original-pdf/{{ result_id }}"></iframe>
            </div>
        </div>
        <div class="viewer-box">
            <span class="label">Optimized Result</span>
            <div class="paper">
                <iframe class="pdf-frame" src="/optimized-pdf/{{ result_id }}"></iframe>
            </div>
            <a class="btn btn-download" href="/download/{{ result_id }}" download>Download Executive PDF</a>
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
    data, error, result_id = None, None, None
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
                original_pdf_bytes = raw_pdf_data
            elif resume_text:
                text = resume_text
                original_pdf_bytes = build_original_text_pdf(text)
            else:
                raise ValueError("Upload a PDF or paste your resume text to refine it.")

            data = improve_resume(text)
            result_id = str(uuid.uuid4())
            save_result_pdfs(result_id, original_pdf_bytes, build_optimized_resume_pdf(data))
            session["latest_result_id"] = result_id
        except Exception as exc:
            error = str(exc) or "Something went wrong while refining the resume."

    return render_template_string(
        HTML_TEMPLATE,
        data=data,
        error=error,
        result_id=result_id,
        resume_text=resume_text,
    )


@app.route("/original-pdf/<result_id>", methods=["GET"])
def original_pdf(result_id):
    pdf_path = result_pdf_path(result_id, "original")
    if not pdf_path or not pdf_path.exists():
        return "No original PDF is available.", 404

    return send_file(
        pdf_path,
        download_name="Original_Resume.pdf",
        mimetype="application/pdf",
    )


@app.route("/optimized-pdf/<result_id>", methods=["GET"])
def optimized_pdf(result_id):
    pdf_path = result_pdf_path(result_id, "optimized")
    if not pdf_path or not pdf_path.exists():
        return "No optimized PDF is available.", 404

    return send_file(
        pdf_path,
        download_name="Optimized_Resume.pdf",
        mimetype="application/pdf",
    )


@app.route("/download/<result_id>", methods=["GET"])
def download(result_id):
    pdf_path = result_pdf_path(result_id, "optimized")
    if not pdf_path or not pdf_path.exists():
        return "No optimized resume is available yet.", 400

    return send_file(
        pdf_path,
        download_name="Optimized_Resume.pdf",
        as_attachment=True,
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
