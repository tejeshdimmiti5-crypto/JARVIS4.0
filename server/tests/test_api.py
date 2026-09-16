from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_health():
 r=client.get('/api/health');assert r.status_code==200;assert r.json()['status']=='ok';assert r.json()['vector_store']=='chroma'

def test_chat_offline():
 r=client.post('/api/chat',json={'question':'What is a stack?'});assert r.status_code==200;assert 'LIFO' in r.json()['answer']

def test_validation():
 assert client.post('/api/chat',json={'question':''}).status_code==422
 assert client.post('/api/auth/register',json={'email':'bad','password':'short'}).status_code==400

def test_protected_routes_require_auth():
 assert client.get('/api/notes').status_code in (401,403)
 assert client.get('/api/chat/history').status_code in (401,403)
 assert client.post('/api/study/plan',json={'subjects':[],'days':7}).status_code in (401,403)

def test_register_login_notes_history():
 email='test-student@example.com';password='StudentAI123!';r=client.post('/api/auth/register',json={'email':email,'password':password})
 if r.status_code==409:r=client.post('/api/auth/login',json={'email':email,'password':password})
 assert r.status_code==200;token=r.json()['access_token'];h={'Authorization':f'Bearer {token}'}
 n=client.post('/api/notes',headers=h,json={'title':'DSA Revision','content':'Stacks use LIFO.'});assert n.status_code==200
 assert client.get('/api/notes',headers=h).status_code==200
 c=client.post('/api/chat',headers=h,json={'question':'What is a stack?'});assert c.status_code==200
 hist=client.get('/api/chat/history',headers=h);assert hist.status_code==200;assert len(hist.json())>=2

def test_flashcard_endpoint_offline():
 r=client.post('/api/flashcards/generate',json={'topic':'Machine Learning','count':3});assert r.status_code==200;assert len(r.json()['cards'])>=1
