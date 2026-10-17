from fastapi.testclient import TestClient
import pytest
from app.database import engine
from app.models import Base
from app.seed import seed_database
from app.database import SessionLocal

from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_demo_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed_database(db)
    yield

def test_health_and_synthetic_job_search():
    assert client.get('/api/health').status_code == 200
    result = client.get('/api/jobs', params={'q': 'FastAPI'})
    assert result.status_code == 200
    assert result.json()['synthetic_data'] is True
    assert result.json()['items'][0]['id'] == 'sample-001'

def test_profile_edit_and_job_save():
    result = client.put('/api/profile', json={'skills':['Python','SQL'], 'projects':[], 'experience':[], 'preferred_roles':['Backend Engineer'], 'preferred_locations':[], 'experience_level':'Early career'})
    assert result.status_code == 200
    jobs = client.get('/api/jobs').json()['items']
    assert jobs[0]['match']['required_coverage'] > 0
    saved = client.put('/api/jobs/sample-001/saved')
    assert saved.json()['saved'] is True
    assert any(r['job']['id'] == 'sample-001' for r in client.get('/api/applications').json()['items'])

def test_profile_and_saves_survive_new_database_sessions():
    client.put('/api/profile', json={'skills':['SQL'], 'projects':[], 'experience':[], 'education':[], 'preferred_roles':[], 'preferred_locations':[], 'experience_level':''})
    client.put('/api/jobs/sample-002/saved')
    assert client.get('/api/profile').json()['skills'] == ['SQL']
    assert client.get('/api/applications').json()['items'][0]['job']['id'] == 'sample-002'

def test_job_ingestion_checks_required_fields_and_duplicate_urls():
    payload={'jobs':[{'title':'Data helper','company':'Example','description':'SQL work','source':'Test feed','url':'https://example.com/imported','required_skills':['SQL']}]}
    assert client.post('/api/ingest/json',json=payload).json()['added'] == 1
    assert client.post('/api/ingest/json',json=payload).json()['added'] == 0
    assert client.get('/api/jobs',params={'q':'Data helper','source':'imported'}).json()['total'] == 1

def test_potential_duplicates_are_reported_without_automatic_merge():
    first={'title':'Data Helper','company':'Example Inc','description':'Build SQL reports and explore weekly product data.','source':'Feed A','url':'https://jobs.example.com/one'}
    second={'title':'data helper','company':'Example Inc','description':'Build SQL reports and explore weekly product data for teams.','source':'Feed B','url':'https://jobs.example.com/two'}
    client.post('/api/ingest/json',json={'jobs':[first]})
    result=client.post('/api/ingest/json',json={'jobs':[second]}).json()
    assert result['added'] == 1
    assert result['potential_duplicates'][0]['candidates'][0]['company'] == 'Example Inc'

