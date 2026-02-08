const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

function getToken(): string | null {
  return localStorage.getItem('token');
}

export async function apiLogin(username: string, password: string) {
  const r = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username, password})
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function http(path: string, opts: RequestInit = {}) {
  const token = getToken();
  const headers: any = { 'Content-Type': 'application/json', ...(opts.headers||{}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const r = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export const apiGetPlans = () => http('/api/plans');
export const apiGetPlan  = (id:number) => http(`/api/plans/${id}`);
export const apiCreatePlan = (payload:any) => http('/api/plans', {method:'POST', body: JSON.stringify(payload)});
export const apiPlanAction = (id:number, a:'start'|'pause'|'resume'|'stop') => http(`/api/plans/${id}/${a}`, {method:'POST', body:'{}'});
export const apiTaskAction = (id:number, a:'cancel'|'retry') => http(`/api/tasks/${id}/${a}`, {method:'POST', body:'{}'});
export const oozieJobInfo = (planId:number, jobId:string) => http(`/api/oozie/job/${encodeURIComponent(jobId)}?plan_id=${planId}`);

export function wsUrl(): string {
  const base = API_BASE.replace('http://','ws://').replace('https://','wss://');
  const token = getToken();
  return `${base}/ws?token=${encodeURIComponent(token||'')}`;
}
