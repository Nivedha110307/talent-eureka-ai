"""Deterministic, evidence-first matching. Scores are relevance signals, never hiring odds."""
from __future__ import annotations

import re
from collections.abc import Iterable

WEIGHTS = {"required": 0.60, "preferred": 0.20, "title": 0.10, "experience": 0.10}
SYNONYMS = {
    "postgresql": {"postgres", "postgresql"},
    "javascript": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
    "rest api": {"rest api", "rest apis", "api development", "api endpoints", "http api"},
    "data analysis": {"data analysis", "analyze data", "analysing data", "analytics"},
    "machine learning": {"machine learning", "ml", "predictive modeling", "predictive modelling"},
}

def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", value.lower()).strip()

def _variants(value: str) -> set[str]:
    normalized = normalize(value)
    return next((variants for variants in SYNONYMS.values() if normalized in {normalize(v) for v in variants}), {normalized})

def _excerpt(text: str, terms: set[str], radius: int = 95) -> str | None:
    clean = " ".join(text.split())
    for term in sorted(terms, key=len, reverse=True):
        if not term:
            continue
        match = re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", clean, re.IGNORECASE)
        if match:
            start=max(0,match.start()-radius); end=min(len(clean),match.end()+radius)
            return ("…" if start else "") + clean[start:end] + ("…" if end<len(clean) else "")
    return None

def _candidate_evidence(profile: dict, requirement: str) -> tuple[str | None, str | None, str | None]:
    variants = _variants(requirement)
    skills = profile.get("skills", []) or []
    for skill in skills:
        if normalize(skill) in {normalize(v) for v in variants}:
            return skill, "skills", "explicit"
    sources = [("projects", s) for s in profile.get("projects", [])] + [("experience", s) for s in profile.get("experience", [])]
    for section, text in sources:
        excerpt = _excerpt(text, {normalize(v) for v in variants})
        if excerpt:
            return excerpt, section, "explicit"
    body=" ".join(text for _,text in sources)
    tokens={t for t in normalize(requirement).split() if len(t)>3}
    if tokens:
        present={t for t in tokens if re.search(rf"\b{re.escape(t)}\b",normalize(body))}
        if present and len(present)<len(tokens):
            excerpt=_excerpt(body,present)
            if excerpt: return excerpt,"project or experience","partial"
    return None,None,None

def match_job(profile: dict, job: dict) -> dict:
    """Map requirements to explicit, partial, or unavailable profile evidence."""
    required = [str(s) for s in (job.get("required_skills") or []) if str(s).strip()]
    preferred = [str(s) for s in (job.get("preferred_skills") or []) if str(s).strip()]
    supported=[]; partial=[]; missing=[]; supported_pref=0.0
    evidence_scores=[]
    for skill in required:
        excerpt, section, grade = _candidate_evidence(profile, skill)
        if grade == "explicit":
            item={"skill":skill,"excerpt":excerpt,"section":section,"job_excerpt":_excerpt(job.get("description", ""),{normalize(v) for v in _variants(skill)}),"status":"explicit"}
            supported.append(item);evidence_scores.append(1.0)
        elif grade == "partial":
            partial.append({"skill":skill,"excerpt":excerpt,"section":section,"job_excerpt":_excerpt(job.get("description", ""),{normalize(v) for v in _variants(skill)}),"status":"partial"});evidence_scores.append(0.5)
        else: missing.append(skill); evidence_scores.append(0.0)
    for skill in preferred:
        _,_,grade=_candidate_evidence(profile,skill)
        if grade=="explicit": supported_pref+=1
        elif grade=="partial": supported_pref+=0.5
    req_coverage=sum(evidence_scores)/max(1,len(required))
    pref_coverage=supported_pref/max(1,len(preferred)) if preferred else 0.5
    title_words=set(normalize(job.get("title", "")).split())
    role_words=set(normalize(" ".join(profile.get("preferred_roles",[]) or [])).split())
    title_score=len(title_words & role_words)/max(1,len(title_words)) if role_words else 0
    exp_level=profile.get("experience_level", "")
    job_level=job.get("experience_level", "")
    exp_score=1.0 if not job_level or not exp_level or exp_level==job_level else 0.35
    score=round(100*(WEIGHTS["required"]*req_coverage+WEIGHTS["preferred"]*pref_coverage+WEIGHTS["title"]*title_score+WEIGHTS["experience"]*exp_score))
    return {"score":score,"label":"Relevant experience found" if supported or partial else "Potential fit","supported":supported,"partially_supported":partial,"not_evidenced":missing,"required_coverage":round(req_coverage*100),"preferred_coverage":round(pref_coverage*100),"title_relevance":round(title_score*100),"experience_relevance":round(exp_score*100),"weights":WEIGHTS}

def reciprocal_rank_fusion(rankings: Iterable[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """RRF score(d)=sum(1/(k+rank_i(d))); ranks are one-based."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, 1): scores[doc_id] = scores.get(doc_id, 0.0) + 1/(k+rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))
