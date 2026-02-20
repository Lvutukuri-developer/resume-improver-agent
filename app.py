import os
from flask import Flask, render_template_string, request
from agent import improve_resume

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Resume Improver</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        textarea { width: 100%; }
        pre { white-space: pre-wrap; background: #f4f4f4; padding: 15px; }
        button { padding: 10px 16px; font-size: 16px; }
    </style>
</head>
<body>
    <h1>AI Resume Improver</h1>
    <p>Paste your resume text below. The agent will improve it.</p>

    <form method="post">
        <textarea name="resume" rows="18" placeholder="Paste resume here..."></textarea>
        <br><br>
        <button type="submit">Improve Resume</button>
    </form>

    {% if improved %}
        <h2>Improved Version:</h2>
        <pre>{{ improved }}</pre>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    improved = None
    if request.method == "POST":
        resume_text = request.form.get("resume", "")
        if resume_text.strip():
            improved = improve_resume(resume_text)
    return render_template_string(HTML, improved=improved)

# ✅ CRITICAL: Render-compatible run block
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
