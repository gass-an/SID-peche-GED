from pathlib import Path

import pytest

from src.dtm import runner


class FakeCursor:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.executed: list[str] = []
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement: str):
        self.executed.append(statement)
        if self.fail_on and self.fail_on in statement:
            raise RuntimeError("erreur SQL DTM")
        return self

    def nextset(self):
        return False


class FakeConnection:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fake_cursor = FakeCursor(fail_on=fail_on)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.mark.parametrize("engine", ["postgresql", "sqlserver"])
def test_discovers_project_dtm_for_each_engine(engine: str) -> None:
    scripts = runner.discover_dtm_scripts(engine)
    assert [path.parent.name for path in scripts] == ["performance_campagnes"]
    assert all(path.name == "init.sql" for path in scripts)


def test_discovery_is_sorted_by_dtm_directory(monkeypatch, tmp_path: Path) -> None:
    dtm_root = tmp_path / "dtm"
    for name in ("zeta", "alpha", "flotte"):
        directory = dtm_root / name
        directory.mkdir(parents=True)
        (directory / "init.sql").write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setitem(runner.DTM_DIRECTORIES, "postgresql", Path("dtm"))

    scripts = runner.discover_dtm_scripts("postgresql")

    assert [path.parent.name for path in scripts] == ["alpha", "flotte", "zeta"]


def test_missing_dtm_scripts_has_clear_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setitem(runner.DTM_DIRECTORIES, "postgresql", Path("dtm"))

    with pytest.raises(FileNotFoundError, match="Aucun script DTM trouvé.*postgresql"):
        runner.discover_dtm_scripts("postgresql")


def test_unknown_engine_is_rejected() -> None:
    with pytest.raises(ValueError, match="Moteur DTM non pris en charge"):
        runner.discover_dtm_scripts("sqlite")


def test_postgresql_script_is_executed_and_committed(
    monkeypatch, tmp_path: Path
) -> None:
    script = tmp_path / "performance" / "init.sql"
    script.parent.mkdir()
    script.write_text("BEGIN; SELECT 1; COMMIT;", encoding="utf-8")
    monkeypatch.setattr(runner, "discover_dtm_scripts", lambda _engine: [script])
    connection = FakeConnection()

    runner.run_dtms(connection, "postgresql")

    assert connection.fake_cursor.executed == ["BEGIN; SELECT 1; COMMIT;"]
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_sqlserver_reuses_go_batch_execution(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "performance" / "init.sql"
    script.parent.mkdir()
    script.write_text("SELECT 1;\nGO\nSELECT 2;", encoding="utf-8")
    monkeypatch.setattr(runner, "discover_dtm_scripts", lambda _engine: [script])
    connection = FakeConnection()

    runner.run_dtms(connection, "sqlserver")

    assert connection.fake_cursor.executed == ["SELECT 1;", "SELECT 2;"]
    assert connection.commits == 1


def test_sql_error_is_propagated_and_stops_following_dtms(
    monkeypatch, tmp_path: Path
) -> None:
    first = tmp_path / "alpha" / "init.sql"
    second = tmp_path / "zeta" / "init.sql"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("SELECT ECHEC;", encoding="utf-8")
    second.write_text("SELECT 2;", encoding="utf-8")
    monkeypatch.setattr(
        runner, "discover_dtm_scripts", lambda _engine: [first, second]
    )
    connection = FakeConnection(fail_on="ECHEC")

    with pytest.raises(RuntimeError, match="erreur SQL DTM"):
        runner.run_dtms(connection, "postgresql")

    assert connection.fake_cursor.executed == ["SELECT ECHEC;"]
    assert connection.commits == 0
    assert connection.rollbacks == 1
