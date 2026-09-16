import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BookOpen, FileText, MessageSquare, Brain, BarChart3, Upload, Send, Settings, Plus, Sparkles } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const tabs = [
  ['chat', 'Study Chat', MessageSquare], ['pdf', 'PDF Study', FileText],
  ['notes', 'My Notes', BookOpen], ['quiz', 'Quiz Me', Brain], ['progress', 'Progress', BarChart3]
];

function App() {
  const [tab, setTab] = useState('chat');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [pdf, setPdf] = useState(null);
  const [pdfText, setPdfText] = useState('');
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState(() => JSON.parse(localStorage.getItem('studentai-notes') || '[]'));
  const [questions, setQuestions] = useState(0);

  async function ask(q = question, task = 'answer', context = pdfText) {
    const text = q.trim(); if (!text || loading) return;
    setQuestion(''); setMessages(m => [...m, { role: 'user', text }]); setLoading(true); setQuestions(n => n + 1);
    try {
      const r = await fetch(`${API}/api/chat`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({question:text, context, task}) });
      const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'Request failed');
      setMessages(m => [...m, { role: 'ai', text: data.answer, model: data.model }]);
    } catch (e) { setMessages(m => [...m, {role:'ai', text:`Backend connection error: ${e.message}. Start the FastAPI server on port 8000.`}]); }
    finally { setLoading(false); }
  }

  async function uploadPdf(file) {
    if (!file) return; setPdf(file); setLoading(true);
    try {
      const form = new FormData(); form.append('file', file);
      const r = await fetch(`${API}/api/pdf/extract`, {method:'POST', body:form});
      const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'PDF extraction failed');
      setPdfText(data.text); setMessages(m => [...m, {role:'ai', text:`Loaded ${data.filename} — ${data.pages} pages. Ask questions about it or use Summarize PDF.`}]);
    } catch(e) { setMessages(m => [...m, {role:'ai', text:e.message}]); }
    finally { setLoading(false); }
  }

  function addNote() {
    const title = prompt('Note title'); const body = prompt('Revision note');
    if (!title || !body) return; const next = [{id:Date.now(), title, body}, ...notes]; setNotes(next); localStorage.setItem('studentai-notes', JSON.stringify(next));
  }

  return <div className="shell">
    <aside className="sidebar"><div className="brand"><span><Sparkles size={18}/></span> StudentAI</div><button className="new"><Plus size={17}/> New session</button><div className="label">WORKSPACE</div>{tabs.map(([id,name,Icon]) => <button key={id} className={`nav ${tab===id?'active':''}`} onClick={()=>setTab(id)}><Icon size={18}/>{name}</button>)}<div className="side-bottom"><div className="ai-badge"><Sparkles size={16}/><div><b>RAG Study Engine</b><small>PDF → retrieval → AI</small></div></div></div></aside>
    <main className="main"><header><div><div className="eyebrow">AI STUDY WORKSPACE</div><h1>{tabs.find(x=>x[0]===tab)?.[1]}</h1></div><button className="icon"><Settings size={19}/></button></header>
      {tab==='chat' && <section className="content chat"><div className="hero"><div className="orb"><Sparkles/></div><h2>Study smarter. Build understanding.</h2><p>Ask questions, upload lecture PDFs, create revision notes and practice with AI.</p><div className="chips">{['Explain supervised learning simply','Give me 5 DBMS revision questions','Explain Big Data for an exam','Make a 7-day study plan'].map(x=><button key={x} onClick={()=>ask(x)}>{x}</button>)}</div></div><div className="messages">{messages.map((m,i)=><div key={i} className={`msg ${m.role}`}><div className="msg-label">{m.role==='ai'?'StudentAI':'You'}</div><div>{m.text}</div>{m.model && <small>Model: {m.model}</small>}</div>)}{loading&&<div className="msg ai"><div className="msg-label">StudentAI</div>Thinking…</div>}</div><div className="composer"><textarea value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask()}}} placeholder="Ask anything about your studies…"/><button onClick={()=>ask()}><Send size={18}/></button></div></section>}
      {tab==='pdf' && <section className="content"><div className="card upload"><Upload size={32}/><h2>Study from a PDF</h2><p>Upload lecture notes, textbooks or question papers. Text is extracted by the backend and can be sent to the AI.</p><label className="drop"><Upload size={20}/> Choose PDF<input type="file" accept="application/pdf" onChange={e=>uploadPdf(e.target.files?.[0])}/></label>{pdf&&<div className="file">{pdf.name}<span>{pdfText.length.toLocaleString()} characters</span></div>}<div className="actions"><button className="primary" disabled={!pdfText||loading} onClick={()=>ask('Create an exam-ready summary with key concepts, definitions, important steps/formulas and likely questions.','summary',pdfText)}><Sparkles size={17}/> Summarize PDF</button><button className="secondary" onClick={()=>{setPdf(null);setPdfText('')}}>Clear</button></div></div></section>}
      {tab==='notes' && <section className="content"><div className="section-title"><div><h2>My Notes</h2><p>Keep your most important revision points in one place.</p></div><button className="primary" onClick={addNote}><Plus size={17}/> Add note</button></div><div className="grid">{notes.map(n=><article className="note" key={n.id}><h3>{n.title}</h3><p>{n.body}</p></article>)}{!notes.length&&<div className="empty">No notes yet. Save your first revision point.</div>}</div></section>}
      {tab==='quiz' && <section className="content"><div className="card quiz"><Brain size={30}/><h2>Quiz mode</h2><p>Use Study Chat to generate a quiz from your current PDF, or ask: “Create 10 MCQs from this chapter.”</p><button className="primary" onClick={()=>{setTab('chat');ask('Create 5 multiple-choice questions on Machine Learning with answers and explanations.','quiz')}}><Sparkles size={17}/> Generate AI Quiz</button></div></section>}
      {tab==='progress' && <section className="content"><div className="stats"><div><span>AI questions</span><b>{questions}</b></div><div><span>Saved notes</span><b>{notes.length}</b></div><div><span>PDF loaded</span><b>{pdf?1:0}</b></div></div><div className="card"><h2>Your study loop</h2><p>Upload → Understand → Ask → Note → Quiz → Review.</p><div className="bar"><span style={{width:`${Math.min(100, questions*10+notes.length*15)}%`}}/></div></div></section>}
    </main>
  </div>
}

createRoot(document.getElementById('root')).render(<App />);
