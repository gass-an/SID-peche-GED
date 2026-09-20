import json
from pathlib import Path

import pytest

from src.extraction.peche_extractor import download_tables


class FakeClient:
    def __init__(self, pages_by_table: dict[str, list[list[dict]]]) -> None:
        self.pages_by_table = pages_by_table
        self.calls: list[str] = []

    def fetch_pages(self, table_name: str):
        self.calls.append(table_name)
        yield from self.pages_by_table[table_name]


def test_download_writes_json_and_archives_previous_snapshot(tmp_path: Path) -> None:
    current = tmp_path / "capture_peche.json"
    current.write_text('[{"capture_id": "old"}]', encoding="utf-8")
    client = FakeClient({"capture_peche": [[{"capture_id": "new"}]]})

    results = download_tables(client, ["capture_peche"], tmp_path)

    assert client.calls == ["capture_peche"]
    assert results[0].rows == 1
    assert json.loads(current.read_text(encoding="utf-8")) == [
        {"capture_id": "new"}
    ]
    archived = list((tmp_path / "archive").glob("*/capture_peche.json"))
    assert len(archived) == 1
    assert json.loads(archived[0].read_text(encoding="utf-8")) == [
        {"capture_id": "old"}
    ]


def test_failed_snapshot_keeps_all_current_json_files(tmp_path: Path) -> None:
    for table_name in ("navire_peche_anonymise", "capture_peche"):
        (tmp_path / f"{table_name}.json").write_text(
            '[{"version": "old"}]', encoding="utf-8"
        )

    class FailingClient(FakeClient):
        def fetch_pages(self, table_name: str):
            if table_name == "capture_peche":
                raise RuntimeError("source indisponible")
            yield [{"version": "new"}]

    with pytest.raises(RuntimeError, match="source indisponible"):
        download_tables(
            FailingClient({}),
            ["navire_peche_anonymise", "capture_peche"],
            tmp_path,
        )

    for table_name in ("navire_peche_anonymise", "capture_peche"):
        content = json.loads(
            (tmp_path / f"{table_name}.json").read_text(encoding="utf-8")
        )
        assert content == [{"version": "old"}]
    assert not list(tmp_path.glob(".staging-*"))


def test_rotation_keeps_only_requested_number_of_snapshots(tmp_path: Path) -> None:
    client = FakeClient({"capture_peche": [[{"capture_id": "new"}]]})
    for index in range(4):
        snapshot = tmp_path / "archive" / f"2026010{index}T000000000000Z"
        snapshot.mkdir(parents=True)
    (tmp_path / "capture_peche.json").write_text("[]", encoding="utf-8")

    download_tables(client, ["capture_peche"], tmp_path, archive_retention=3)

    assert len(list((tmp_path / "archive").iterdir())) == 3
