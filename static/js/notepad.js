/**
 * Блокнот — один свободный лист.
 *
 * Сохраняется сам через паузу в наборе, поэтому кнопки «сохранить» нет.
 * Лист лежит в профиле и в журнал не пишется: иначе каждая пауза в наборе
 * забивала бы журнал собой.
 */

import * as api from './api.js';
import { t } from './i18n.js';
import { failure } from './notify.js';

const SAVE_DELAY_MS = 900;

let timer = null;
let lastSaved = '';

const sheet = () => document.getElementById('notepad');
const status = () => document.getElementById('notepad-state');

function clockLabel() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
}

async function save() {
  const text = sheet().value;
  if (text === lastSaved) return;

  status().textContent = t('notepad.saving');
  try {
    await api.updateProfile({ notepad: text });
    lastSaved = text;
    status().textContent = t('notepad.saved', { at: clockLabel() });
  } catch (error) {
    status().textContent = '';
    failure(error);
  }
}

/** Ставит на лист то, что пришло с сервера. */
export function showNotepad() {
  const text = api.state.profile.notepad || '';
  lastSaved = text;
  if (document.activeElement !== sheet()) sheet().value = text;
  status().textContent = text ? t('notepad.saved', { at: clockLabel() }) : '';
}

export function initNotepad() {
  sheet().addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(save, SAVE_DELAY_MS);
  });

  // Уход со страницы или из поля не должен съедать последний абзац.
  sheet().addEventListener('blur', () => {
    clearTimeout(timer);
    save();
  });
  window.addEventListener('pagehide', () => {
    if (sheet().value === lastSaved) return;
    navigator.sendBeacon?.(
      '/api/profile',
      new Blob([JSON.stringify({ notepad: sheet().value })], { type: 'application/json' }),
    );
  });
}
