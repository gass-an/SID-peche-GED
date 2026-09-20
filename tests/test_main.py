import sys

from main import parse_args


def test_from_json_option_has_french_and_english_names(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--depuis-json"])
    assert parse_args().depuis_json is True

    monkeypatch.setattr(sys, "argv", ["main.py", "--from-json"])
    assert parse_args().depuis_json is True
