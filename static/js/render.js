/** Отрисовка состояния. Ни одной цифры здесь не вычисляется — всё приходит с сервера. */

import * as api from './api.js';
import { eventLine, eventNote, plural, rankName, statName, t } from './i18n.js';
import { failure, flash } from './notify.js';
import { openWindow } from './desktop.js';

const $ = (id) => document.getElementById(id);

/** Создаёт элемент: тег, класс или свойства, содержимое. */
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  if (typeof props === 'string') {
    node.className = props;
  } else {
    for (const [key, value] of Object.entries(props)) {
      if (key === 'dataset') Object.assign(node.dataset, value);
      else if (key in node) node[key] = value;
      else node.setAttribute(key, value);
    }
  }
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

/** Оборачивает действие: отправляет, показывает уведомления, перерисовывает. */
async function act(call) {
  try {
    flash(await call());
  } catch (error) {
    failure(error);
  }
  renderAll();
}

/* ---------------------------------------------------------------
   Срок
   --------------------------------------------------------------- */

function deadlineChip(quest) {
  const days = quest.daysLeft;
  if (days === null || days === undefined) return null;
  if (days < 0) return el('span', 'chip late', t('due.late', { n: plural(-days, 'day') }));
  if (days === 0) return el('span', 'chip late', t('due.today'));
  return el('span', 'chip', t('due.left', { n: plural(days, 'day') }));
}

/* ---------------------------------------------------------------
   Лист героя
   --------------------------------------------------------------- */

function renderHero() {
  const { profile, stats } = api.state;
  if (!profile) return;

  $('hero-level').textContent = profile.level;
  $('hero-name').textContent = profile.name;
  $('hero-name').title = t('hero.rename');
  $('hero-title').textContent = `${rankName(profile.titleIndex)} · ${t('hero.level')} ${profile.level}`;
  $('hero-xp').textContent = `${profile.xp} / ${profile.xpNeeded}`;
  $('hero-xp-bar').style.width = `${(profile.xp / profile.xpNeeded) * 100}%`;
  $('hero-streak').textContent = profile.streak;
  $('clock-streak').textContent = profile.streak;

  const peak = Math.max(10, ...stats.map((stat) => stat.value));
  $('hero-stats').replaceChildren(...stats.map((stat) => el('div', 'stat',
    el('span', {}, statName(stat.key)),
    el('div', 'bar thin', el('i', { style: `width:${(stat.value / peak) * 100}%` })),
    el('span', {}, String(stat.value)),
  )));

  const rest = $('rest-btn');
  rest.dataset.on = profile.resting ? '1' : '0';
  rest.textContent = t(profile.resting ? 'hero.resting' : 'hero.rest');
}

/* ---------------------------------------------------------------
   Мейн-квесты
   --------------------------------------------------------------- */

function chapterRow(chapter) {
  const row = el('button', {
    type: 'button',
    className: 'chap',
    dataset: { done: chapter.done ? '1' : '0' },
  },
    el('span', 'box', '✓'),
    el('span', 'name', chapter.name),
    el('span', 'xp', `+${chapter.xp}`),
  );
  row.setAttribute('aria-pressed', String(chapter.done));
  row.addEventListener('click', () => act(() => api.toggleChapter(chapter.id)));
  return row;
}

function chapterForm(quest) {
  const input = el('input', {
    type: 'text',
    maxLength: 120,
    required: true,
    placeholder: t(quest.chapters.length ? 'chapter.next' : 'chapter.first'),
    'aria-label': t('chapter.label'),
  });

  const form = el('form', 'add-chapter',
    input,
    el('button', { className: 'act small', type: 'submit' }, '+'));

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) return;
    input.value = '';
    act(() => api.addChapter(quest.id, { name }));
  });
  return form;
}

function killButton(quest) {
  const label = `${t('quest.delete')}: ${quest.title}`;
  const button = el('button', { className: 'act q-kill', type: 'button', title: label }, '×');
  button.setAttribute('aria-label', label);
  button.addEventListener('click', () => {
    if (confirm(t('quest.delete.confirm', { title: quest.title }))) {
      act(() => api.deleteQuest(quest.id));
    }
  });
  return button;
}

