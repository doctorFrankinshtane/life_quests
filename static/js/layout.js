/**
 * Раскладка окон по умолчанию.
 *
 * Стол занимает всю ширину экрана, поэтому раскладка задана колонками, а не
 * точками: на ноутбуке их две, на обычном мониторе три, на ультрашироком
 * четыре. Окна внутри колонки ставятся друг под друга по настоящей высоте —
 * её приходится измерять в DOM, поэтому функция принимает сами элементы.
 */

const GAP = 10;
const EDGE = 8;
const TITLE_STEP = 26;   // минимальный сдвиг: высота шапки окна

// Колонки для разной ширины стола. Берётся первый подходящий план сверху.
const PLANS = [
  {
    min: 1800,                       // ультраширокий: четыре колонки
    columns: [
      { share: 0.19, stack: ['hero', 'about'] },
      { share: 0.28, stack: ['mains', 'sides'] },
      { share: 0.30, stack: ['bosses', 'log'] },
      { share: 0.23, stack: ['clock', 'notepad'] },
    ],
  },
  {
    min: 1200,                       // обычный монитор: три колонки
    columns: [
      { share: 0.24, stack: ['hero', 'clock', 'about'] },
      { share: 0.38, stack: ['mains', 'sides'] },
      { share: 0.38, stack: ['bosses', 'log', 'notepad'] },
    ],
  },
  {
    min: 0,                          // узкий стол: две колонки
    columns: [
      { share: 0.33, stack: ['hero', 'clock', 'about'] },
      { share: 0.67, stack: ['mains', 'bosses', 'sides', 'log', 'notepad'] },
    ],
  },
];

// Окна, которые всплывают по требованию: их место — середина стола.
const FLOATING = {
  new: { share: 0.30, minW: 320, maxW: 420 },
  intro: { share: 0.42, minW: 320, maxW: 580 },
};

/** Окна, закрытые при первом запуске. */
export const CLOSED_AT_START = new Set(Object.keys(FLOATING));

const clamp = (value, low, high) => Math.max(low, Math.min(value, high));

/** Раскладывает колонку сверху вниз; если не влезает — ставит внахлёст. */
function stackColumn(items, top, height) {
  const heights = items.map((item) => item.el.offsetHeight || 160);
  const total = heights.reduce((sum, value) => sum + value, 0) + GAP * (items.length - 1);

  if (total <= height || items.length === 1) {
    let y = top;
    return items.map((item, index) => {
      const spot = { name: item.name, y: Math.round(y) };
      y += heights[index] + GAP;
      return spot;
    });
  }

  // Колонка длиннее стола — сдвигаем равномерно, чтобы шапки остались видны.
  // Шаг не меньше высоты шапки: иначе окно уезжает выше предыдущего.
  const last = heights[heights.length - 1];
  const step = Math.max(TITLE_STEP, (height - last) / (items.length - 1));
  return items.map((item, index) => ({
    name: item.name,
    y: Math.round(Math.min(top + step * index, top + height - TITLE_STEP)),
  }));
}

/**
 * Считает раскладку под размер стола.
 * @param {HTMLElement[]} windows окна стола
 * @param {number} width ширина стола в пикселях
 * @param {number} height высота стола в пикселях
 */
export function defaultPlaces(windows, width, height) {
  const plan = PLANS.find((candidate) => width >= candidate.min);
  const byName = new Map(windows.map((win) => [win.dataset.win, win]));
  const places = {};

  // 1. Ширины колонок и ширина каждого окна.
  const usable = width - EDGE * 2 - GAP * (plan.columns.length - 1);
  const columns = [];
  let left = EDGE;

  for (const column of plan.columns) {
    const columnWidth = Math.max(240, Math.round(usable * column.share));
    columns.push({ left, width: columnWidth, stack: column.stack });
    left += columnWidth + GAP;
  }

  for (const column of columns) {
    for (const name of column.stack) {
      const win = byName.get(name);
      if (win) win.style.width = `${column.width}px`;   // ширина до замера высоты
    }
  }

  // 2. Вертикальная раскладка по измеренной высоте.
  for (const column of columns) {
    const visible = column.stack
      .map((name) => ({ name, el: byName.get(name) }))
      .filter((item) => item.el && !item.el.hidden);

    for (const spot of stackColumn(visible, EDGE, height - EDGE * 2)) {
      places[spot.name] = {
        x: column.left,
        y: spot.y,
        w: `${column.width}px`,
        h: '',
        hidden: false,
      };
    }

    // Закрытому окну тоже нужна точка, куда открыться.
    for (const name of column.stack) {
      if (places[name]) continue;
      places[name] = { x: column.left, y: EDGE, w: `${column.width}px`, h: '', hidden: true };
    }
  }

  // 3. Всплывающие окна — по центру стола.
  for (const [name, spec] of Object.entries(FLOATING)) {
    const win = byName.get(name);
    const winWidth = Math.round(clamp(width * spec.share, spec.minW, spec.maxW));
    const winHeight = win?.offsetHeight || 320;

    places[name] = {
      x: Math.round((width - winWidth) / 2),
      y: Math.round(clamp((height - winHeight) / 2, EDGE, Math.max(EDGE, height - 80))),
      w: `${winWidth}px`,
      h: '',
      hidden: win ? win.hidden : true,
    };
  }

  return places;
}
