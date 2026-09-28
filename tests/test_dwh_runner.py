from pathlib import Path

import pytest

from src.dwh import runner


class FakeCursor:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.executed: list[str] = []
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement: str):
        self.executed.append(statement)
        if self.fail:
            raise RuntimeError("erreur SQL")
        return self

    def nextset(self):
        return False


class FakeConnection:
    def __init__(self, *, fail: bool = False) -> None:
        self.fake_cursor = FakeCursor(fail=fail)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.mark.parametrize(
    ("engine", "expected"),
    [
        ("postgresql", Path("sql/postgresql/dwh/init_dwh.sql")),
        ("sqlserver", Path("sql/sqlserver/dwh/init_dwh.sql")),
    ],
)
def test_engine_selects_expected_script(engine: str, expected: Path) -> None:
    path = runner.get_dwh_script_path(engine)
    assert path == runner.PROJECT_ROOT / expected
    assert path.is_absolute()


def test_unknown_engine_is_rejected() -> None:
    with pytest.raises(ValueError, match="Moteur DWH non pris en charge"):
        runner.get_dwh_script_path("sqlite")


def test_script_path_does_not_depend_on_working_directory(
    monkeypatch, tmp_path: Path
) -> None:
    expected = runner.PROJECT_ROOT / "sql/postgresql/dwh/init_dwh.sql"
    monkeypatch.chdir(tmp_path)
    assert runner.get_dwh_script_path("postgresql") == expected


def test_sqlserver_go_lines_create_exactly_three_batches() -> None:
    script = "SELECT 1;\nGO\nSELECT 2;\n  go  \nSELECT 3;"
    assert runner.split_sqlserver_batches(script) == [
        "SELECT 1;",
        "SELECT 2;",
        "SELECT 3;",
    ]


def test_go_inside_sql_or_comment_is_not_a_separator() -> None:
    script = (
        "SELECT 'GO' AS mot; -- GO dans un commentaire\n"
        "SELECT 'ligne GO encore';\n"
        "GO\n"
        "SELECT 2;"
    )
    assert runner.split_sqlserver_batches(script) == [
        "SELECT 'GO' AS mot; -- GO dans un commentaire\nSELECT 'ligne GO encore';",
        "SELECT 2;",
    ]


def test_successful_run_commits(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "dwh.sql"
    script.write_text("SELECT 1", encoding="utf-8")
    monkeypatch.setattr(runner, "get_dwh_script_path", lambda _engine: script)
    connection = FakeConnection()

    runner.run_dwh(connection, "postgresql")

    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_sql_error_rolls_back(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "dwh.sql"
    script.write_text("SELECT 1", encoding="utf-8")
    monkeypatch.setattr(runner, "get_dwh_script_path", lambda _engine: script)
    connection = FakeConnection(fail=True)

    with pytest.raises(RuntimeError, match="erreur SQL"):
        runner.run_dwh(connection, "postgresql")

    assert connection.commits == 0
    assert connection.rollbacks == 1
