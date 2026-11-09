# Google Sheets setup

See [`google_apps_script/README.md`](../google_apps_script/README.md) for the
manual deployment procedure. The Python service communicates with the published
Web App; it does not edit the spreadsheet directly.

Create these three tabs:

- **Current Cars** — plate, make, owner first/last name, arrival, last seen,
  and duration.
- **History** — the same vehicle details plus departure and visit duration.
- **Config** — parameter names in column A and values in column B.

The Apps Script initializes headers in empty tabs. Keep the header row in place.
