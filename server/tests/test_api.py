from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def auth_user():
    email=f"test-{uuid4().hex[:10]}@example.com"
    password="StudentAI123!"
    r=client.post('/api/auth/register',json={'email':email,'password':password})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['access_token']}"}


def test_health():
    r=client.get('/api/health')
    assert r.status_code==200
    assert r.json()['status']=='ok'
    assert r.json()['database']=='ok'
    assert r.json()['vector_store']=='chroma'


def test_chat_offline():
    r=client.post('/api/chat',json={'question':'What is a stack?'})
    assert r.status_code==200
    assert 'LIFO' in r.json()['answer']


def test_validation():
    assert client.post('/api/chat',json={'question':''}).status_code==422
    assert client.post('/api/auth/register',json={'email':'bad','password':'short'}).status_code==400


def test_protected_routes_require_auth():
    assert client.get('/api/notes').status_code in (401,403)
    assert client.get('/api/chat/history').status_code in (401,403)
    assert client.post('/api/study/plan',json={'subjects':[],'days':7}).status_code in (401,403)
    assert client.get('/api/analytics/daily').status_code in (401,403)
    assert client.get('/api/flashcards').status_code in (401,403)


def test_invalid_bearer_token_is_rejected():
    h={'Authorization':'Bearer definitely-invalid-token'}
    assert client.get('/api/notes',headers=h).status_code==401
    assert client.get('/api/chat/history',headers=h).status_code==401


def test_register_login_notes_history():
    h=auth_user()
    n=client.post('/api/notes',headers=h,json={'title':'DSA Revision','content':'Stacks use LIFO.'})
    assert n.status_code==200
    assert client.get('/api/notes',headers=h).status_code==200
    c=client.post('/api/chat',headers=h,json={'question':'What is a stack?'})
    assert c.status_code==200
    hist=client.get('/api/chat/history',headers=h)
    assert hist.status_code==200
    assert len(hist.json())>=2


def test_flashcard_persistence_and_review():
    h=auth_user()
    r=client.post('/api/flashcards/generate',headers=h,json={'topic':'Machine Learning','count':3})
    assert r.status_code==200
    generated=r.json()['cards']
    assert len(generated)>=1
    cards=client.get('/api/flashcards',headers=h)
    assert cards.status_code==200
    saved=cards.json()
    assert len(saved)>=1
    card_id=saved[0]['id']
    review=client.post(f'/api/flashcards/{card_id}/review',headers=h)
    assert review.status_code==200
    assert review.json()['review_count']>=1
    assert client.delete(f'/api/flashcards/{card_id}',headers=h).status_code==200


def test_daily_analytics_and_tasks():
    h=auth_user()
    subject=client.post('/api/subjects',headers=h,json={'name':'Data Structures','code':'DSA','daily_minutes':60})
    assert subject.status_code==200
    plan=client.post('/api/study/plan',headers=h,json={'subjects':subject.json() and [{'name':'Data Structures','code':'DSA','daily_minutes':60}],'days':2})
    assert plan.status_code==200
    tasks=client.get('/api/study/tasks',headers=h)
    assert tasks.status_code==200
    assert len(tasks.json())>=1
    task_id=tasks.json()[0]['id']
    done=client.patch(f'/api/study/tasks/{task_id}',headers=h,json={'completed':True})
    assert done.status_code==200
    analytics=client.get('/api/analytics/daily?days=7',headers=h)
    assert analytics.status_code==200
    data=analytics.json()
    assert len(data['days'])==7
    assert 'current_streak' in data
