from datetime import datetime, timezone, timedelta

from klimozawr.core.status import compute_loss_pct, compute_status, derive_tick_metrics


def test_loss_pct():
    assert compute_loss_pct(3, 3) == 0
    assert compute_loss_pct(2, 3) == 33
    assert compute_loss_pct(1, 3) == 66
    assert compute_loss_pct(0, 3) == 100


def test_derive_metrics():
    loss, last, avg, unstable = derive_tick_metrics([10, None, 20])
    assert loss == 33
    assert last == 20
    assert avg == 15
    assert unstable is True

    loss, last, avg, unstable = derive_tick_metrics([None, None, None])
    assert loss == 100
    assert last is None
    assert avg is None
    assert unstable is False


def test_status_rules():
    now = datetime.now(timezone.utc)
    first = now - timedelta(seconds=10)

    # green when success
    assert compute_status(now, True, None, first, 120) == "GREEN"

    # yellow within threshold
    assert compute_status(now, False, now - timedelta(seconds=60), first, 120) == "YELLOW"

    # red after threshold
    assert compute_status(now, False, now - timedelta(seconds=121), first, 120) == "RED"
