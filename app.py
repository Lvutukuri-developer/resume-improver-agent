import os
import PyPDF2
from flask import Flask, render_template_string, request
from dotenv import load_dotenv
from agent import improve_resume

# Load environment variables
load_dotenv()

app = Flask(__name__)

# =============================
# 📄 PDF TEXT EXTRACTION
# =============================
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text.strip()


# =============================
# 🖥️ INLINE HTML
# =============================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Resume Improver</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; max-width: 900px; }
        textarea { width: 100%; }
        pre { white-space: pre-wrap; background: #f4f4f4; padding: 16px; border-radius: 8px; }
        button { padding: 10px 16px; font-size: 16px; }
    </style>
</head>
<body>
    <h1>AI Resume Improver</h1>
    <p>Paste your resume text OR upload a PDF.</p>

    <form method="post" enctype="multipart/form-data">
        <textarea name="resume_text" rows="18" placeholder="Paste resume here..."></textarea>

        <p><strong>Or upload your resume (PDF):</strong></p>
        <input type="file" name="resume_pdf" accept=".pdf">

        <br><br>
        <button type="submit">Improve Resume</button>
    </form>

    {% if error %}
        <p style="color:red;"><strong>{{ error }}</strong></p>
    {% endif %}

    {% if result %}
        <h2>Improved Version:</h2>
        <pre>{{ result }}</pre>
    {% endif %}
</body>
</html>
"""


# =============================
# 🏠 MAIN ROUTE
# =============================
@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    error = None

    if request.method == "POST":
        resume_text = ""

        # Case 1: pasted text
        if "resume_text" in request.form and request.form["resume_text"].strip():
            resume_text = request.form["resume_text"]

        # Case 2: uploaded PDF
        elif "resume_pdf" in request.files:
            pdf_file = request.files["resume_pdf"]

            if pdf_file and pdf_file.filename != "":
                try:
                    resume_text = extract_text_from_pdf(pdf_file)
                except Exception:
                    error = "Could not read the PDF. Please try another file."

        if not resume_text:
            error = "Please paste resume text or upload a PDF."

        if resume_text:
            try:
                result = improve_resume(resume_text)
            except Exception:
                error = "AI processing failed. Check your API key."

    return render_template_string(HTML, result=result, error=error)


# =============================
# 🚀 RENDER-COMPATIBLE RUN
# =============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
