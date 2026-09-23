/** Сборка приложения: тянем состояние, расставляем окна, включаем часы. */

import * as api from './api.js';
import { applyPlaces, initDesktop, openWindow, renderMenuList, renderWindowMenu } from './desktop.js';
import { applyLanguage, langName, locale, setLang, skinName, t } from './i18n.js';
import { initNotepad, showNotepad } from './notepad.js';
import { failure, flash, requestPermission } from './notify.js';
import { initForms, renderAll, renderStatOptions } from './render.js';

const CLOCK_TICK_MS = 1000;
const BOOT_LIMIT_MS = 4000;

/** Снимает завесу загрузки. Вызывается один раз, чем бы ни кончился запуск. */
function reveal() {
  document.documentElement.classList.remove('booting');
}

// Если запуск где-то застрял, стол всё равно должен появиться.
setTimeout(reveal, BOOT_LIMIT_MS);

const pad = (value) => String(value).padStart(2, '0');

function tick() {
  const now = new Date();
  const time = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  document.getElementById('clock-time').textContent = time;
  document.getElementById('clock-mini').textContent = time;
  document.getElementById('clock-date').textContent = now.toLocaleDateString(locale(), {
    weekday: 'long', day: 'numeric', month: 'long',
  });
}

/* ---------------------------------------------------------------
   Облик и язык
   --------------------------------------------------------------- */

function showSkin(skin) {
  document.documentElement.dataset.skin = skin;
  try {
    localStorage.setItem('lq-skin', skin);   // подсказка для следующего запуска
  } catch (error) { /* приватный режим — переживём */ }
  renderMenuList('menu-skins', api.state.limits.skins, skin, skinName, pickSkin);
}

async function pickSkin(skin) {
  showSkin(skin);                              // мгновенно, не дожидаясь сервера
  try {
    await api.updateProfile({ skin });
  } catch (error) {
    failure(error);
    showSkin(api.state.profile.skin);          // сервер не принял — возвращаем как было
  }
  renderAll();
}

function showLang(code) {
  setLang(code);
  applyLanguage();
  renderMenuList('menu-langs', api.state.limits.langs, code, langName, pickLang);
  renderMenuList('menu-skins', api.state.limits.skins, api.state.profile.skin, skinName, pickSkin);
  renderWindowMenu();
  renderStatOptions();
  renderAll();
  showNotepad();
}

async function pickLang(code) {
  showLang(code);
  try {
    await api.updateProfile({ lang: code });
  } catch (error) {
    failure(error);
    showLang(api.state.profile.lang);
  }
  renderAll();
}

/* ---------------------------------------------------------------
   Интро
   --------------------------------------------------------------- */

function initIntro() {
  const nameInput = document.getElementById('intro-name-input');

  /** Закрывает интро, попутно сохраняя имя, если его вписали. */
  const dismiss = async () => {
    openWindow('intro', false);

    const patch = {};
    const name = nameInput.value.trim();
    if (name && name !== api.state.profile.name) patch.name = name;
    if (!api.state.profile.introSeen) patch.introSeen = true;
    if (!Object.keys(patch).length) return;

    try {
      await api.updateProfile(patch);
    } catch (error) {
      failure(error);
    }
    renderAll();
  };

  document.getElementById('intro-start').addEventListener('click', async () => {
    await dismiss();
    openWindow('new');
    document.getElementById('q-title').focus();
  });

  document.getElementById('intro-later').addEventListener('click', dismiss);
}

/* ---------------------------------------------------------------
   Запуск
   --------------------------------------------------------------- */

async function saveLayout(places) {
  try {
    await api.updateProfile({ places });
  } catch (error) {
    failure(error);
  }
}

async function start() {
  initDesktop({
    onLayoutChange: saveLayout,
    commands: {
      'new-quest': () => {
        openWindow('new');
        document.getElementById('q-title').focus();
      },
      intro: () => {
        document.getElementById('intro-name-input').value = api.state.profile.name;
        openWindow('intro');
      },
      rest: async () => {
        try {
          flash(await api.updateProfile({ resting: !api.state.profile.resting }));
        } catch (error) {
          failure(error);
        }
        renderAll();
      },
    },
  });

  initForms();
  initIntro();
  initNotepad();
  requestPermission();
  tick();
  setInterval(tick, CLOCK_TICK_MS);

  try {
    await api.pull();

    showLang(api.state.profile.lang);
    showSkin(api.state.profile.skin);
    applyPlaces(api.state.profile.places);
    renderStatOptions();
    renderAll();
    showNotepad();

    // Новому человеку сначала объясняем, что это такое.
    if (!api.state.profile.introSeen) {
      document.getElementById('intro-name-input').value = api.state.profile.name;
      openWindow('intro');
    }
  } catch (error) {
    setLang('en');
    applyLanguage();
    failure(error);
  } finally {
    // Показываем стол в любом случае: с ошибкой её хотя бы видно.
    reveal();
  }
}

start();
