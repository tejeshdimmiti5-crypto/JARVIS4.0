from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health():
 r=client.get('/api/health');assert r.status_code==200;assert r.json()['status']=='ok';assert r.json()['vector_store']=='chroma'
def test_chat_offline():
 r=client.post('/api/chat',json={'question':'What is a stack?'});assert r.status_code==200;assert 'LIFO' in r.json()['answer']
def test_register_login_notes_history():
 email='test-student@example.com';password='StudentAI123!';r=client.post('/api/auth/register',json={'email':email,'password':password})
 if r.status_code==409:r=client.post('/api/auth/login',json={'email':email,'password':password})
 assert r.status_code==200;token=r.json()['access_token'];h={'Authorization':f'Bearer {token}'}
 n=client.post('/api/notes',headers=h,json={'title':'DSA Revision','content':'Stacks use LIFO.'});assert n.status_code==200
 assert client.get('/api/notes',headers=h).status_code==200
 c=client.post('/api/chat',headers=h,json={'question':'What is a stack?'});assert c.status_code==200
 hist=client.get('/api/chat/history',headers=h);assert hist.status_code==200;assert len(hist.json())>=2
