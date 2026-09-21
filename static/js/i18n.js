/**
 * Два языка интерфейса.
 *
 * Здесь лежат все человеческие строки проекта. База хранит только коды,
 * поэтому смена языка переписывает и уведомления, и журнал задним числом.
 *
 * Ключи `ui.*` подставляются в разметку по атрибутам data-i18n,
 * ключи `event.*` — в журнал и уведомления по коду с сервера.
 */

export const LANGS = ['ru', 'en'];

const DICT = {
  ru: {
    langName: 'Русский',
    locale: 'ru-RU',

    stat: {
      body: 'Тело', mind: 'Разум', craft: 'Ремесло', soul: 'Дух', bonds: 'Связи',
    },
    title: ['Новичок', 'Искатель', 'Странник', 'Следопыт', 'Ветеран', 'Мастер'],
    skin: { win98: 'Окна 98', platinum: 'Платина', plum: 'Слива' },

    ui: {
      'menu.quest': 'Квест',
      'menu.quest.new': 'Новый квест…',
      'menu.quest.rest': 'Объявить привал',
      'menu.quest.intro': 'Что это такое',
      'menu.windows': 'Окна',
      'menu.windows.reset': 'Расставить по умолчанию',
      'menu.skin': 'Облик',
      'menu.lang': 'Язык',

      'win.clock': 'Часы',
      'win.hero': 'Лист героя',
      'win.mains': 'Мейн-квесты',
      'win.sides': 'Сайд-квесты',
      'win.bosses': 'Боссы',
      'win.log': 'Журнал системы',
      'win.new': 'Новый квест',
      'win.about': 'О программе',
      'win.notepad': 'Блокнот',
      'win.intro': 'Добро пожаловать',

      'hero.xp': 'Опыт',
      'hero.stats': 'Характеристики',
      'hero.streak': 'Серия дней',
      'hero.streak.note': 'ежедневки без пропуска',
      'hero.rest': 'Объявить привал',
      'hero.resting': 'Привал · серия заморожена',
      'hero.level': 'ур.',
      'hero.rename': 'Изменить имя героя',
      'notepad.hint': 'мысли, ссылки, что угодно — сохраняется само',
      'notepad.saved': 'сохранено {at}',
      'notepad.saving': 'сохраняю…',

      'mains.badge': 'МЕЙН',
      'mains.count': 'активных {active}',
      'mains.empty': 'Ни одного мейн-квеста. Меню «Квест» → «Новый квест».',
      'mains.chapters': 'Шаги',
      'mains.fog.head': 'В ТУМАНЕ. ',
      'mains.fog.body': 'Нет ни одного шага, поэтому квест не даёт опыта. Назовите шаг, выполнимый за один заход.',
      'chapter.first': 'первый шаг на один заход',
      'chapter.next': 'следующий шаг',
      'chapter.label': 'Название шага',
      'step.add.sub': 'Добавить подшаг',
      'step.sub.hint': 'подшаг — что сделать внутри этого шага',
      'step.auto.head': 'Шаг с подшагами',
      'step.auto': 'Закроется сам, когда будут отмечены все подшаги.',
      'step.delete': 'Удалить шаг',
      'step.delete.confirm': 'Удалить «{name}»? Подшаги уйдут вместе с ним, опыт останется.',

      'sides.head': 'Мелочь и ежедневки',
      'sides.empty': 'Пока пусто. Сайд-квест — мелкое дело или ежедневка.',
      'sides.streak': 'серия {n}',

      'archive.head': 'Закрытые и удалённые',
      'archive.empty': 'Пусто. Закрытые и удалённые квесты оседают здесь.',
      'archive.closed': 'закрыт {at}',
      'archive.deleted': 'удалён {at}',
      'archive.restore': 'Вернуть на доску',
      'archive.purge': 'Стереть из архива',
      'archive.purge.confirm': 'Стереть «{title}» из архива навсегда? Вернуть будет нельзя.',
      'archive.steps': 'шаги {done} / {total}',

      'boss.badge': 'БОСС',
      'boss.hp': 'Здоровье босса',
      'boss.hits': '{left} / {max} ударов',
      'boss.reward': '{xp} XP за победу',
      'boss.hit': 'Нанести удар · +{xp} XP',
      'boss.note': 'Один удар — одно реальное действие. Босса нельзя закрыть галочкой, только серией ударов.',
      'boss.empty': 'Боссов нет. Босс — жёсткая цель, которую нельзя закрыть одной галочкой.',

      'due.left': 'осталось {n}',
      'due.today': 'сегодня последний день',
      'due.late': 'просрочен на {n}',
      'due.overdue': 'просрочен',
      'day': ['день', 'дня', 'дней'],

      'form.title': 'Название',
      'form.title.hint': 'пробежать 10 км без остановки',
      'form.kind': 'Тип',
      'form.kind.side': 'Сайд-квест',
      'form.kind.main': 'Мейн-квест',
      'form.kind.boss': 'Босс',
      'form.stat': 'Характеристика',
      'form.why': 'Зачем',
      'form.why.hint': 'строка мотива — она держит дольше награды',
      'form.due': 'Срок',
      'form.xp': 'Опыт',
      'form.hp': 'Ударов',
      'form.hit': 'Опыт за удар',
      'form.repeat': 'Повторять',
      'form.every': 'Каждые',
      'repeat.none': 'не повторять',
      'repeat.day': 'по дням',
      'repeat.week': 'по неделям',
      'repeat.month': 'по месяцам',
      'repeat.every.day': 'каждый день',
      'repeat.every.week': 'каждую неделю',
      'repeat.every.month': 'каждый месяц',
      'repeat.every.n.day': 'раз в {n}',
      'repeat.every.n.week': 'раз в {n}',
      'repeat.every.n.month': 'раз в {n}',
      'unit.day': ['день', 'дня', 'дней'],
      'unit.week': ['неделю', 'недели', 'недель'],
      'unit.month': ['месяц', 'месяца', 'месяцев'],
      'repeat.renews': 'обновится через {n}',
      'repeat.renews.today': 'обновится сегодня',
      'form.submit': 'Записать в журнал',

      'quest.delete': 'Удалить',
      'quest.edit': 'Изменить квест',
      'quest.edit.short': 'Изм.',
      'quest.save': 'Сохранить',
      'quest.cancel': 'Отмена',
      'quest.delete.confirm': 'Удалить «{title}»? Заработанный опыт останется.',
      'window.close': 'Закрыть окно «{name}»',
      'window.min': 'Свернуть окно «{name}»',
      'window.max': 'Развернуть окно «{name}»',
      'toast.close': 'Закрыть уведомление',
      'error.head': 'Не вышло',
      'error.offline': 'Сервер не отвечает. Запущен ли run.py?',
      'error.status': 'Сервер ответил {status}',

      'about.version': 'Life Quests · версия 0.1',
      'about.note': 'Окна таскаются за шапку и тянутся за правый нижний угол. Облик, язык и раскладка окон хранятся в базе вместе с прогрессом.',

      'intro.head': 'Цели как квесты',
      'intro.lead': 'Большая цель редко умирает от лени. Она умирает, когда непонятно, что сделать сегодня. Здесь цель обязана распасться на шаги, и каждый шаг что-то даёт.',
      'intro.name': 'Как вас зовут',
      'intro.types': 'Три типа квестов',
      'intro.main.name': 'МЕЙН',
      'intro.main.text': 'Большая цель. Делится на главы — шаг на один заход. Пока главы нет, квест лежит в тумане и опыта не даёт.',
      'intro.side.name': 'САЙД',
      'intro.side.text': 'Мелкое дело или ежедневка. Ставится галочкой, ежедневка копит серию.',
      'intro.boss.name': 'БОСС',
      'intro.boss.text': 'Жёсткая цель со здоровьем. Галочкой не закрыть — только серией ударов, где удар равен реальному действию.',
      'intro.xp': 'Сделанное даёт опыт: растут уровень и пять характеристик — Тело, Разум, Ремесло, Дух, Связи.',
      'intro.rest': 'Пропустили неделю — объявите привал: серия замирает, ничего не сгорает.',
      'intro.tip': 'Окна таскаются за шапку, всё остальное — в меню сверху.',
      'intro.start': 'Создать первый квест',
      'intro.later': 'Осмотреться',
    },

    event: {
      base_created: { log: 'База создана · профиль пуст' },
      demo_filled: { log: 'Демо-квесты залиты' },
      level_up: {
        log: 'Уровень {level} · {title}',
        head: 'Уровень {level}',
        body: 'Новое звание: {title}.',
      },
      main_created: {
        log: 'Новый мейн · {title} · статус: туман',
        head: 'Мейн в тумане',
        body: 'Опыта не будет, пока нет первой главы. Назовите шаг на один заход.',
      },
      side_created: {
        log: 'Новый сайд · {title} · +{xp} XP',
        head: 'Сайд-квест записан',
        body: '{title} · +{xp} XP при выполнении.',
      },
      boss_created: {
        log: 'Новый босс · {title} · {hp} HP',
        head: 'Босс объявлен',
        body: '{title} · {hp} ударов до победы.',
      },
      chapter_added: { log: 'Шаг · {title} · {name} · +{xp} XP' },
      substep_added: { log: 'Подшаг · {parent} · {name} · +{xp} XP' },
      step_closed: { log: 'Шаг закрыт целиком · {name} · +{xp} XP' },
      step_deleted: { log: 'Шаг удалён · {name}' },
      quest_edited: { log: 'Квест изменён · {title}',
                      head: 'Сохранено', body: '«{title}» обновлён.' },
      phase_added: { log: 'Фаза · {title} · {name} · +{xp} XP' },
      fog_lifted: {
        head: 'Туман рассеялся',
        body: '«{title}» получил первый шаг.',
      },
      chapter_done: { log: '+{xp} XP · {name} · осталось глав {left}' },
      chapter_undone: { log: 'Отмена · −{xp} XP · {name}' },
      phases_done: { log: '+{xp} XP · {name} · все фазы закрыты' },
      main_closed: {
        log: 'Квест закрыт · {title} · бонус +{bonus} XP',
        head: 'Квест закрыт',
        body: '«{title}» пройден целиком. Бонус +{bonus} XP.',
      },
      side_done: { log: '+{xp} XP · {title}' },
      side_undone: { log: 'Отмена · −{xp} XP · {title}' },
      boss_hit: { log: 'Удар · {title} · −1 HP · осталось {left}' },
      boss_defeated: {
        log: 'Босс повержен · {title} · +{xp} XP',
        head: 'Босс повержен',
        body: '«{title}» закрыт. +{xp} XP.',
      },
      quest_deleted: {
        log: 'Квест удалён · {title}',
        head: 'Квест удалён',
        body: '«{title}» уехал в архив.',
      },
      quest_restored: {
        log: 'Квест возвращён из архива · {title}',
        head: 'Квест возвращён',
        body: '«{title}» снова на доске.',
      },
      archive_purged: { log: 'Запись стёрта из архива · {title}' },
      rest_on: {
        log: 'Привал объявлен · серия заморожена',
        head: 'Привал',
        body: 'Ежедневки не сгорают, серия {streak} держится. Возвращайтесь, когда сможете.',
      },
      rest_off: {
        log: 'Привал окончен',
        head: 'Возвращение',
        body: 'Привал окончен. Серия продолжается с {streak} дней.',
      },
      name_changed: { log: 'Имя героя → {name}' },
      skin_changed: { log: 'Облик → {skin}' },
      lang_changed: { log: 'Язык → {lang}' },
    },
  },

  en: {
    langName: 'English',
    locale: 'en-GB',

    stat: {
      body: 'Body', mind: 'Mind', craft: 'Craft', soul: 'Spirit', bonds: 'Bonds',
    },
    title: ['Novice', 'Seeker', 'Wanderer', 'Pathfinder', 'Veteran', 'Master'],
    skin: { win98: 'Windows 98', platinum: 'Platinum', plum: 'Plum' },

    ui: {
      'menu.quest': 'Quest',
      'menu.quest.new': 'New quest…',
      'menu.quest.rest': 'Take a rest',
      'menu.quest.intro': 'What this is',
      'menu.windows': 'Windows',
      'menu.windows.reset': 'Reset arrangement',
      'menu.skin': 'Skin',
      'menu.lang': 'Language',

      'win.clock': 'Clock',
      'win.hero': 'Character sheet',
      'win.mains': 'Main quests',
      'win.sides': 'Side quests',
      'win.bosses': 'Bosses',
      'win.log': 'System log',
      'win.new': 'New quest',
      'win.about': 'About',
      'win.notepad': 'Notepad',
      'win.intro': 'Welcome',

      'hero.xp': 'Experience',
      'hero.stats': 'Attributes',
      'hero.streak': 'Day streak',
      'hero.streak.note': 'dailies without a miss',
      'hero.rest': 'Take a rest',
      'hero.resting': 'Resting · streak frozen',
      'hero.level': 'lvl',
      'hero.rename': 'Change the hero name',
      'notepad.hint': 'thoughts, links, anything — saves itself',
      'notepad.saved': 'saved at {at}',
      'notepad.saving': 'saving…',

      'mains.badge': 'MAIN',
      'mains.count': 'active {active}',
      'mains.empty': 'No main quests yet. Menu “Quest” → “New quest”.',
      'mains.chapters': 'Steps',
      'mains.fog.head': 'IN THE FOG. ',
      'mains.fog.body': 'No steps, so this quest earns nothing. Name one step you can finish in a single sitting.',
      'chapter.first': 'first step, one sitting',
      'chapter.next': 'next step',
      'chapter.label': 'Step name',
      'step.add.sub': 'Add a substep',
      'step.sub.hint': 'substep — what to do inside this step',
      'step.auto.head': 'Step with substeps',
      'step.auto': 'It closes itself once every substep is ticked.',
      'step.delete': 'Delete the step',
      'step.delete.confirm': 'Delete “{name}”? Its substeps go with it; the experience stays.',

      'sides.head': 'Small things and dailies',
      'sides.empty': 'Empty so far. A side quest is a small task or a daily.',
      'sides.streak': 'streak {n}',

      'archive.head': 'Closed and deleted',
      'archive.empty': 'Empty so far. Closed and deleted quests settle here.',
      'archive.closed': 'closed {at}',
      'archive.deleted': 'deleted {at}',
      'archive.restore': 'Back to the desk',
      'archive.purge': 'Delete forever',
      'archive.purge.confirm': 'Erase “{title}” from the archive for good? There is no way back.',
      'archive.steps': 'steps {done} / {total}',

      'boss.badge': 'BOSS',
      'boss.hp': 'Boss health',
      'boss.hits': '{left} / {max} hits',
      'boss.reward': '{xp} XP for the win',
      'boss.hit': 'Strike · +{xp} XP',
      'boss.note': 'One strike is one real action. A boss cannot be ticked off — only worn down.',
      'boss.empty': 'No bosses. A boss is a hard goal that no single checkbox can close.',

      'due.left': '{n} left',
      'due.today': 'last day',
      'due.late': '{n} overdue',
      'due.overdue': 'overdue',
      'day': ['day', 'days', 'days'],

      'form.title': 'Name',
      'form.title.hint': 'run 10 km without stopping',
      'form.kind': 'Type',
      'form.kind.side': 'Side quest',
      'form.kind.main': 'Main quest',
      'form.kind.boss': 'Boss',
      'form.stat': 'Attribute',
      'form.why': 'Why',
      'form.why.hint': 'the reason — it lasts longer than the reward',
      'form.due': 'Due',
      'form.xp': 'XP',
      'form.hp': 'Hits',
      'form.hit': 'XP per hit',
      'form.repeat': 'Repeat',
      'form.every': 'Every',
      'repeat.none': 'no repeat',
      'repeat.day': 'daily',
      'repeat.week': 'weekly',
      'repeat.month': 'monthly',
      'repeat.every.day': 'every day',
      'repeat.every.week': 'every week',
      'repeat.every.month': 'every month',
      'repeat.every.n.day': 'every {n}',
      'repeat.every.n.week': 'every {n}',
      'repeat.every.n.month': 'every {n}',
      'unit.day': ['day', 'days', 'days'],
      'unit.week': ['week', 'weeks', 'weeks'],
      'unit.month': ['month', 'months', 'months'],
      'repeat.renews': 'renews in {n}',
      'repeat.renews.today': 'renews today',
      'form.submit': 'Write it down',

      'quest.delete': 'Delete',
      'quest.edit': 'Edit the quest',
      'quest.edit.short': 'Edit',
      'quest.save': 'Save',
      'quest.cancel': 'Cancel',
      'quest.delete.confirm': 'Delete “{title}”? Earned experience stays.',
      'window.close': 'Close the “{name}” window',
      'window.min': 'Minimise the “{name}” window',
      'window.max': 'Maximise the “{name}” window',
      'toast.close': 'Dismiss',
      'error.head': 'Did not work',
      'error.offline': 'No answer from the server. Is run.py running?',
      'error.status': 'Server answered {status}',

      'about.version': 'Life Quests · version 0.1',
      'about.note': 'Drag windows by the title bar, resize from the bottom-right corner. Skin, language and window layout live in the database next to your progress.',

      'intro.head': 'Goals as quests',
      'intro.lead': 'A big goal rarely dies of laziness. It dies when today’s move is unclear. Here a goal has to break into steps, and every step pays.',
      'intro.name': 'What should we call you',
      'intro.types': 'Three kinds of quest',
      'intro.main.name': 'MAIN',
      'intro.main.text': 'A big goal. It splits into chapters — one step per sitting. With no chapter the quest sits in the fog and earns nothing.',
      'intro.side.name': 'SIDE',
      'intro.side.text': 'A small task or a daily. Tick it off; dailies build a streak.',
      'intro.boss.name': 'BOSS',
      'intro.boss.text': 'A hard goal with health. No checkbox closes it — only a run of strikes, where one strike is one real action.',
      'intro.xp': 'Finished work pays experience: your level grows, and so do five attributes — Body, Mind, Craft, Spirit, Bonds.',
      'intro.rest': 'Missed a week? Take a rest: the streak freezes and nothing burns down.',
      'intro.tip': 'Drag windows by the title bar; everything else lives in the menu above.',
      'intro.start': 'Create the first quest',
      'intro.later': 'Look around first',
    },

    event: {
      base_created: { log: 'Database created · profile empty' },
      demo_filled: { log: 'Demo quests loaded' },
      level_up: {
        log: 'Level {level} · {title}',
        head: 'Level {level}',
        body: 'New rank: {title}.',
      },
      main_created: {
        log: 'New main · {title} · status: fog',
        head: 'Main quest in the fog',
        body: 'No experience until the first chapter. Name a step you can finish in one sitting.',
      },
      side_created: {
        log: 'New side · {title} · +{xp} XP',
        head: 'Side quest written down',
        body: '{title} · +{xp} XP when done.',
      },
      boss_created: {
        log: 'New boss · {title} · {hp} HP',
        head: 'Boss declared',
        body: '{title} · {hp} hits to victory.',
      },
      chapter_added: { log: 'Step · {title} · {name} · +{xp} XP' },
      substep_added: { log: 'Substep · {parent} · {name} · +{xp} XP' },
      step_closed: { log: 'Step fully closed · {name} · +{xp} XP' },
      step_deleted: { log: 'Step deleted · {name}' },
      quest_edited: { log: 'Quest edited · {title}',
                      head: 'Saved', body: '“{title}” is updated.' },
      phase_added: { log: 'Phase · {title} · {name} · +{xp} XP' },
      fog_lifted: {
        head: 'The fog lifted',
        body: '“{title}” has its first step.',
      },
      chapter_done: { log: '+{xp} XP · {name} · {left} chapters left' },
      chapter_undone: { log: 'Undone · −{xp} XP · {name}' },
      phases_done: { log: '+{xp} XP · {name} · all phases closed' },
      main_closed: {
        log: 'Quest closed · {title} · bonus +{bonus} XP',
        head: 'Quest closed',
        body: '“{title}” is done. Bonus +{bonus} XP.',
      },
      side_done: { log: '+{xp} XP · {title}' },
      side_undone: { log: 'Undone · −{xp} XP · {title}' },
      boss_hit: { log: 'Strike · {title} · −1 HP · {left} left' },
      boss_defeated: {
        log: 'Boss defeated · {title} · +{xp} XP',
        head: 'Boss defeated',
        body: '“{title}” is closed. +{xp} XP.',
      },
      quest_deleted: {
        log: 'Quest deleted · {title}',
        head: 'Quest deleted',
        body: '“{title}” moved to the archive.',
      },
      quest_restored: {
        log: 'Quest restored from the archive · {title}',
        head: 'Quest restored',
        body: '“{title}” is back on the desk.',
      },
      archive_purged: { log: 'Archive entry erased · {title}' },
      rest_on: {
        log: 'Rest declared · streak frozen',
        head: 'Rest',
        body: 'Dailies stay put, the streak of {streak} holds. Come back when you can.',
      },
      rest_off: {
        log: 'Rest over',
        head: 'Back',
        body: 'Rest is over. The streak continues from {streak} days.',
      },
      name_changed: { log: 'Hero name → {name}' },
      skin_changed: { log: 'Skin → {skin}' },
      lang_changed: { log: 'Language → {lang}' },
    },
  },
};

