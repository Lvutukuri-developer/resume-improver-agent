from flask import Flask, render_template_string, request
from agent import improve_resume

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Resume Improver Agent</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; max-width: 900px; }
    textarea { width: 100%; }
    pre { white-space: pre-wrap; background: #f4f4f4; padding: 16px; border-radius: 8px; }
    button { padding: 10px 16px; font-size: 16px; }
  </style>
</head>
<body>
  <h1>AI Resume Improver</h1>
  <p>Paste your resume text below. The agent will rewrite it with stronger bullet points.</p>

  <form method="post">
    <textarea name="resume" rows="18" placeholder="Paste resume here...">{{ original or "" }}</textarea>
    <br><br>
    <button type="submit">Improve Resume</button>
  </form>

  {% if improved %}
    <h2>Improved Resume</h2>
    <pre>{{ improved }}</pre>
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    improved = None
    original = ""
    if request.method == "POST":
        original = request.form.get("resume", "")
        improved = improve_resume(original)
    return render_template_string(HTML, improved=improved, original=original)


if __name__ == "__main__":
    app.run(debug=True)
