import type {
  AgentDecision,
  AreaRisk,
  AuditVerify,
  Cell,
  DecisionState,
  Grades,
  GridStress,
  MyHome,
  Outage,
  SourceHealth,
  Triage,
} from './types';

export const isLive = import.meta.env.MODE === 'live';

// Lazy so the live build never ships the fixtures.
const fixtures = import.meta.glob<{ default: unknown }>('../../fixtures/api/*.json');
const capSample = import.meta.glob<string>('../../fixtures/api/cap_alert_sample.xml', { query: '?raw', import: 'default' });

async function fixture<T>(name: string): Promise<T> {
  const load = fixtures[`../../fixtures/api/${name}.json`];
  if (!load) throw new Error(`No fixture named ${name}.json`);
  return (await load()).default as T;
}

/** A failure talking to the backend, kept apart from bugs in this app so only these get the "check the tunnel" hint. */
export class ApiError extends Error {}

/** 401 / 403: the view needs a login (or a different one), which the UI can fix by asking for it. */
export class AuthError extends ApiError {}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(path, init).catch((e: Error) => {
    throw new ApiError(`${path}: ${e.message}`);
  });
  if (res.status === 401 || res.status === 403) throw new AuthError(`${path} returned ${res.status}`);
  if (!res.ok) throw new ApiError(`${path} returned ${res.status}`);
  return res;
}

async function live<T>(path: string): Promise<T> {
  return (await request(path, { headers: { Accept: 'application/json' } })).json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T | null> {
  const res = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return res.status === 204 ? null : (res.json() as Promise<T>);
}

export const getOutages = () =>
  isLive ? live<Outage[]>('/api/outages?status=active') : fixture<Outage[]>('outages');

export const getCells = () =>
  isLive ? live<Cell[]>('/api/cells?level=1') : fixture<Cell[]>('cells');

export const getTriage = (limit = 3) =>
  isLive ? live<Triage>(`/api/triage?limit=${limit}`) : fixture<Triage>('triage');

export const getGrades = () => (isLive ? live<Grades>('/api/agent/grades') : fixture<Grades>('agent_grades'));

export const getAreaRisk = () => (isLive ? live<AreaRisk[]>('/api/areas/risk') : fixture<AreaRisk[]>('areas_risk'));

export const getStress = () =>
  isLive ? live<GridStress>('/api/grids/gb/stress') : fixture<GridStress>('grid_stress_gb');

export const getSourcesHealth = () =>
  isLive
    ? live<{ sources: SourceHealth[] }>('/api/sources/health')
    : fixture<{ sources: SourceHealth[] }>('sources_health');

export const getDecisions = () =>
  isLive ? live<AgentDecision[]>('/api/agent/decisions?limit=50') : fixture<AgentDecision[]>('agent_decisions');

export const getAudit = () => (isLive ? live<AuditVerify>('/api/audit/verify') : fixture<AuditVerify>('audit_verify'));

export const getMyHome = () => (isLive ? live<MyHome>('/api/me/home') : fixture<MyHome>('me_home'));

export type Role = 'operator' | 'household';

export async function login(name: string, passphrase: string): Promise<Role> {
  if (!isLive) return name.startsWith('home') ? 'household' : 'operator';
  return (await post<{ role: Role }>('/api/auth/login', { login: name, passphrase }))!.role;
}

export const logout = async () => {
  if (isLive) await post('/api/auth/logout');
};

/** Operator only; the session cookie (HttpOnly, SameSite=Strict) rides along on same-origin requests. */
export async function decide(decisionId: string, approve: boolean): Promise<DecisionState> {
  if (!isLive) {
    const sample = await fixture<DecisionState>('decision_state');
    return { ...sample, decision_id: decisionId, state: approve ? 'approved' : 'rejected' };
  }
  return (await post<DecisionState>(`/api/decisions/${encodeURIComponent(decisionId)}/approve`, { approve }))!;
}

/** The CAP 1.2 XML; the backend only serves it once a person has approved the alert. */
export async function getCapXml(decisionId: string): Promise<string> {
  if (!isLive) return Object.values(capSample)[0]();
  return (await request(`/api/alerts/cap/${encodeURIComponent(decisionId)}`, { headers: { Accept: 'application/cap+xml' } })).text();
}
