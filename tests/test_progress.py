from io import StringIO

from src.extraction.progress import ProgressDisplay, format_duration


def test_progress_refreshes_aligned_counter() -> None:
    stream = StringIO()
    times = iter([0.0, 0.3, 1.0])
    display = ProgressDisplay("capture_peche", stream=stream, clock=lambda: next(times))

    display.update(50)
    elapsed = display.finish()

    assert stream.getvalue().splitlines()[-1] == (
        "capture_peche                      |         50 lignes | 00:00:01"
    )
    assert elapsed == 1.0


def test_progress_accumulates_pages_in_one_counter() -> None:
    stream = StringIO()
    times = iter([0.0, 0.3, 0.6, 1.0])
    display = ProgressDisplay("navire_moteur", stream=stream, clock=lambda: next(times))

    display.update(50)
    display.update(27)
    display.finish()

    assert "        77 lignes | 00:00:01" in stream.getvalue().splitlines()[-1]


def test_format_duration_includes_hours() -> None:
    assert format_duration(3723.9) == "01:02:03"
