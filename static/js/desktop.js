/**
 * Оконный менеджер и строка меню.
 *
 * Раскладка хранится на сервере вместе с прогрессом, поэтому переезжает
 * вместе с базой. Запись отложена: во время перетаскивания запрос не уходит.
 * Пока человек сам не двигал окна, раскладка пересобирается под размер
 * экрана — на широком мониторе и на ноутбуке композиция своя.
 */

import { defaultPlaces } from './layout.js';
import { t } from './i18n.js';

const STACK_QUERY = '(max-width: 760px)';
const SAVE_DELAY_MS = 600;
const RESIZE_DELAY_MS = 180;
const MIN_WIDTH = 250;
const MIN_HEIGHT = 110;

const desktop = document.getElementById('desktop');
const windows = [...document.querySelectorAll('.win')];
const menus = [...document.querySelectorAll('[data-menu]')];

let topZ = 40;
let savePlaces = () => {};
let saveTimer = null;
let resizeTimer = null;
let arrangedByHand = false;   // человек двигал окна — размер экрана их больше не трогает

export const stacked = () => window.matchMedia(STACK_QUERY).matches;

const byName = (name) => windows.find((win) => win.dataset.win === name);

function currentPlaces() {
  const layout = {};
  for (const win of windows) {
    layout[win.dataset.win] = {
      x: win.offsetLeft,
      y: win.offsetTop,
      w: win.style.width,
      h: win.style.height,
      hidden: win.hidden,
    };
  }
  return layout;
}

function scheduleSave({ byHand = true } = {}) {
  if (byHand) arrangedByHand = true;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => savePlaces(currentPlaces()), SAVE_DELAY_MS);
}

export function focusWindow(win) {
  if (stacked()) return;
  topZ += 1;
  win.style.zIndex = topZ;
  for (const other of windows) other.classList.toggle('focus', other === win);
}

export function openWindow(name, open = true) {
  const win = byName(name);
  if (!win) return;
  win.hidden = !open;
  if (open) focusWindow(win);
  renderWindowMenu();
  scheduleSave();
}

function clampToDesk(win, x, y) {
  return [
    Math.max(-win.offsetWidth + 70, Math.min(x, desktop.clientWidth - 50)),
    Math.max(0, Math.min(y, desktop.clientHeight - 24)),
  ];
}

function toggleMaximise(win) {
  if (stacked()) return;

  if (win.dataset.maxed === '1') {
    const saved = JSON.parse(win.dataset.restore || '{}');
    win.style.left = `${saved.x ?? 20}px`;
    win.style.top = `${saved.y ?? 20}px`;
    win.style.width = saved.w || '';
    win.style.height = saved.h || '';
    win.dataset.maxed = '0';
  } else {
    win.dataset.restore = JSON.stringify({
      x: win.offsetLeft, y: win.offsetTop, w: win.style.width, h: win.style.height,
    });
    Object.assign(win.style, {
      left: '0px',
      top: '0px',
      width: `${desktop.clientWidth}px`,
      height: `${desktop.clientHeight}px`,
    });
    win.dataset.maxed = '1';
    win.querySelector('.body')?.style.setProperty('flex', '1 1 auto');
  }

  focusWindow(win);
  scheduleSave();
}

function draggable(win, handle, mode) {
  handle.addEventListener('pointerdown', (event) => {
    if (stacked() || event.target.closest('.btn')) return;
    event.preventDefault();
    focusWindow(win);

    const startX = event.clientX;
    const startY = event.clientY;
    const base = {
      left: win.offsetLeft, top: win.offsetTop,
      width: win.offsetWidth, height: win.offsetHeight,
    };
    handle.setPointerCapture(event.pointerId);

    const move = (moveEvent) => {
      const dx = moveEvent.clientX - startX;
      const dy = moveEvent.clientY - startY;

      if (mode === 'move') {
        const [x, y] = clampToDesk(win, base.left + dx, base.top + dy);
        win.style.left = `${x}px`;
        win.style.top = `${y}px`;
      } else {
        win.style.width = `${Math.max(MIN_WIDTH, base.width + dx)}px`;
        win.style.height = `${Math.max(MIN_HEIGHT, base.height + dy)}px`;
        win.querySelector('.body')?.style.setProperty('flex', '1 1 auto');
      }
    };

    const up = () => {
      handle.removeEventListener('pointermove', move);
      handle.removeEventListener('pointerup', up);
      scheduleSave();
    };

    handle.addEventListener('pointermove', move);
    handle.addEventListener('pointerup', up);
  });
}

/* ---------------------------------------------------------------
   Расстановка
   --------------------------------------------------------------- */

