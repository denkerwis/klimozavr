from __future__ import annotations

import ipaddress
import re
import socket


_HOST_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def is_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return True
    except ipaddress.AddressValueError:
        return False


def is_valid_hostname(value: str) -> bool:
    host = value.strip()
    if not host:
        return False
    if host.endswith("."):
        host = host[:-1]
    if not host or len(host) > 253:
        return False
    labels = host.split(".")
    if len(labels) == 4 and all(label.isdigit() for label in labels):
        return False
    if any(len(label) == 0 for label in labels):
        return False
    for label in labels:
        if len(label) > 63:
            return False
        if not _HOST_LABEL_RE.match(label):
            return False
    return True


def is_valid_target(value: str) -> bool:
    return is_ipv4(value) or is_valid_hostname(value)


def is_host_online(timeout_secs: float = 2.0) -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout_secs):
            return True
    except OSError:
        return False
