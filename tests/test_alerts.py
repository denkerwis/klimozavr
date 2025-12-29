from datetime import datetime, timezone, timedelta

from klimozawr.core.alerts import should_fire_yellow, should_fire_red


def test_yellow_schedule():
    now = datetime.now(timezone.utc)
    start = now - timedelta(seconds=29)
    assert should_fire_yellow(now, start, 30, None, False).fire is False

    now2 = now + timedelta(seconds=2)
    assert should_fire_yellow(now2, start, 30, None, False).fire is True

    last = now2
    # not yet repeat
    assert should_fire_yellow(now2 + timedelta(seconds=30), start, 30, last, False).fire is False
    # repeat after 2 min
    assert should_fire_yellow(now2 + timedelta(minutes=2, seconds=1), start, 30, last, False).fire is True

    # acked stops
    assert should_fire_yellow(now2 + timedelta(minutes=10), start, 30, last, True).fire is False


def test_red_schedule():
    now = datetime.now(timezone.utc)
    start = now
    assert should_fire_red(now, start, None, False).fire is True
    last = now
    assert should_fire_red(now + timedelta(minutes=4), start, last, False).fire is False
    assert should_fire_red(now + timedelta(minutes=5, seconds=1), start, last, False).fire is True
    assert should_fire_red(now + timedelta(minutes=20), start, last, True).fire is False
