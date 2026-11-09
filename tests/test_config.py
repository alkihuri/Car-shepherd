import pytest

from app.core.config import load_config, load_recognizer
from app.recognition.plate_recognizer import UnavailablePlateRecognizer


def test_load_config_expands_environment_and_camera_settings(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        'cameras:\n'
        '  - id: "front"\n'
        '    name: "Front"\n'
        '    stream_url: "${FRONT_STREAM}"\n'
        '    scan_interval: 15\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("FRONT_STREAM", "rtsp://camera/stream")

    config = load_config(config_path)

    assert config.cameras[0].stream_url == "rtsp://camera/stream"
    assert config.cameras[0].scan_interval == 15
    assert isinstance(load_recognizer(config), UnavailablePlateRecognizer)


def test_load_config_rejects_missing_environment_variable(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text('google:\n  apps_script_url: "${MISSING_APPS_URL}"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="MISSING_APPS_URL"):
        load_config(config_path)
