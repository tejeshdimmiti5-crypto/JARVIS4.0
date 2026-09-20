from __future__ import annotations
import hashlib,os
from typing import Any
import chromadb,httpx
GEMINI_API_KEY=os.getenv('GEMINI_API_KEY','');EMBEDDING_MODEL=os.getenv('GEMINI_EMBEDDING_MODEL','gemini-embedding-001');DB_PATH=os.getenv('CHROMA_PATH','./data/chroma')
os.makedirs(os.path.dirname(DB_PATH) or '.',exist_ok=True)
_client=chromadb.PersistentClient(path=DB_PATH);_collection=_client.get_or_create_collection(name='studentai_documents',metadata={'hnsw:space':'cosine'})
async def embed(text:str)->list[float]:
 if not GEMINI_API_KEY:raise RuntimeError('GEMINI_API_KEY is required for semantic indexing')
 url=f'https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent';payload={'model':f'models/{EMBEDDING_MODEL}','content':{'parts':[{'text':text}]}}
 async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:r=await client.post(url,headers={'x-goog-api-key':GEMINI_API_KEY},json=payload)
 if r.status_code>=400:raise RuntimeError(r.text[:500])
 return r.json()['embedding']['values']
async def index_chunks(document_id:str,chunks:list[dict[str,Any]])->int:
 if not chunks:return 0
 ids=[];texts=[];metas=[];vectors=[]
 for i,c in enumerate(chunks):
  text=c['text'].strip()
  if not text:continue
  ids.append(hashlib.sha256(f'{document_id}:{i}'.encode()).hexdigest());texts.append(text);metas.append({'document_id':document_id,'page':c.get('page',1),'chunk':i});vectors.append(await embed(text))
 if ids:_collection.upsert(ids=ids,documents=texts,metadatas=metas,embeddings=vectors)
 return len(ids)
async def semantic_search(query:str,document_id:str|None=None,top_k:int=5)->list[dict[str,Any]]:
 vector=await embed(query);kwargs={'query_embeddings':[vector],'n_results':max(1,min(top_k,20))}
 if document_id:kwargs['where']={'document_id':document_id}
 result=_collection.query(**kwargs);docs=result.get('documents',[[]])[0];metas=result.get('metadatas',[[]])[0];distances=result.get('distances',[[]])[0]
 return [{'text':d,'page':m.get('page',1),'document_id':m.get('document_id'),'distance':distances[i] if i<len(distances) else None} for i,(d,m) in enumerate(zip(docs,metas))]
