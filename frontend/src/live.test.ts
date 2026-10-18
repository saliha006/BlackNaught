import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { connectLive, formatRate, type LiveHandlers } from './live';

class FakeSource {
  static last: FakeSource;
  listeners = new Map<string, ((e: MessageEvent) => void)[]>();
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) {
    FakeSource.last = this;
  }
  addEventListener(type: string, fn: (e: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), fn]);
  }
  emit(type: string, data: unknown = {}) {
    for (const fn of this.listeners.get(type) ?? []) fn({ data: JSON.stringify(data) } as MessageEvent);
  }
  close() {
    this.closed = true;
  }
}

let on: { [K in keyof LiveHandlers]: ReturnType<typeof vi.fn> };
let close: () => void;

beforeEach(() => {
  vi.useFakeTimers();
  on = { refetch: vi.fn(), feed: vi.fn(), stats: vi.fn(), status: vi.fn() };
  close = connectLive(on as unknown as LiveHandlers, '/stream', FakeSource as unknown as typeof EventSource);
});

afterEach(() => vi.useRealTimers());

describe('connectLive', () => {
  it('subscribes to the stream the backend serves', () => {
    expect(FakeSource.last.url).toBe('/stream');
  });

  it('pings newly active faults only, and works without a ping handler', () => {
    FakeSource.last.emit('outage', { id: 7, status: 'active' });
    const ping = vi.fn();
    connectLive({ ...on, ping } as unknown as LiveHandlers, '/stream', FakeSource as unknown as typeof EventSource);
    FakeSource.last.emit('outage', { id: 8, status: 'restored' });
    FakeSource.last.emit('outage', { id: 9, status: 'active' });
    expect(ping.mock.calls).toEqual([[9]]);
  });

  it('coalesces a burst of events into one refetch per kind', () => {
    for (let i = 0; i < 5; i++) FakeSource.last.emit('outage', { id: i });
    FakeSource.last.emit('triage');
    expect(on.refetch).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(on.refetch.mock.calls).toEqual([['outages'], ['triage']]);
    FakeSource.last.emit('outage');
    vi.advanceTimersByTime(1000);
    expect(on.refetch).toHaveBeenCalledTimes(3);
  });

  it('maps grades and resync to their refetches', () => {
    FakeSource.last.emit('grade', { graded: 3 });
    FakeSource.last.emit('resync');
    vi.advanceTimersByTime(1000);
    expect(on.refetch.mock.calls).toEqual([['grades'], ['all']]);
  });

  it('patches feed health in place and passes the event rate on', () => {
    FakeSource.last.emit('source_health', { source: 'npg', status: 'stale' });
    FakeSource.last.emit('stats', { events_per_s: 1234 });
    expect(on.feed).toHaveBeenCalledWith({ source: 'npg', status: 'stale' });
    expect(on.stats).toHaveBeenCalledWith(1234);
  });

  it('reports the connection state', () => {
    FakeSource.last.onopen!();
    FakeSource.last.onerror!();
    expect(on.status.mock.calls).toEqual([['live'], ['reconnecting']]);
  });

  it('closes the stream and drops queued refetches', () => {
    FakeSource.last.emit('outage');
    close();
    vi.advanceTimersByTime(1000);
    expect(FakeSource.last.closed).toBe(true);
    expect(on.refetch).not.toHaveBeenCalled();
  });
});

it('formats the event rate for the toggle', () => {
  expect(formatRate(0)).toBe('0.0 events/s');
  expect(formatRate(42.4)).toBe('42 events/s');
  expect(formatRate(1530)).toBe('1.5k events/s');
});