function mainCard(quest) {
  const card = el('article', 'quest',
    el('div', 'q-head',
      el('div', {},
        el('div', 'q-name', quest.title),
        quest.why ? el('div', 'q-why', quest.why) : null,
      ),
      killButton(quest),
    ),
    el('div', 'chips',
      el('span', 'chip fill', t('mains.badge')),
      el('span', 'chip', statName(quest.stat)),
      quest.xpTotal ? el('span', 'chip', `${quest.xpTotal} XP`) : null,
      deadlineChip(quest),
    ),
  );

  if (quest.fog) {
    card.classList.add('fog');
    card.append(el('div', 'fog-note',
      el('b', {}, t('mains.fog.head')),
      t('mains.fog.body'),
    ));
  } else {
    const share = quest.doneCount / quest.chapters.length;
    card.append(
      el('div', 'row',
        el('span', 'lab', t('mains.chapters')),
        el('span', { className: 'num', style: 'font-size:11px' },
          `${quest.doneCount} / ${quest.chapters.length}`),
      ),
      el('div', 'bar', el('i', { style: `width:${share * 100}%` })),
      el('div', {}, ...quest.chapters.map(chapterRow)),
    );
  }

  card.append(chapterForm(quest));
  return card;
}

function renderMains() {
  const { mains, limits } = api.state;
  $('mains-count').textContent = t('mains.count', {
    active: mains.length,
    limit: limits.maxMains,
  });

  $('mains').replaceChildren(mains.length
    ? el('div', {}, ...mains.map(mainCard))
    : el('div', 'empty', t('mains.empty')));
}

/* ---------------------------------------------------------------
   Боссы
   --------------------------------------------------------------- */

function phaseButton(phase, index, phases) {
  const firstOpen = phases.findIndex((item) => !item.done);
  const state = phase.done ? 'done' : (index === firstOpen ? 'now' : 'locked');

  const button = el('button', { type: 'button', className: 'phase', dataset: { state } },
    el('b', {}, phase.name),
    `+${phase.xp} XP`);

  button.addEventListener('click', () => act(() => api.toggleChapter(phase.id)));
  return button;
}

function bossCard(boss) {
  const hit = el('button', { className: 'act', type: 'button' },
    t('boss.hit', { xp: boss.hitXp }));
  hit.addEventListener('click', () => act(() => api.hitBoss(boss.id)));

  return el('article', 'boss',
    el('div', { style: 'display:flex; gap:12px; align-items:flex-start; flex-wrap:wrap' },
      el('span', 'inv big', t('boss.badge')),
      el('div', { style: 'flex:1 1 220px; min-width:0' },
        el('div', { style: 'font-size:14px; font-weight:700' }, boss.title),
        el('div', { className: 'chips', style: 'margin-top:5px' },
          el('span', 'chip', statName(boss.stat)),
          el('span', 'chip', t('boss.reward', { xp: boss.xpReward })),
          deadlineChip(boss),
        ),
      ),
      killButton(boss),
    ),
    el('div', {},
      el('div', { className: 'row', style: 'margin-bottom:4px' },
        el('span', 'lab', t('boss.hp')),
        el('span', 'num', t('boss.hits', { left: boss.hpLeft, max: boss.hpMax })),
      ),
      el('div', { className: 'bar hatch', style: 'height:18px' },
        el('i', { style: `width:${(boss.hpLeft / boss.hpMax) * 100}%` })),
    ),
    boss.phases.length ? el('div', 'phases', ...boss.phases.map(phaseButton)) : null,
    el('p', { className: 'dim', style: 'font-size:11.5px' }, t('boss.note')),
    hit,
    chapterForm({ id: boss.id, chapters: boss.phases }),
  );
}

function renderBosses() {
  const { bosses } = api.state;
  $('bosses').replaceChildren(bosses.length
    ? el('div', {}, ...bosses.map(bossCard))
    : el('div', 'empty', t('boss.empty')));
}

/* ---------------------------------------------------------------
   Сайд-квесты
   --------------------------------------------------------------- */

