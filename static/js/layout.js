/**
 * Раскладка окон по умолчанию.
 *
 * Позиции заданы долями стола, а не пикселями, поэтому одна и та же
 * композиция собирается и на ноутбуке, и на широком мониторе. Пиксельные
 * минимумы не дают окнам схлопнуться на узких экранах.
 */

const PLAN = {
  clock:  { x: 0.74, y: 0.02, w: 0.24, minW: 210, maxW: 300 },
  hero:   { x: 0.01, y: 0.05, w: 0.24, minW: 250, maxW: 320 },
  mains:  { x: 0.27, y: 0.02, w: 0.41, minW: 330, maxW: 560 },
  sides:  { x: 0.01, y: 0.52, w: 0.33, minW: 300, maxW: 440 },
  bosses: { x: 0.36, y: 0.39, w: 0.47, minW: 340, maxW: 620 },
  log:    { x: 0.47, y: 0.72, w: 0.47, minW: 330, maxW: 620 },
  about:  { x: 0.01, y: 0.86, w: 0.27, minW: 260, maxW: 360 },
  new:    { x: 0.30, y: 0.22, w: 0.30, minW: 320, maxW: 400 },
  intro:  { x: 0.24, y: 0.10, w: 0.45, minW: 320, maxW: 560 },
};

/** Окна, которые при первом запуске лежат закрытыми. */
const CLOSED_AT_START = new Set(['new', 'intro']);

const clamp = (value, low, high) => Math.max(low, Math.min(value, high));

/**
 * Считает раскладку под конкретный размер стола.
 * @param {number} width ширина стола в пикселях
 * @param {number} height высота стола в пикселях
 */
export function defaultPlaces(width, height) {
  const places = {};

  for (const [name, spot] of Object.entries(PLAN)) {
    const w = Math.round(clamp(width * spot.w, spot.minW, spot.maxW));
    const x = Math.round(clamp(width * spot.x, 4, Math.max(4, width - w - 4)));
    const y = Math.round(clamp(height * spot.y, 2, Math.max(2, height - 60)));

    places[name] = { x, y, w: `${w}px`, h: '', hidden: CLOSED_AT_START.has(name) };
  }

  return places;
}
