import os
import base64
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from agent import improve_resume
from PyPDF2 import PdfReader

load_dotenv()
app = Flask(__name__)

# ==========================
# Extract text for the AI
# ==========================
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

# ==========================
# Apple-Style Layout
# ==========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume AI | Desktop View</title>
    <style>
        :root {
            --apple-blue: #0071e3;
            --bg: #f5f5f7;
            --text-main: #1d1d1f;
            --highlight: rgba(0, 113, 227, 0.15);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            background-color: var(--bg);
            margin: 0;
            overflow-x: hidden;
        }
        /* Top Navigation */
        .nav {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(20px);
            padding: 15px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #d2d2d7;
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .nav-logo { font-weight: 600; font-size: 19px; letter-spacing: -0.5px; }
        
        /* Upload Section */
        .upload-bar {
            padding: 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .drop-zone {
            width: 100%;
            max-width: 600px;
            background: white;
            border-radius: 18px;
            padding: 30px;
            text-align: center;
            border: 2px dashed #d2d2d7;
            cursor: pointer;
            transition: 0.2s;
        }
        .drop-zone:hover { border-color: var(--apple-blue); }

        /* THE SPLIT VIEWPORT */
        .workspace {
            display: grid;
            grid-template-columns: 1fr 1fr;
            height: calc(100vh - 200px);
            gap: 20px;
            padding: 0 20px 40px;
        }
        .viewer-container {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .viewer-label {
            font-size: 12px;
            font-weight: 600;
            color: #86868b;
            text-transform: uppercase;
            margin-bottom: 10px;
            padding-left: 10px;
        }
        
        /* Left Side: Real PDF */
        .pdf-frame {
            width: 100%;
            height: 100%;
            border-radius: 12px;
            border: 1px solid #d2d2d7;
            background: #fff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }

        /* Right Side: Virtual Document */
        .virtual-doc {
            width: 100%;
            height: 100%;
            background: white;
            border-radius: 12px;
            border: 1px solid #d2d2d7;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            overflow-y: auto;
            padding: 50px;
            box-sizing: border-box;
            font-family: "Times New Roman", Times, serif; /* Resume Standard */
            font-size: 14px;
            line-height: 1.5;
            color: #000;
        }
        .improved-text { white-space: pre-wrap; }
        
        /* Highlight Styling */
        .hl {
            background-color: #fff9c4;
            border-bottom: 1px solid #fbc02d;
            padding: 2px 0;
        }

        .btn-refine {
            background: var(--apple-blue);
            color: white;
            padding: 12px 24px;
            border-radius: 980px;
            border: none;
            font-weight: 500;
            cursor: pointer;
            margin-top: 20px;
        }
        #loading { display: none; color: var(--apple-blue); margin-top: 10px; font-weight: 500; }
    </style>
</head>
<body>

<div class="nav">
    <div class="nav-logo">ResumeAI Pro</div>
</div>

<div class="upload-bar">
    <div class="drop-zone" onclick="document.getElementById('pdf-input').click()">
        <p id="status-text">Drop your original PDF here to begin</p>
        <input type="file" id="pdf-input" name="resume_pdf" form="mainForm" hidden accept=".pdf">
    </div>
    <form id="mainForm" method="POST" enctype="multipart/form-data">
        <button type="submit" class="btn-refine" onclick="showLoad()">Analyze & Refine</button>
    </form>
    <div id="loading">✨ Crafting your flagship resume...</div>
</div>

{% if improved_content %}
<div class="workspace">
    <div class="viewer-container">
        <span class="viewer-label">Original Document</span>
        <iframe class="pdf-frame" src="data:application/pdf;base64,{{ pdf_base64 }}"></iframe>
    </div>

    <div class="viewer-container">
        <span class="viewer-label">AI Refined Version</span>
        <div class="virtual-doc">
            <div class="improved-text">{{ improved_content | safe }}</div>
        </div>
    </div>
</div>
{% endif %}

<script>
    const fileInput = document.getElementById('pdf-input');
    const statusText = document.getElementById('status-text');
    
    fileInput.onchange = () => {
        if(fileInput.files[0]) statusText.innerText = "Ready: " + fileInput.files[0].name;
    };

    function showLoad() {
        document.getElementById('loading').style.display = 'block';
    }
</script>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    improved_content = None
    pdf_base64 = None

    if request.method == "POST":
        pdf_file = request.files.get("resume_pdf")
        if pdf_file and pdf_file.filename:
            # 1. Read file for base64 display (The "Before" PDF)
            file_content = pdf_file.read()
            pdf_base64 = base64.b64encode(file_content).decode('utf-8')
            
            # 2. Reset pointer and extract text for AI
            pdf_file.seek(0)
            text = extract_text_from_pdf(pdf_file)
            
            # 3. Get AI Improvement
            improved_text = improve_resume(text)
            
            # 4. Simple formatting for the "After" View
            # Note: You can add logic here to wrap specific keywords in <span class="hl">
            improved_content = improved_text.replace("\n", "<br>")

    return render_template_string(HTML_TEMPLATE, 
                                 improved_content=improved_content, 
                                 pdf_base64=pdf_base64)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)