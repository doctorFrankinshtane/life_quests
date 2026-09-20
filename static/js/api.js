/**
 * Разговор с сервером. Каждая запись возвращает состояние целиком —
 * браузер ничего не досчитывает сам.
 */

/** Последнее состояние, полученное с сервера. */
export const state = {
  profile: null,
  stats: [],
  mains: [],
  bosses: [],
  sides: [],
  events: [],
  limits: { maxMains: 3, skins: [] },
};

/** Ошибка, у которой есть текст для человека. */
export class ApiError extends Error {}

function adopt(next) {
  Object.assign(state, next);
  return state;
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError('Сервер не отвечает. Запущен ли run.py?');
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(payload.error || `Сервер ответил ${response.status}`);
  }
  return payload;
}

/** Забирает состояние целиком. */
export async function pull() {
  return adopt(await request('/api/state'));
}

/**
 * Отправляет намерение и принимает новое состояние.
 * @returns {Promise<Array<{title: string, text: string}>>} уведомления
 */
export async function send(path, body = {}) {
  const payload = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  adopt(payload.state);
  return payload.flash || [];
}

export const createQuest = (quest) => send('/api/quests', quest);
export const addChapter = (questId, chapter) => send(`/api/quests/${questId}/chapters`, chapter);
export const toggleChapter = (chapterId) => send(`/api/chapters/${chapterId}/toggle`);
export const toggleSide = (questId) => send(`/api/quests/${questId}/toggle`);
export const hitBoss = (questId) => send(`/api/quests/${questId}/hit`);
export const deleteQuest = (questId) => send(`/api/quests/${questId}/delete`);
export const updateProfile = (patch) => send('/api/profile', patch);
