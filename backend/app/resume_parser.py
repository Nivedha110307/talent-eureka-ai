"""Conservative, review-first extraction helpers for text-based resumes."""
import re

SKILL_TERMS = ["Python","Java","JavaScript","TypeScript","SQL","PostgreSQL","FastAPI","Django","Flask","React","Node.js","Docker","Kubernetes","AWS","Azure","GCP","Linux","Git","Tableau","Power BI","Excel","pandas","scikit-learn","TensorFlow","PyTorch","Figma","HTML","CSS","REST APIs","Machine Learning","Data Analysis","Data Modeling"]
HEADINGS = {"experience":("experience","work experience","employment","professional experience"),"projects":("projects","selected projects","personal projects"),"education":("education","academic background"),"skills":("skills","technical skills","core skills")}

def parse_resume_text(text: str) -> dict:
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    suggestions=[]
    normalized=re.sub(r"\s+"," ",text)
    for term in SKILL_TERMS:
        match=re.search(rf"(?<![\w]){re.escape(term)}(?![\w])",normalized,re.IGNORECASE)
        if match:
            start=max(0,match.start()-70);end=min(len(normalized),match.end()+110)
            suggestions.append({"skill":term,"excerpt":normalized[start:end].strip()})
    sections={key:[] for key in HEADINGS}
    active=None
    for line in lines:
        heading=next((key for key,aliases in HEADINGS.items() if line.lower().rstrip(":") in aliases),None)
        if heading:
            active=heading;continue
        if active and re.fullmatch(r"[A-Z][A-Z &/]{2,}",line): active=None
        elif active and len(sections[active])<30: sections[active].append(line)
    return {"suggested_skills":suggestions,"sections":sections}
