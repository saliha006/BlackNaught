// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.resetModules();
  vi.doUnmock('./api');
});

async function load(login: (name: string, pass: string) => Promise<string>) {
  vi.doMock('./api', async (orig) => ({ ...(await orig<typeof import('./api')>()), login }));
  return import('./modal');
}

const submit = (root: HTMLElement, pass: string) => {
  root.querySelector<HTMLInputElement>('input[type=password]')!.value = pass;
  root.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
};

describe('openModal', () => {
  it('closes on Escape and on the backdrop, calling back each time', async () => {
    const { openModal } = await load(vi.fn());
    const root = document.createElement('div');
    const closed = vi.fn();
    openModal(root, 'Title', closed);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(root.childElementCount).toBe(0);
    openModal(root, 'Again', closed);
    root.querySelector<HTMLElement>('.modal')!.click();
    expect(closed).toHaveBeenCalledTimes(2);
  });
});

describe('askLogin', () => {
  it('resolves true once the right role signs in', async () => {
    const login = vi.fn().mockResolvedValue('operator');
    const { askLogin } = await load(login);
    const root = document.createElement('div');
    const result = askLogin(root, 'operator');
    submit(root, 'pw');
    expect(await result).toBe(true);
    expect(login).toHaveBeenCalledWith('operator', 'pw');
  });

  it('refuses the wrong role, explains a bad passphrase, and resolves false when closed', async () => {
    const login = vi
      .fn()
      .mockResolvedValueOnce('household')
      // the modal sees a fresh copy of ./api after resetModules, so the error must come from that copy
      .mockImplementationOnce(async () => {
        const { AuthError } = await import('./api');
        throw new AuthError('401');
      })
      .mockRejectedValueOnce(new Error('timeout'));
    const { askLogin } = await load(login);
    const root = document.createElement('div');
    const result = askLogin(root, 'operator');
    submit(root, 'pw');
    await vi.waitFor(() => expect(root.textContent).toContain('a household login'));
    submit(root, 'pw');
    await vi.waitFor(() => expect(root.textContent).toContain('Wrong login or passphrase'));
    submit(root, 'pw');
    await vi.waitFor(() => expect(root.textContent).toContain('Couldn'));
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(await result).toBe(false);
  });
});
