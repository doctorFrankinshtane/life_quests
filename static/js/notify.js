/** Системные уведомления — маленькие окна в правом нижнем углу. */

import { eventNote, t } from './i18n.js';

const HOLD_MS = 4200;

function panel(title, text, kind) {
  const box = document.createElement('div');
  box.className = 'toast';
  if (kind) box.dataset.kind = kind;

  const head = document.createElement('header');
  head.className = 'title';

  const caption = document.createElement('span');
  caption.className = 't';
  caption.textContent = title;

  const close = document.createElement('button');
  close.className = 'btn';
  close.type = 'button';
  close.textContent = '×';
  close.setAttribute('aria-label', t('toast.close'));
  close.addEventListener('click', () => box.remove());

  const body = document.createElement('p');
  body.textContent = text;

  head.append(caption, close);
  box.append(head, body);
  return box;
}

export function toast(title, text, kind) {
  const box = panel(title, text, kind);
  document.getElementById('toasts').append(box);
  setTimeout(() => box.remove(), HOLD_MS);
}

/** Показывает пачку событий, пришедшую с сервера. Тексты берутся из словаря. */
export function flash(events) {
  for (const event of events) {
    const note = eventNote(event);
    if (note) toast(note.title, note.text);
  }
}

export function failure(error) {
  toast(t('error.head'), error.message, 'error');
}
