# Google Apps Script integration

The Apps Script sources are stored here for version control, but they are not run
by Python and are not deployed automatically. Copy each `.js` file into a file
with the same name in one Google Apps Script V8 project.

## Setup

1. Create a Google spreadsheet and add sheets named `Current Cars`, `History`,
   and `Config`. The script creates missing tabs and headers on first use.
2. Open **Extensions → Apps Script**, create `Code.js`, `Config.js`,
   `CurrentCars.js`, `History.js`, and `Utils.js`, and copy the matching source.
3. In **Project Settings → Script properties**, add `API_TOKEN` with a long,
   random secret. Use the same value as `GOOGLE_APPS_SCRIPT_TOKEN` in Python.
4. Deploy as a **Web app**, execute as yourself, and restrict access according
   to your Google Workspace policy. The API token is still required by every
   request.
5. Copy the deployment URL into `GOOGLE_APPS_SCRIPT_URL` in the Python `.env`.
6. Add the configuration keys below to the Config sheet (column A is key,
   column B is value). Boolean values should be `TRUE` or `FALSE`.

| Parameter | Default |
| --- | --- |
| telegram_enabled | FALSE |
| notify_on_arrival | TRUE |
| notify_on_departure | TRUE |
| telegram_chat_id | (empty) |
| scan_interval | 30 |
| departure_timeout | 300 |
| recognition_confidence_threshold | 0.8 |

Supported API actions are `register_arrival`, `update_car`,
`register_departure`, `get_current_cars`, and `get_config`. POST actions accept
JSON and include `action` and `token`; write actions also include a unique
`event_id`. Repeated event IDs are ignored; current-car operations upsert by
normalized plate number. The Python client sends all operations in POST bodies
so the API token is not exposed in request URLs.

The script uses only Google Apps Script V8 services and built-in JavaScript APIs.
