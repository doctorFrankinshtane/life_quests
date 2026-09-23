/** Системные уведомления — маленькие окна в правом нижнем углу. */

import { eventNote, plural, t } from './i18n.js';
import { state } from './api.js';

const HOLD_MS = 4200;

// Эти события достаточно важны, чтобы вдобавок к тосту дать звук и
// нативный поп-ап ОС: квест поставлен или доведён до конца.
const LOUD_CODES = new Set([
  'main_created', 'side_created', 'boss_created',
  'main_closed', 'side_done', 'boss_defeated',
]);

/** Просит разрешение на нативные уведомления один раз при старте. */
export function requestPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => { /* переживём */ });
  }
}

function nativePopup(title, text) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    new Notification(title, { body: text });
  } catch { /* переживём */ }
}

let audioCtx;

/** Короткий приятный звон двумя нотами — без внешних файлов. */
function chime() {
  try {
    audioCtx ||= new (window.AudioContext || window.webkitAudioContext)();
    const now = audioCtx.currentTime;
    [659, 988].forEach((freq, i) => {
      const start = now + i * 0.1;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.2, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.3);
      osc.connect(gain).connect(audioCtx.destination);
      osc.start(start);
      osc.stop(start + 0.3);
    });
  } catch { /* переживём */ }
}

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
    if (!note) continue;
    toast(note.title, note.text);
    if (LOUD_CODES.has(event.code)) {
      nativePopup(note.title, note.text);
      chime();
    }
  }
}

export function failure(error) {
  toast(t('error.head'), error.message, 'error');
}

// Срок «подходит», если до него не больше суток. Сервер уже посчитал
// daysLeft — здесь только сравнение готового числа, без дат.
const DUE_WARN_DAYS = 1;
const WARNED_KEY = 'lq-due-warned';

function warnedSet() {
  try {
    return new Set(JSON.parse(localStorage.getItem(WARNED_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

function saveWarned(set) {
  try {
    localStorage.setItem(WARNED_KEY, JSON.stringify([...set]));
  } catch { /* приватный режим — переживём */ }
}

/** Предупреждает о приближающемся сроке — один раз на квест и дедлайн. */
export function checkDeadlines() {
  const quests = [...state.mains, ...state.bosses, ...state.sides];
  const seen = warnedSet();
  let changed = false;

  for (const quest of quests) {
    if (quest.dueDate == null || quest.daysLeft == null) continue;
    if (quest.daysLeft < 0 || quest.daysLeft > DUE_WARN_DAYS) continue;

    const key = `${quest.id}:${quest.dueDate}`;
    if (seen.has(key)) continue;
    seen.add(key);
    changed = true;

    const when = quest.daysLeft === 0 ? t('due.today') : t('due.left', { n: plural(quest.daysLeft, 'day') });
    const title = t('notify.due.head');
    const text = `${quest.title} · ${when}`;
    toast(title, text);
    nativePopup(title, text);
    chime();
  }

  if (changed) saveWarned(seen);
}