function put(layout) {
  for (const win of windows) {
    const spot = layout[win.dataset.win];
    if (!spot) continue;
    win.style.left = `${spot.x}px`;
    win.style.top = `${spot.y}px`;
    win.style.width = spot.w || '';
    win.style.height = spot.h || '';
    win.dataset.maxed = '0';
    if (spot.hidden !== undefined) win.hidden = Boolean(spot.hidden);
  }
  renderWindowMenu();
}

/** Расставляет окна по сохранённой раскладке либо собирает её под экран. */
export function applyPlaces(saved) {
  const known = saved && Object.keys(saved).length > 0;
  arrangedByHand = Boolean(known);

  if (stacked()) {
    // В стопке позиции не нужны, но видимость окон сохраняется.
    for (const win of windows) {
      const spot = saved?.[win.dataset.win];
      if (spot?.hidden !== undefined) win.hidden = Boolean(spot.hidden);
    }
    renderWindowMenu();
    return;
  }

  // Рассчитанную раскладку не сохраняем: пока человек не двигал окна,
  // она должна пересобираться под каждый новый размер экрана.
  put(known ? saved : defaultPlaces(windows, desktop.clientWidth, desktop.clientHeight));
}

function onResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (arrangedByHand || stacked()) return;
    put(defaultPlaces(windows, desktop.clientWidth, desktop.clientHeight));
  }, RESIZE_DELAY_MS);
}

/** Возвращает окна на места, рассчитанные под текущий экран. */
export function resetPlaces() {
  arrangedByHand = false;
  if (!stacked()) put(defaultPlaces(windows, desktop.clientWidth, desktop.clientHeight));
  clearTimeout(saveTimer);
  savePlaces({});                 // сервер забывает ручную раскладку
}

/* ---------------------------------------------------------------
   Меню
   --------------------------------------------------------------- */

export function closeMenus() {
  for (const menu of menus) menu.dataset.open = '0';
}

function menuItem(label, mark, onClick) {
  const item = document.createElement('li');
  const button = document.createElement('button');
  button.type = 'button';

  const name = document.createElement('span');
  name.textContent = label;

  const check = document.createElement('span');
  check.textContent = mark ? '✓' : '';

  button.append(name, check);
  button.addEventListener('click', () => {
    closeMenus();
    onClick();
  });

  item.append(button);
  return item;
}

export function renderWindowMenu() {
  const list = document.getElementById('menu-windows');
  if (!list) return;

  const items = windows.map((win) =>
    menuItem(win.dataset.title, !win.hidden, () => openWindow(win.dataset.win, win.hidden)));

  const separator = document.createElement('li');
  separator.className = 'sep';
  items.push(separator, menuItem(t('menu.windows.reset'), false, resetPlaces));

  list.replaceChildren(...items);
}

/**
 * Список с галочкой — облики и языки устроены одинаково.
 * @param {string} listId id элемента ul
 * @param {string[]} values ключи
 * @param {string} current выбранный ключ
 * @param {(key: string) => string} nameOf название для показа
 * @param {(key: string) => void} onPick выбор
 */
export function renderMenuList(listId, values, current, nameOf, onPick) {
  const list = document.getElementById(listId);
  if (!list) return;
  list.replaceChildren(
    ...values.map((value) =>
      menuItem(nameOf(value), value === current, () => onPick(value))),
  );
}

/* ---------------------------------------------------------------
   Запуск
   --------------------------------------------------------------- */

/**
 * @param {object} options
 * @param {(places: object) => void} options.onLayoutChange сохранение раскладки
 * @param {Record<string, () => void>} options.commands обработчики пунктов меню
 */
export function initDesktop({ onLayoutChange, commands }) {
  savePlaces = onLayoutChange;

  for (const win of windows) {
    draggable(win, win.querySelector('.title'), 'move');

    const grip = win.querySelector('[data-grip]');
    if (grip) draggable(win, grip, 'resize');

    win.addEventListener('pointerdown', () => focusWindow(win));
    win.querySelector('[data-close]')?.addEventListener('click', () => openWindow(win.dataset.win, false));
    win.querySelector('[data-min]')?.addEventListener('click', () => openWindow(win.dataset.win, false));
    win.querySelector('[data-max]')?.addEventListener('click', () => toggleMaximise(win));
  }

  for (const menu of menus) {
    menu.querySelector('button').addEventListener('click', (event) => {
      event.stopPropagation();
      const wasOpen = menu.dataset.open === '1';
      closeMenus();
      menu.dataset.open = wasOpen ? '0' : '1';
    });
  }

  for (const button of document.querySelectorAll('[data-cmd]')) {
    button.addEventListener('click', () => {
      closeMenus();
      commands[button.dataset.cmd]?.();
    });
  }

  document.addEventListener('click', closeMenus);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenus();
  });
  window.addEventListener('resize', onResize);

  renderWindowMenu();
}