function sideRow(side) {
  const meta = [statName(side.stat)];
  if (side.daily) meta.push(t('sides.streak', { n: side.streak }));
  if (side.daysLeft !== null && side.daysLeft !== undefined && side.daysLeft < 0) {
    meta.push(t('due.overdue'));
  }

  const row = el('button', {
    type: 'button',
    className: 'side',
    dataset: { done: side.done ? '1' : '0' },
  },
    el('span', 'box', '✓'),
    el('span', {},
      el('span', 'name', side.title),
      el('br'),
      el('span', 'meta', meta.join(' · ')),
    ),
    el('span', { className: 'num', style: 'font-size:10.5px' }, `+${side.xp}`),
  );
  row.setAttribute('aria-pressed', String(side.done));
  row.addEventListener('click', () => act(() => api.toggleSide(side.id)));
  return row;
}

function renderSides() {
  const { sides } = api.state;
  const done = sides.filter((side) => side.done).length;
  $('sides-count').textContent = `${done} / ${sides.length}`;

  $('sides').replaceChildren(sides.length
    ? el('div', {}, ...sides.map(sideRow))
    : el('div', 'empty', t('sides.empty')));
}

/* ---------------------------------------------------------------
   Журнал
   --------------------------------------------------------------- */

function renderLog() {
  const lines = api.state.events.map((event) =>
    el('div', {}, `[${event.at}] ${eventLine(event)}`));
  lines.push(el('div', 'cur', '> '));

  const box = $('log');
  box.replaceChildren(...lines);
  box.scrollTop = box.scrollHeight;
}

/* ---------------------------------------------------------------
   Форма нового квеста
   --------------------------------------------------------------- */

function syncFormFields() {
  const kind = $('q-kind').value;
  for (const field of document.querySelectorAll('[data-when]')) {
    field.hidden = field.dataset.when !== kind;
  }
}

/** Заполняет список характеристик — набор ключей приходит с сервера. */
export function renderStatOptions() {
  const select = $('q-stat');
  const chosen = select.value;
  select.replaceChildren(...api.state.limits.stats.map((key) =>
    el('option', { value: key }, statName(key))));
  if (chosen) select.value = chosen;
}

/**
 * Переименование героя: имя — кнопка, по щелчку превращается в поле.
 * Enter сохраняет, Escape отменяет, уход фокуса тоже сохраняет.
 */
function initHeroName() {
  const button = $('hero-name');
  const input = $('hero-name-input');

  const show = (editing) => {
    button.hidden = editing;
    input.hidden = !editing;
  };

  const finish = async (save) => {
    if (input.hidden) return;
    const name = input.value.trim();
    show(false);
    if (!save || !name || name === api.state.profile.name) return;
    await act(() => api.updateProfile({ name }));
  };

  button.addEventListener('click', () => {
    input.value = api.state.profile.name;
    show(true);
    input.focus();
    input.select();
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') finish(true);
    if (event.key === 'Escape') finish(false);
  });
  input.addEventListener('blur', () => finish(true));
}

export function initForms() {
  initHeroName();
  const form = $('new-quest-form');

  $('q-kind').addEventListener('change', syncFormFields);
  syncFormFields();

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const kind = data.get('kind');

    const quest = {
      kind,
      title: data.get('title'),
      stat: data.get('stat'),
      dueDate: data.get('dueDate') || null,
    };
    if (kind === 'main') quest.why = data.get('why') || '';
    if (kind === 'side') {
      quest.xp = Number(data.get('xp'));
      quest.daily = data.get('daily') === 'on';
    }
    if (kind === 'boss') {
      quest.hp = Number(data.get('hp'));
      quest.hitXp = Number(data.get('hitXp'));
    }

    try {
      flash(await api.createQuest(quest));
      form.reset();
      syncFormFields();
      openWindow({ side: 'sides', boss: 'bosses', main: 'mains' }[kind]);
    } catch (error) {
      failure(error);
    }
    renderAll();
  });

  $('rest-btn').addEventListener('click', () =>
    act(() => api.updateProfile({ resting: !api.state.profile.resting })));
}

/* ---------------------------------------------------------------
   Всё сразу
   --------------------------------------------------------------- */

export { eventNote };

export function renderAll() {
  renderHero();
  renderMains();
  renderBosses();
  renderSides();
  renderLog();
}
