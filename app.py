from flask import Flask, render_template, request, jsonify
import os
import re
import PyPDF2
import docx
from io import BytesIO

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_bytes):
    try:
        reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

def extract_text_from_docx(file_bytes):
    try:
        doc = docx.Document(BytesIO(file_bytes))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"

def extract_text(file_bytes, filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(file_bytes)
    elif ext == 'docx':
        return extract_text_from_docx(file_bytes)
    elif ext == 'txt':
        return file_bytes.decode('utf-8', errors='ignore')
    return ""

def analyze_resume_free(resume_text):
    """A 100% free, rule-based Python resume analyzer."""
    t = resume_text.lower()
    words = t.split()
    wc = len(words)

    # 1. Extract Contact Info
    email = re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', resume_text)
    phone = re.search(r'(\+?\d[\d\s\-().]{8,14}\d)', resume_text)
    linkedin = re.search(r'linkedin\.com/in/[\w-]+', resume_text, re.IGNORECASE)

    # 2. Detect Sections
    section_kws = {
        'Experience': ['experience', 'work history', 'employment', 'career'],
        'Education': ['education', 'academic', 'qualification', 'degree', 'university', 'college', 'bachelor'],
        'Skills': ['skills', 'technical skills', 'core competencies', 'expertise'],
        'Projects': ['projects', 'portfolio'],
        'Summary': ['summary', 'objective', 'profile', 'about me'],
        'Certifications': ['certification', 'certificate', 'certified']
    }
    found = []
    missing = []
    for sec, kws in section_kws.items():
        if any(kw in t for kw in kws):
            found.append(sec)
        else:
            missing.append(sec)

    # 3. Detect Skills (Tailored for Data/Tech roles)
    tech_skills = ['python', 'java', 'javascript', 'react', 'sql', 'aws', 'docker', 'excel', 'power bi', 'machine learning', 'data science', 'duckdb', 'streamlit', 'git']
    soft_skills = ['leadership', 'communication', 'teamwork', 'problem solving', 'management', 'agile']
    detected_skills = [s for s in tech_skills + soft_skills if s in t]

    # 4. Action Verbs & Metrics
    action_verbs = ['achieved', 'built', 'created', 'designed', 'developed', 'improved', 'increased', 'led', 'managed', 'optimized', 'reduced', 'implemented']
    verb_count = sum(1 for v in action_verbs if v in t)
    action_verb_score = min(100, verb_count * 10 + 20)

    numbers = re.findall(r'\d+%|\$[\d,]+|\d+x', resume_text)
    quant_score = min(100, len(numbers) * 15 + 10)

    # 5. ATS Scoring & Issues
    ats_issues = []
    ats_score = 100
    
    if not email:
        ats_issues.append({"issue": "No email address found", "fix": "Add a professional email.", "severity": "high"})
        ats_score -= 15
    if not phone:
        ats_issues.append({"issue": "No phone number detected", "fix": "Include your phone number.", "severity": "high"})
        ats_score -= 15
    if 'Summary' not in found:
        ats_issues.append({"issue": "Missing professional summary", "fix": "Add a 2-3 sentence summary at the top.", "severity": "high"})
        ats_score -= 10
    if wc < 150:
        ats_issues.append({"issue": "Resume content is too short", "fix": "Expand your bullet points to show more detail.", "severity": "high"})
        ats_score -= 15
    if len(numbers) < 2:
        ats_issues.append({"issue": "Lacks quantified impact", "fix": "Add numbers and percentages to your achievements.", "severity": "medium"})
        ats_score -= 10

    ats_score = max(20, ats_score)
    
    content_score = min(100, int((len(found) / len(section_kws)) * 50 + min(wc, 500) / 10))
    format_score = 90 if ats_score > 70 else 60
    keywords_score = min(100, len(detected_skills) * 10 + 20)
    impact_score = min(100, verb_count * 8 + len(numbers) * 10 + 20)
    overall_score = int((ats_score * 0.3) + (content_score * 0.2) + (format_score * 0.15) + (keywords_score * 0.15) + (impact_score * 0.2))

    return {
        "candidate_name": "Applicant",
        "contact_info": {
            "email": email.group(0) if email else None,
            "phone": phone.group(0) if phone else None,
            "linkedin": linkedin.group(0) if linkedin else None,
            "location": None
        },
        "scores": {
            "ats_score": ats_score,
            "overall_score": overall_score,
            "content_score": content_score,
            "format_score": format_score,
            "keywords_score": keywords_score,
            "impact_score": impact_score
        },
        "sections_found": found,
        "sections_missing": missing,
        "skills_detected": detected_skills,
        "experience_years": "Unknown",
        "education": ["Extracted from text"],
        "strengths": [
            {"title": "Action Verbs", "description": f"Detected {verb_count} strong action verbs."} if verb_count > 3 else {"title": "Parseable format", "description": "Text was easily readable by the ATS Engine."}
        ],
        "weaknesses": [
            {"title": "Needs Quantified Results", "description": "Add more metrics to prove impact."} if len(numbers) < 2 else {"title": "Missing Sections", "description": "Ensure a standard layout."}
        ],
        "ats_issues": ats_issues,
        "keyword_suggestions": ["data analysis", "cross-functional collaboration", "KPIs"],
        "action_verb_score": action_verb_score,
        "quantification_score": quant_score,
        "suggestions": [
            {"category": "Optimization", "suggestion": "Ensure standard section headers like 'Experience' and 'Education'.", "priority": "high"},
            {"category": "Impact", "suggestion": "Start bullet points with strong action verbs.", "priority": "medium"}
        ],
        "overall_verdict": f"System matched with a score of {overall_score}/100. This data was processed locally via Python offline logic.",
        "job_titles_fit": ["Data Analyst", "Data Engineer", "Software Engineer"]
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['resume']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT'}), 400

    try:
        file_bytes = file.read()
        resume_text = extract_text(file_bytes, file.filename)

        if not resume_text or len(resume_text) < 50:
            return jsonify({'error': 'Could not extract text from the file.'}), 400

        # Call the FREE local Python function, completely offline
        analysis = analyze_resume_free(resume_text)
        analysis['raw_text_length'] = len(resume_text)
        analysis['word_count'] = len(resume_text.split())

        return jsonify({'success': True, 'analysis': analysis})

    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
