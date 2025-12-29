from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone

from klimozawr.core.icmp import IcmpClient
from klimozawr.core.models import Device, DeviceRuntimeState, TickResult
from klimozawr.core.status import derive_tick_metrics, compute_status, should_promote_to_red
from klimozawr.core.alerts import should_fire_yellow, should_fire_red, AlertDecision

logger = logging.getLogger("klimozawr.engine")


class MonitorEngine:
    """
    Background engine:
    - ticks ~ each second
    - runs per-device pings in a thread pool
    - emits results through callbacks (thread-safe for Qt signals)
    """

    def __init__(self, max_workers: int = 8) -> None:
        self._lock = threading.RLock()
        self._devices: list[Device] = []
        self._states: dict[int, DeviceRuntimeState] = {}

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ping")

        self.on_tick: callable[[TickResult], None] | None = None
        self.on_alert: callable[[int, str], None] | None = None  # (device_id, level)

        self._in_flight: set[int] = set()
        self._futures: dict[Future, int] = {}

    def set_devices(self, devices: list[Device]) -> None:
        with self._lock:
            self._devices = devices[:]
            now = datetime.now(timezone.utc)
            for d in self._devices:
                if d.id not in self._states:
                    self._states[d.id] = DeviceRuntimeState(device_id=d.id, first_seen_utc=now)

            # cleanup removed devices
            known = {d.id for d in self._devices}
            for did in list(self._states.keys()):
                if did not in known:
                    self._states.pop(did, None)

    def get_state(self, device_id: int) -> DeviceRuntimeState | None:
        with self._lock:
            return self._states.get(device_id)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="MonitorEngine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _run(self) -> None:
        logger.info("engine started")
        client = None
        try:
            client = IcmpClient()
            next_tick = time.perf_counter()

            while not self._stop.is_set():
                nowp = time.perf_counter()
                if nowp < next_tick:
                    time.sleep(min(0.05, next_tick - nowp))
                    self._drain_futures()
                    continue

                next_tick += 1.0
                self._drain_futures()
                self._schedule_tick(client)

        except Exception:
            logger.exception("engine crashed")
        finally:
            try:
                if client:
                    client.close()
            except Exception:
                logger.exception("failed to close ICMP handle")
            logger.info("engine stopped")

    def _drain_futures(self) -> None:
        done: list[Future] = []
        for f, did in list(self._futures.items()):
            if f.done():
                done.append(f)

        for f in done:
            did = self._futures.pop(f, None)
            if did is not None:
                self._in_flight.discard(did)
            try:
                f.result()
            except Exception:
                logger.exception("ping task failed")

    def _schedule_tick(self, client: IcmpClient) -> None:
        with self._lock:
            devices = self._devices[:]

        now_utc = datetime.now(timezone.utc)

        for d in devices:
            if d.id in self._in_flight:
                continue
            self._in_flight.add(d.id)
            fut = self._pool.submit(self._ping_device_tick, client, d, now_utc)
            self._futures[fut] = d.id

    def _ping_device_tick(self, client: IcmpClient, d: Device, ts_utc: datetime) -> None:
        rtts = client.ping_three(d.ip, timeout_ms=d.ping_timeout_ms)
        loss_pct, rtt_last, rtt_avg, unstable = derive_tick_metrics(rtts)
        tick_ok = (loss_pct < 100)

        with self._lock:
            st = self._states.get(d.id)
            if st is None:
                st = DeviceRuntimeState(device_id=d.id, first_seen_utc=ts_utc)
                self._states[d.id] = st

            status = compute_status(
                now_utc=ts_utc,
                tick_has_success=tick_ok,
                last_ok_utc=st.last_ok_utc,
                first_seen_utc=st.first_seen_utc,
                yellow_to_red_secs=d.yellow_to_red_secs,
            )

            # episodes/anchors
            prev_status = st.current_status
            if status == "GREEN":
                st.last_ok_utc = ts_utc
                st.yellow_start_utc = None
                st.red_start_utc = None
                st.yellow_acked = False
                st.red_acked = False
                st.last_yellow_alert_utc = None
                st.last_red_alert_utc = None
            elif status == "YELLOW":
                if prev_status != "YELLOW":
                    st.yellow_start_utc = st.yellow_start_utc or ts_utc
                    st.red_start_utc = None
                    st.red_acked = False
                    st.last_red_alert_utc = None
                    if prev_status == "GREEN" or prev_status is None:
                        st.yellow_acked = False
                        st.last_yellow_alert_utc = None
                if should_promote_to_red(ts_utc, st.yellow_start_utc, d.yellow_to_red_secs):
                    status = "RED"
            elif status == "RED":
                if prev_status != "RED":
                    st.red_start_utc = st.red_start_utc or ts_utc
                    if prev_status != "RED":
                        st.red_acked = False
                        st.last_red_alert_utc = None

            st.current_status = status
            st.current_unstable = unstable
            if prev_status != status:
                logger.info(
                    "status transition device=%s %s->%s yellow_start=%s red_start=%s",
                    d.id,
                    prev_status,
                    status,
                    st.yellow_start_utc.isoformat() if st.yellow_start_utc else None,
                    st.red_start_utc.isoformat() if st.red_start_utc else None,
                )

            # alert decisions
            yellow_dec = should_fire_yellow(
                now_utc=ts_utc,
                yellow_start_utc=st.yellow_start_utc if status == "YELLOW" else None,
                yellow_notify_after_secs=d.yellow_notify_after_secs,
                last_fired_utc=st.last_yellow_alert_utc,
                acked=st.yellow_acked,
            )
            red_dec = should_fire_red(
                now_utc=ts_utc,
                red_start_utc=st.red_start_utc if status == "RED" else None,
                last_fired_utc=st.last_red_alert_utc,
                acked=st.red_acked,
            )

            if yellow_dec.fire and yellow_dec.level == "YELLOW":
                st.last_yellow_alert_utc = ts_utc
                if self.on_alert:
                    self.on_alert(d.id, "YELLOW")
            if red_dec.fire and red_dec.level == "RED":
                st.last_red_alert_utc = ts_utc
                if self.on_alert:
                    self.on_alert(d.id, "RED")

        tr = TickResult(
            device_id=d.id,
            ts_utc=ts_utc,
            loss_pct=loss_pct,
            rtt_last_ms=rtt_last,
            rtt_avg_ms=rtt_avg,
            unstable=unstable,
            status=status,
        )
        if self.on_tick:
            self.on_tick(tr)

    def ack_device(self, device_id: int, level: str) -> None:
        with self._lock:
            st = self._states.get(device_id)
            if not st:
                return
            if level == "YELLOW":
                st.yellow_acked = True
            if level == "RED":
                st.red_acked = True