let current = 'en';

export function setLang(lang) {
  current = DICT[lang] ? lang : 'en';
  document.documentElement.lang = current;
}

export const lang = () => current;
export const locale = () => DICT[current].locale;
export const langName = (code) => DICT[code]?.langName || code;
export const statName = (key) => DICT[current].stat[key] || key;
export const rankName = (index) => DICT[current].title[index] || '';
export const skinName = (key) => DICT[current].skin[key] || key;

/** Подставляет значения в шаблон: «осталось {n}». */
function fill(template, params) {
  return String(template).replace(/\{(\w+)\}/g, (whole, key) =>
    (params[key] === undefined ? whole : params[key]));
}

/** Строка интерфейса по ключу. */
export function t(key, params = {}) {
  const value = DICT[current].ui[key];
  if (value === undefined) return key;
  return fill(value, params);
}

/**
 * Склонение по числу. В русском три формы, в английском две —
 * поэтому правило выбирается вместе со словарём.
 */
export function plural(count, key) {
  const forms = DICT[current].ui[key];
  if (current === 'en') return `${count} ${forms[count === 1 ? 0 : 1]}`;

  const mod100 = count % 100;
  const mod10 = count % 10;
  let form = forms[2];
  if (mod100 < 11 || mod100 > 14) {
    if (mod10 === 1) form = forms[0];
    else if (mod10 >= 2 && mod10 <= 4) form = forms[1];
  }
  return `${count} ${form}`;
}

