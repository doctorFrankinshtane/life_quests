# API

The browser sends an intent to a JSON endpoint and gets the whole new state
back — nothing is recomputed in JavaScript. Writes answer with
`{ "state": …, "flash": [ … ] }`, where `flash` is the list of notifications
as code + parameters; the wording lives in `static/js/i18n.js`. Errors come
back as `{ "error": "text" }` with 400, 404 or 409.

`GET /api/state` also rolls repeating side quests whose period has ended —
there is no background scheduler.

| Request                          | Does                                       |
| -------------------------------- | ------------------------------------------ |
| `GET  /api/state`                | the whole state                            |
| `POST /api/quests`               | create a quest                             |
| `POST /api/quests/{id}/chapters` | add a step, a substep or a boss phase      |
| `POST /api/quests/{id}/toggle`   | tick a side quest                          |
| `POST /api/quests/{id}/hit`      | strike a boss                              |
| `POST /api/quests/{id}/update`   | edit a quest                               |
| `POST /api/quests/{id}/delete`   | delete a quest; it lands in the archive    |
| `POST /api/chapters/{id}/toggle` | tick a step                                |
| `POST /api/chapters/{id}/delete` | delete a step with its substeps            |
| `POST /api/archive/{id}/restore` | bring an archived quest back to the desk   |
| `POST /api/archive/{id}/delete`  | erase an archive entry for good            |
| `POST /api/profile`              | name, skin, language, rest, notepad, layout |

A quest leaves the desk into the `archive` table when it closes (a main quest
or a boss) or is deleted (any kind). Restoring a closed quest undoes the
closing reward and returns it open; restoring a deleted one returns it
exactly as it was. An archive entry can also be erased for good.
