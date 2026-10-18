import { AuthError, login, type Role } from './api';
import { button, el } from './dom';

export interface Modal {
  body: HTMLElement;
  close(): void;
}

/**
 * A native <dialog> opened with showModal(): the browser gives it the top layer, makes the page behind it inert,
 * closes it on Escape and returns focus to the opener. One at a time, so two layers never fight over focus.
 */
export function openModal(root: HTMLElement, title: string, onClose?: () => void): Modal {
  root.querySelector<HTMLDialogElement>('dialog')?.close();
  const dialog = el('dialog', 'modal');
  const heading = el('h2', 'modal__title', title);
  heading.id = 'modal-title';
  dialog.setAttribute('aria-labelledby', heading.id);
  const body = el('div', 'modal__body');
  const closeButton = button('Close', 'l-btn l-btn--ghost modal__close', () => dialog.close());

  dialog.addEventListener('close', () => {
    dialog.remove();
    onClose?.();
  });
  // A click that lands on the dialog itself, not its content, is a click on the backdrop
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog.close();
  });

  const head = el('header', 'modal__head');
  head.append(heading, closeButton);
  dialog.append(head, body);
  root.replaceChildren(dialog);
  dialog.showModal();
  // Focus the way out first; callers with a form move it to the first field
  closeButton.focus();
  return { body, close: () => dialog.close() };
}

export interface ConfirmText {
  title: string;
  message: string;
  // Says what happens ("Send 999 packet"), never a bare "OK", so the button can't be pressed on autopilot
  action: string;
}

/** For decisions that can't be undone. Cancel takes focus, so Enter on a stray keypress backs out. */
export function confirm(root: HTMLElement, text: ConfirmText): Promise<boolean> {
  return new Promise((resolve) => {
    let confirmed = false;
    const modal = openModal(root, text.title, () => resolve(confirmed));
    const cancel = button('Cancel', 'l-btn l-btn--ghost', () => modal.close());
    const go = button(text.action, 'l-btn', () => {
      confirmed = true;
      modal.close();
    });
    const actions = el('div', 'confirm__actions');
    actions.append(cancel, go);
    modal.body.append(el('p', 'confirm__message', text.message), actions);
    cancel.focus();
  });
}

const ROLE_TEXT: Record<Role, { hint: string; user: string }> = {
  operator: { hint: 'Approving sends a 999 context packet or a public alert, so it needs the operator login.', user: 'operator' },
  household: { hint: 'Each household sees only its own home. The demo logins are in households.txt on the VM.', user: 'home-1' },
};

/** Resolves with the login name once the person signs in with the role the next request needs, or null if they give up. */
export function askLogin(root: HTMLElement, role: Role): Promise<string | null> {
  return new Promise((resolve) => {
    let signedIn: string | null = null;
    const modal = openModal(root, role === 'operator' ? 'Operator sign-in' : 'Household sign-in', () => resolve(signedIn));
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
        const who = name.value.trim();
        const got = await login(who, pass.value);
        if (got !== role) {
          error.textContent = `That's a ${got} login; this needs the ${role} one.`;
          return;
        }
        signedIn = who;
        modal.close();
      } catch (err) {
        error.textContent = err instanceof AuthError ? 'Wrong login or passphrase.' : `Couldn't sign in: ${(err as Error).message}`;
      } finally {
        submit.disabled = false;
      }
    });
    modal.body.append(form);
    // The login name is prefilled, so the passphrase is the first thing to type
    pass.focus();
  });
}
