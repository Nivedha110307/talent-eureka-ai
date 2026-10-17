from app.matching import match_job, reciprocal_rank_fusion

def test_explicit_evidence_and_missing_evidence_are_distinguished():
    result = match_job({"skills":["Python"],"projects":["Built APIs with FastAPI for a campus tool"]}, {"title":"Backend Engineer","required_skills":["Python","FastAPI","Kubernetes"],"preferred_skills":[]})
    assert result["required_coverage"] == 67
    assert "Kubernetes" in result["not_evidenced"]
    assert result["supported"][1]["excerpt"].startswith("Built APIs")

def test_missing_resume_evidence_is_not_claimed_absent():
    result = match_job({"skills":[],"projects":[]}, {"title":"Engineer","required_skills":["Python"]})
    assert result["not_evidenced"] == ["Python"]

def test_rrf_combines_rankings_deterministically():
    assert [key for key, _ in reciprocal_rank_fusion([["a","b"],["b","a"]])] == ["a","b"]

def test_synonym_is_matched_but_not_treated_as_a_quote():
    result = match_job({'skills':['ML']}, {'title':'Data Scientist','description':'Build machine learning models.','required_skills':['Machine Learning']})
    assert result['required_coverage'] == 100
    assert result['supported'][0]['section'] == 'skills'
    assert result['supported'][0]['job_excerpt'] == 'Build machine learning models.'

def test_partial_evidence_is_separate_from_explicit_evidence():
    result = match_job({'projects':['Used data to make weekly product reports']}, {'title':'Analyst','required_skills':['Data analysis']})
    assert result['partially_supported'][0]['skill'] == 'Data analysis'
    assert result['supported'] == []

def test_empty_profile_and_incomplete_job_are_handled():
    assert match_job({}, {'title':'Role'})['not_evidenced'] == []
    assert match_job({}, {'required_skills':['SQL']})['not_evidenced'] == ['SQL']

def test_ambiguous_multiword_requirement_only_gets_partial_credit():
    result = match_job({'projects':['Led a small team']}, {'required_skills':['team communication']})
    assert result['required_coverage'] == 50
    assert result['partially_supported'][0]['skill'] == 'team communication'