/** Человеческая подпись ритма: «каждый день», «раз в 2 недели». */
export function repeatLabel(repeat) {
  if (!repeat) return '';
  if (repeat.every === 1) return t(`repeat.every.${repeat.unit}`);
  return t(`repeat.every.n.${repeat.unit}`, { n: plural(repeat.every, `unit.${repeat.unit}`) });
}

/** Готовит параметры события: индексы и ключи превращает в названия. */
function eventParams(params) {
  const ready = { ...params };
  if (ready.titleIndex !== undefined) ready.title = rankName(ready.titleIndex);
  if (ready.skin !== undefined) ready.skin = skinName(ready.skin);
  if (ready.lang !== undefined) ready.lang = langName(ready.lang);
  return ready;
}

/** Строка журнала по событию с сервера. */
export function eventLine({ code, params }) {
  const entry = DICT[current].event[code];
  if (!entry?.log) return code;
  return fill(entry.log, eventParams(params));
}

/** Уведомление по событию с сервера: заголовок и текст. */
export function eventNote({ code, params }) {
  const entry = DICT[current].event[code];
  if (!entry?.head) return null;
  const ready = eventParams(params);
  return { title: fill(entry.head, ready), text: fill(entry.body || '', ready) };
}

/** Проставляет строки в разметку по атрибутам data-i18n. */
export function applyLanguage() {
  for (const node of document.querySelectorAll('[data-i18n]')) {
    node.textContent = t(node.dataset.i18n);
  }
  for (const node of document.querySelectorAll('[data-i18n-placeholder]')) {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  }
  for (const node of document.querySelectorAll('[data-i18n-aria]')) {
    node.setAttribute('aria-label', t(node.dataset.i18nAria));
  }
  for (const win of document.querySelectorAll('[data-i18n-title]')) {
    const name = t(win.dataset.i18nTitle);
    win.dataset.title = name;
    win.querySelector('.title .t').textContent = name;
    win.querySelector('[data-close]')?.setAttribute('aria-label', t('window.close', { name }));
    win.querySelector('[data-min]')?.setAttribute('aria-label', t('window.min', { name }));
    win.querySelector('[data-max]')?.setAttribute('aria-label', t('window.max', { name }));
  }
}
