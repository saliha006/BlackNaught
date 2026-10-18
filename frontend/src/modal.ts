import { AuthError, login, type Role } from './api';
import { button, el } from './dom';

export interface Modal {
  body: HTMLElement;
  close(): void;
}

/** One dialog at a time: opening another replaces it, so focus and Escape never fight over two layers. */
export function openModal(root: HTMLElement, title: string, onClose?: () => void): Modal {
  const opener = document.activeElement as HTMLElement | null;
  const overlay = el('div', 'modal');
  const box = el('section', 'modal__box');
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  const heading = el('h2', 'modal__title', title);
  heading.id = 'modal-title';
  box.setAttribute('aria-labelledby', heading.id);
  const body = el('div', 'modal__body');

  const close = () => {
    overlay.remove();
    document.removeEventListener('keydown', onKey);
    opener?.focus();
    onClose?.();
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') close();
  };
  document.addEventListener('keydown', onKey);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });

  const head = el('header', 'modal__head');
  head.append(heading, button('Close', 'l-btn l-btn--ghost modal__close', close));
  box.append(head, body);
  overlay.append(box);
  root.replaceChildren(overlay);
  return { body, close };
}

const ROLE_TEXT: Record<Role, { hint: string; user: string }> = {
  operator: { hint: 'Approving sends a 999 context packet or a public alert, so it needs the operator login.', user: 'operator' },
  household: { hint: 'Each household sees only its own home. The demo logins are in households.txt on the VM.', user: 'home-1' },
};

/** Resolves true once the person is signed in with the role the next request needs. */
export function askLogin(root: HTMLElement, role: Role): Promise<boolean> {
  return new Promise((resolve) => {
    let done = false;
    const modal = openModal(root, role === 'operator' ? 'Operator sign-in' : 'Household sign-in', () => {
      if (!done) resolve(false);
    });
    const form = el('form', 'login');
    const name = el('input', 'login__input');
    name.name = 'login';
    name.autocomplete = 'username';
    name.required = true;
    name.value = ROLE_TEXT[role].user;
    const pass = el('input', 'login__input');
    pass.type = 'password';
    pass.name = 'passphrase';
    pass.autocomplete = 'current-password';
    pass.required = true;
    const error = el('p', 'login__error');
    error.setAttribute('role', 'alert');
    const submit = el('button', 'l-btn', 'Sign in');
    submit.type = 'submit';

    const field = (text: string, input: HTMLInputElement) => {
      const label = el('label', 'login__field', text);
      label.append(input);
      return label;
    };
    form.append(el('p', 'login__hint', ROLE_TEXT[role].hint), field('Login', name), field('Passphrase', pass), error, submit);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      submit.disabled = true;
      error.textContent = '';
      try {
        const got = await login(name.value.trim(), pass.value);
        if (got !== role) {
          error.textContent = `That's a ${got} login; this needs the ${role} one.`;
          return;
        }
        done = true;
        modal.close();
        resolve(true);
      } catch (err) {
        error.textContent = err instanceof AuthError ? 'Wrong login or passphrase.' : `Couldn't sign in: ${(err as Error).message}`;
      } finally {
        submit.disabled = false;
      }
    });
    modal.body.append(form);
    (role === 'operator' ? pass : name).focus();
  });
}
