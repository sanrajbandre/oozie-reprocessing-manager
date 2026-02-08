import React, { useEffect, useState } from 'react'
import { apiCreatePlan, apiGetPlan, apiGetPlans, apiLogin, apiPlanAction, apiTaskAction, oozieJobInfo, wsUrl } from '../api'

type Plan = {
  id:number; name:string; description:string; status:string; oozie_url:string; use_rest:boolean; max_concurrency:number;
  created_by:string; created_at:string; updated_at:string;
}

function Login({onDone}:{onDone:()=>void}) {
  const [username,setUsername] = useState('admin');
  const [password,setPassword] = useState('admin123');
  const [err,setErr] = useState<string|null>(null);

  async function submit(e:any){
    e.preventDefault();
    setErr(null);
    try{
      const res = await apiLogin(username,password);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('role', res.role);
      onDone();
    }catch(ex:any){
      setErr(String(ex?.message||ex));
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Login</h2>
        <p className="muted">Use your admin/viewer credentials</p>
        <form onSubmit={submit}>
          <div className="row">
            <div className="col">
              <label className="muted">Username</label>
              <input className="input" value={username} onChange={e=>setUsername(e.target.value)} />
            </div>
            <div className="col">
              <label className="muted">Password</label>
              <input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
            </div>
          </div>
          <div style={{marginTop:12}}>
            <button className="btn" type="submit">Sign in</button>
          </div>
          {err && <pre style={{marginTop:12}}>{err}</pre>}
        </form>
      </div>
    </div>
  )
}

function PlanCreate({onCreated}:{onCreated:(p:any)=>void}) {
  const [name,setName] = useState('Sample Plan');
  const [oozieUrl,setOozieUrl] = useState('http://10.X.X.X:11000/oozie');
  const [maxConc,setMaxConc] = useState(2);
  const [useRest,setUseRest] = useState(false);
  const [tasks,setTasks] = useState<any[]>([
    {name:'wf-failed-only', type:'workflow', job_id:'0000000-000000000000000-oozie-oozi-W', wf_failnodes:true, wf_skip_nodes:'', refresh:false, failed:false, action:'', date:'', coordinator:'', extra_props:{}}
  ]);
  const [err,setErr] = useState<string|null>(null);

  function updateTask(i:number, key:string, val:any){
    const copy = [...tasks];
    copy[i] = {...copy[i], [key]:val};
    setTasks(copy);
  }
  function addTask(){
    setTasks([...tasks, {name:'new-task', type:'workflow', job_id:'', wf_failnodes:false, wf_skip_nodes:'', refresh:false, failed:false, action:'', date:'', coordinator:'', extra_props:{}}]);
  }

  async function create(){
    setErr(null);
    try{
      const payload = {name, oozie_url: oozieUrl, max_concurrency:maxConc, use_rest:useRest, tasks};
      const p = await apiCreatePlan(payload);
      onCreated(p);
    }catch(ex:any){
      setErr(String(ex?.message||ex));
    }
  }

  return (
    <div className="card">
      <h3>Create Plan</h3>
      <div className="row">
        <div className="col">
          <label className="muted">Plan Name</label>
          <input className="input" value={name} onChange={e=>setName(e.target.value)} />
        </div>
        <div className="col">
          <label className="muted">Oozie URL</label>
          <input className="input" value={oozieUrl} onChange={e=>setOozieUrl(e.target.value)} />
        </div>
      </div>
      <div className="row" style={{marginTop:10}}>
        <div className="col">
          <label className="muted">Max Concurrency</label>
          <input className="input" type="number" value={maxConc} onChange={e=>setMaxConc(parseInt(e.target.value||'1'))}/>
        </div>
        <div className="col">
          <label className="muted">Use REST rerun</label>
          <div style={{marginTop:10}}>
            <input type="checkbox" checked={useRest} onChange={e=>setUseRest(e.target.checked)} /> <span className="muted">Use Oozie REST rerun (fallback to CLI)</span>
          </div>
        </div>
      </div>

      <div style={{marginTop:12}}>
        <div className="topbar">
          <h4 style={{margin:0}}>Tasks</h4>
          <button className="btn secondary" onClick={addTask}>+ Add task</button>
        </div>
        {tasks.map((t, idx)=>(
          <div key={idx} className="card" style={{marginTop:10}}>
            <div className="row">
              <div className="col">
                <label className="muted">Name</label>
                <input className="input" value={t.name} onChange={e=>updateTask(idx,'name',e.target.value)} />
              </div>
              <div className="col">
                <label className="muted">Type</label>
                <select className="input" value={t.type} onChange={e=>updateTask(idx,'type',e.target.value)}>
                  <option value="workflow">workflow</option>
                  <option value="coordinator">coordinator</option>
                  <option value="bundle">bundle</option>
                </select>
              </div>
              <div className="col">
                <label className="muted">Job ID</label>
                <input className="input" value={t.job_id} onChange={e=>updateTask(idx,'job_id',e.target.value)} />
              </div>
            </div>

            {t.type === 'workflow' && (
              <div className="row" style={{marginTop:10}}>
                <div className="col">
                  <label className="muted">failnodes (only failed)</label>
                  <input type="checkbox" checked={!!t.wf_failnodes} onChange={e=>updateTask(idx,'wf_failnodes',e.target.checked)} />
                </div>
                <div className="col">
                  <label className="muted">skip nodes (comma)</label>
                  <input className="input" value={t.wf_skip_nodes||''} onChange={e=>updateTask(idx,'wf_skip_nodes',e.target.value)} />
                </div>
              </div>
            )}

            {t.type !== 'workflow' && (
              <div className="row" style={{marginTop:10}}>
                <div className="col">
                  <label className="muted">action (coord)</label>
                  <input className="input" value={t.action||''} onChange={e=>updateTask(idx,'action',e.target.value)} />
                </div>
                <div className="col">
                  <label className="muted">date</label>
                  <input className="input" value={t.date||''} onChange={e=>updateTask(idx,'date',e.target.value)} />
                </div>
                <div className="col">
                  <label className="muted">coordinator (bundle)</label>
                  <input className="input" value={t.coordinator||''} onChange={e=>updateTask(idx,'coordinator',e.target.value)} />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{marginTop:12}}>
        <button className="btn" onClick={create}>Create Plan</button>
      </div>
      {err && <pre style={{marginTop:12}}>{err}</pre>}
    </div>
  )
}

function PlanDetails({planId, onBack}:{planId:number; onBack:()=>void}) {
  const [data,setData] = useState<any>(null);
  const [err,setErr] = useState<string|null>(null);
  const role = localStorage.getItem('role') || 'viewer';

  async function refresh(){
    try{
      const d = await apiGetPlan(planId);
      setData(d);
      setErr(null);
    }catch(ex:any){
      setErr(String(ex?.message||ex));
    }
  }

  useEffect(()=>{ refresh(); }, [planId]);

  useEffect(()=>{
    const url = wsUrl();
    const ws = new WebSocket(url);
    ws.onopen = ()=>{ ws.send('ping'); };
    ws.onmessage = (m)=>{
      try{
        const e = JSON.parse(m.data);
        if(e.plan_id === planId){
          refresh();
        }
      }catch{}
    };
    return ()=>ws.close();
  }, [planId]);

  async function doPlanAction(a:'start'|'pause'|'resume'|'stop'){
    await apiPlanAction(planId,a);
    await refresh();
  }
  async function doTaskAction(taskId:number, a:'cancel'|'retry'){
    await apiTaskAction(taskId,a);
    await refresh();
  }

  async function showOozie(jobId:string){
    try{
      const info = await oozieJobInfo(planId, jobId);
      alert(JSON.stringify(info, null, 2));
    }catch(ex:any){
      alert(String(ex?.message||ex));
    }
  }

  if(err) return <div className="container"><pre>{err}</pre></div>
  if(!data) return <div className="container"><div className="card">Loading...</div></div>

  const plan:Plan = data.plan;
  const tasks:any[] = data.tasks || [];
  const total = tasks.length;
  const done = tasks.filter(t=>['SUCCESS','FAILED','CANCELED','SKIPPED'].includes(t.status)).length;
  const pct = total ? Math.round((done/total)*100) : 0;

  return (
    <div className="container">
      <div className="card">
        <div className="topbar">
          <div>
            <button className="btn secondary" onClick={onBack}>← Back</button>
            <h2 style={{margin:'10px 0 0 0'}}>{plan.name}</h2>
            <div className="muted">Status: <span className="badge">{plan.status}</span> • Progress: {done}/{total} ({pct}%) • Concurrency: {plan.max_concurrency}</div>
          </div>
          <div style={{display:'flex', gap:8}}>
            <button className="btn" disabled={role!=='admin'} onClick={()=>doPlanAction('start')}>Start</button>
            <button className="btn secondary" disabled={role!=='admin'} onClick={()=>doPlanAction('pause')}>Pause</button>
            <button className="btn" disabled={role!=='admin'} onClick={()=>doPlanAction('resume')}>Resume</button>
            <button className="btn danger" disabled={role!=='admin'} onClick={()=>doPlanAction('stop')}>Stop</button>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Tasks</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th><th>Name</th><th>Type</th><th>Job ID</th><th>Status</th><th>Exit</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(t=>(
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.name}</td>
                <td><span className="badge">{t.type}</span></td>
                <td style={{maxWidth:340}}>{t.job_id}</td>
                <td><span className="badge">{t.status}</span></td>
                <td>{t.exit_code ?? ''}</td>
                <td>
                  <div style={{display:'flex', gap:6, flexWrap:'wrap'}}>
                    <button className="btn secondary" onClick={()=>showOozie(t.job_id)}>Oozie Info</button>
                    <button className="btn secondary" disabled={role!=='admin'} onClick={()=>doTaskAction(t.id,'retry')}>Retry</button>
                    <button className="btn danger" disabled={role!=='admin'} onClick={()=>doTaskAction(t.id,'cancel')}>Cancel</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <h4 style={{marginTop:16}}>Task Logs (latest)</h4>
        {tasks.slice(-3).reverse().map(t=>(
          <div key={t.id} className="card">
            <div className="muted">Task #{t.id} • {t.name} • {t.status}</div>
            <div className="muted">Command:</div>
            <pre>{t.command || ''}</pre>
            <div className="row">
              <div className="col">
                <div className="muted">stdout</div>
                <pre>{t.stdout || ''}</pre>
              </div>
              <div className="col">
                <div className="muted">stderr</div>
                <pre>{t.stderr || ''}</pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function App(){
  const [authed,setAuthed] = useState<boolean>(!!localStorage.getItem('token'));
  const [plans,setPlans] = useState<Plan[]>([]);
  const [selected,setSelected] = useState<number|null>(null);
  const [err,setErr] = useState<string|null>(null);

  async function loadPlans(){
    try{
      const p = await apiGetPlans();
      setPlans(p);
      setErr(null);
    }catch(ex:any){
      setErr(String(ex?.message||ex));
    }
  }

  useEffect(()=>{ if(authed) loadPlans(); }, [authed]);

  useEffect(()=>{
    if(!authed) return;
    const ws = new WebSocket(wsUrl());
    ws.onopen = ()=>ws.send('ping');
    ws.onmessage = ()=>{ loadPlans(); };
    return ()=>ws.close();
  }, [authed]);

  if(!authed) return <Login onDone={()=>setAuthed(true)} />

  if(selected !== null) return <PlanDetails planId={selected} onBack={()=>setSelected(null)} />

  return (
    <div className="container">
      <div className="topbar">
        <h2 style={{margin:0}}>Oozie Reprocessing Manager</h2>
        <button className="btn secondary" onClick={()=>{localStorage.removeItem('token'); setAuthed(false);}}>Logout</button>
      </div>

      <PlanCreate onCreated={(p)=>{ setSelected(p.id); loadPlans(); }} />

      <div className="card">
        <h3>Plans</h3>
        {err && <pre>{err}</pre>}
        <table className="table">
          <thead>
            <tr>
              <th>ID</th><th>Name</th><th>Status</th><th>Concurrency</th><th>Owner</th><th>Open</th>
            </tr>
          </thead>
          <tbody>
            {plans.map(p=>(
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.name}</td>
                <td><span className="badge">{p.status}</span></td>
                <td>{p.max_concurrency}</td>
                <td>{p.created_by}</td>
                <td><button className="btn secondary" onClick={()=>setSelected(p.id)}>Open</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">Live updates via WebSocket. Worker publishes execution events to Redis; API broadcasts to connected clients.</p>
      </div>
    </div>
  )
}
