import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe('fixture mode', () => {
  it('loads outages and cells from fixtures/api', async () => {
    const api = await import('./api');
    expect(api.isLive).toBe(false);
    expect((await api.getOutages()).map((x) => x.id)).toEqual([101, 102, 103]);
    expect((await api.getCells())[0].cell_id).toBe('L1:5153:-6');
    expect((await api.getTriage()).items[0].patient_ref).toBe('P-3F2A1C');
    expect((await api.getSourcesHealth()).sources.map((s) => s.source)).toContain('npg');
    expect((await api.getGrades()).by_horizon.length).toBeGreaterThan(0);
    expect((await api.getAreaRisk())[0].district).toBe('Manchester');
    expect((await api.getStress()).state).toBe('NORMAL');
  });
});

describe('live mode', () => {
  it('calls the API and surfaces HTTP errors', async () => {
    vi.stubEnv('MODE', 'live');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('[]', { status: 200 }))
      .mockResolvedValueOnce(new Response('', { status: 502 }));
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    expect(await api.getOutages()).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/outages?status=active');
    const failed = api.getCells();
    await expect(failed).rejects.toThrow('/api/cells?level=1 returned 502');
    await expect(failed).rejects.toBeInstanceOf(api.ApiError);
  });

  it('marks a dropped connection as an API failure, naming the path', async () => {
    vi.stubEnv('MODE', 'live');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const api = await import('./api');

    const failed = api.getTriage();
    await expect(failed).rejects.toBeInstanceOf(api.ApiError);
    await expect(failed).rejects.toThrow('/api/triage?limit=3: Failed to fetch');
  });
});

describe('decisions, audit, my home and login', () => {
  it('serves every new view from fixtures', async () => {
    const api = await import('./api');
    expect((await api.getDecisions())[0].state).toBe('awaiting_approval');
    expect((await api.getAudit()).ok).toBe(true);
    expect((await api.getMyHome()).risk.layers).toHaveLength(3);
    expect(await api.login('home-ama', 'x')).toBe('household');
    expect(await api.login('operator', 'x')).toBe('operator');
    expect((await api.decide('d-1', false)).state).toBe('rejected');
    expect(await api.getCapXml('d-1')).toContain('urn:oasis:names:tc:emergency:cap:1.2');
    await expect(api.logout()).resolves.toBeUndefined();
  });

  it('posts approvals with JSON and treats 401 as a login problem', async () => {
    vi.stubEnv('MODE', 'live');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('{"role":"operator"}', { status: 200 }))
      .mockResolvedValueOnce(new Response('{"decision_id":"a b","state":"approved","audit_seq":7}', { status: 200 }))
      .mockResolvedValueOnce(new Response('', { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response('<alert/>', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    expect(await api.login('operator', 'pw')).toBe('operator');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ login: 'operator', passphrase: 'pw' });
    expect((await api.decide('a b', true)).state).toBe('approved');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/decisions/a%20b/approve');
    await expect(api.getMyHome()).rejects.toBeInstanceOf(api.AuthError);
    await expect(api.logout()).resolves.toBeUndefined();
    expect(await api.getCapXml('d')).toBe('<alert/>');
  });
});
