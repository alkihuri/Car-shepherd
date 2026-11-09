# Detailing Centre Surveillance MVP

Python 3.11+ service for polling RTSP cameras, tracking recognized vehicle
plates, and sending arrival/departure events to Google Sheets and Telegram.
Python, Google Apps Script, documentation, and tests are kept in this repository.

## Status and recognition plugin

The camera, tracker, event, integration, and monitoring components are provided.
No license-plate detection/OCR model is bundled. The default recognizer reports
that it is not configured and deliberately does not invent recognition results.
To connect a real model, implement `recognize(image, camera_id)` returning
`Detection` objects, then set `recognition.plugin` in `config.yaml` to
`your_python_module:YourRecognizer`. The module must be importable in the
environment running the service.

## Run locally

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in RTSP, Apps Script, and Telegram values in .env.
python main.py
```

The monitoring page is at `http://localhost:8000`. Configure cameras by adding
entries to `cameras` in `config.yaml`; camera stream credentials belong in
environment variables, not the YAML file. Cameras run independently, so a failed
stream does not stop other readers. The app binds to `0.0.0.0` by default; change
`server.host` if it should only be available locally.

When every camera is disconnected, departure detection pauses. Each available
camera is sampled on the configured tracking interval. Current cars are kept in
memory; Google Sheets is the persistent current list and visit history.

Google Sheets settings are polled every minute and can be changed without
restarting the service. See [`google_apps_script/README.md`](google_apps_script/README.md)
for manual Apps Script deployment and spreadsheet setup.

Run the unit tests with:

```sh
python -m pytest
```