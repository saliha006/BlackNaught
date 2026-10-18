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
    await expect(api.getCells()).rejects.toThrow('/api/cells?level=1 returned 502');
  });
});
