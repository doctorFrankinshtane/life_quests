/**
 * Раскладка окон на разных экранах.
 *
 * Запуск: node --test tests/
 * Встроенный в Node тест-раннер, ставить нечего.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { defaultPlaces } from '../static/js/layout.js';

const NAMES = ['hero', 'about', 'mains', 'sides', 'bosses', 'log', 'clock', 'notepad', 'new', 'intro'];

/** Окна-заглушки: высота зависит от того, что в них лежит. */
function fakeWindows(heights = {}) {
  return NAMES.map((name) => ({
    dataset: { win: name },
    style: { width: '' },
    hidden: name === 'new' || name === 'intro',
    offsetHeight: heights[name] ?? 200,
  }));
}

const SCREENS = [
  { name: 'ноутбук', width: 1000, height: 700 },
  { name: 'обычный монитор', width: 1440, height: 900 },
  { name: 'широкий', width: 2560, height: 1080 },
  { name: 'ультраширокий', width: 3440, height: 1200 },
  { name: 'сверхвысокий', width: 5120, height: 1440 },
];

function boxes(places, width, height) {
  return Object.entries(places).map(([name, spot]) => ({
    name,
    x: spot.x,
    y: spot.y,
    w: Number.parseInt(spot.w, 10),
    hidden: spot.hidden,
  }));
}

for (const screen of SCREENS) {
  test(`${screen.name} ${screen.width}×${screen.height}: окна помещаются на стол`, () => {
    const places = defaultPlaces(fakeWindows(), screen.width, screen.height);

    for (const box of boxes(places, screen.width, screen.height)) {
      assert.ok(box.x >= 0, `${box.name}: левый край за столом (${box.x})`);
      assert.ok(box.x + box.w <= screen.width,
        `${box.name}: правый край за столом (${box.x} + ${box.w} > ${screen.width})`);
      assert.ok(box.y >= 0 && box.y < screen.height,
        `${box.name}: верх за столом (${box.y})`);
      assert.ok(box.w >= 240, `${box.name}: окно уже 240px (${box.w})`);
    }
  });

  test(`${screen.name}: колонки не налезают друг на друга`, () => {
    const places = defaultPlaces(fakeWindows(), screen.width, screen.height);
    const tiled = boxes(places).filter((box) => box.name !== 'new' && box.name !== 'intro');

    for (const a of tiled) {
      for (const b of tiled) {
        if (a.name === b.name) continue;
        const sameColumn = a.x === b.x;
        const overlapX = a.x < b.x + b.w && b.x < a.x + a.w;
        assert.ok(sameColumn || !overlapX,
          `${a.name} и ${b.name} пересекаются по горизонтали, но стоят в разных колонках`);
      }
    }
  });
}

test('шире экран — больше колонок', () => {
  const columnsAt = (width) => {
    const places = defaultPlaces(fakeWindows(), width, 1000);
    const tiled = Object.entries(places).filter(([name]) => name !== 'new' && name !== 'intro');
    return new Set(tiled.map(([, spot]) => spot.x)).size;
  };

  assert.equal(columnsAt(1000), 2);
  assert.equal(columnsAt(1440), 3);
  assert.equal(columnsAt(2560), 4);
});

test('стол шире — окна шире, а не просто разъезжаются', () => {
  const widthOf = (deskWidth) =>
    Number.parseInt(defaultPlaces(fakeWindows(), deskWidth, 1000).mains.w, 10);

  assert.ok(widthOf(3440) > widthOf(2560), 'на ультрашироком мейн-квесты должны стать шире');
  assert.ok(widthOf(5120) > widthOf(3440));
});

test('высокая колонка укладывается внахлёст, а не уезжает вниз', () => {
  const tall = fakeWindows({ mains: 900, sides: 900 });
  const places = defaultPlaces(tall, 2560, 800);

  assert.ok(places.sides.y < 800, `сайд-квесты уехали за стол (${places.sides.y})`);
  assert.ok(places.sides.y > places.mains.y, 'порядок в колонке должен сохраниться');
});

test('закрытое окно получает место, куда открыться', () => {
  const places = defaultPlaces(fakeWindows(), 1440, 900);

  assert.equal(places.new.hidden, true);
  assert.ok(Number.parseInt(places.new.w, 10) >= 320);
  assert.ok(places.new.x > 0 && places.new.y > 0);
});

test('всплывающее окно встаёт по центру стола', () => {
  const width = 3440;
  const places = defaultPlaces(fakeWindows(), width, 1200);
  const middle = places.intro.x + Number.parseInt(places.intro.w, 10) / 2;

  assert.ok(Math.abs(middle - width / 2) <= 1, `интро сдвинуто от центра: ${middle}`);
});
