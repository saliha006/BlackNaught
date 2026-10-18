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

// Escape and focus-return are the browser's job with showModal(); these check what our code does around it
describe('openModal', () => {
  it('opens a modal dialog with focus on Close, and cleans up when it closes', async () => {
    const { openModal } = await load(vi.fn());
    const root = document.createElement('div');
    document.body.append(root);
    const closed = vi.fn();
    const modal = openModal(root, 'Title', closed);
    const dialog = root.querySelector('dialog')!;
    expect(dialog.open).toBe(true);
    expect(dialog.getAttribute('aria-labelledby')).toBe('modal-title');
    expect((document.activeElement as HTMLElement).textContent).toBe('Close');
    modal.close();
    expect(closed).toHaveBeenCalledOnce();
    expect(root.querySelector('dialog')).toBeNull();
  });

  it('closes on a backdrop click but not on a click inside, and replaces an open dialog', async () => {
    const { openModal } = await load(vi.fn());
    const root = document.createElement('div');
    const first = vi.fn();
    openModal(root, 'First', first);
    const dialog = root.querySelector('dialog')!;
    root.querySelector<HTMLElement>('.modal__body')!.click();
    expect(dialog.open).toBe(true);
    openModal(root, 'Second');
    expect(first).toHaveBeenCalledOnce();
    root.querySelector('dialog')!.click();
    expect(root.querySelector('dialog')).toBeNull();
  });
});

describe('askLogin', () => {
  it('resolves with the login name once the right role signs in', async () => {
    const login = vi.fn().mockResolvedValue('operator');
    const { askLogin } = await load(login);
    const root = document.createElement('div');
    const result = askLogin(root, 'operator');
    submit(root, 'pw');
    expect(await result).toBe('operator');
    expect(login).toHaveBeenCalledWith('operator', 'pw');
  });

  it('refuses the wrong role, explains a bad passphrase, and resolves null when closed', async () => {
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
    root.querySelector<HTMLButtonElement>('.modal__close')!.click();
    expect(await result).toBeNull();
  });
});
