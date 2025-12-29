from __future__ import annotations

import ctypes
import socket
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional

import platform

IS_WINDOWS = platform.system().lower() == "windows"

# Windows ICMP API: IcmpCreateFile / IcmpSendEcho / IcmpCloseHandle (iphlpapi.dll)
# https://learn.microsoft.com/windows/win32/api/icmpapi/

if IS_WINDOWS:
    iphlpapi = ctypes.WinDLL("iphlpapi.dll")
    ws2_32 = ctypes.WinDLL("ws2_32.dll")
else:
    iphlpapi = None
    ws2_32 = None


class IP_OPTION_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Ttl", ctypes.c_ubyte),
        ("Tos", ctypes.c_ubyte),
        ("Flags", ctypes.c_ubyte),
        ("OptionsSize", ctypes.c_ubyte),
        ("OptionsData", ctypes.c_void_p),
    ]


class ICMP_ECHO_REPLY(ctypes.Structure):
    _fields_ = [
        ("Address", wintypes.DWORD),
        ("Status", wintypes.DWORD),
        ("RoundTripTime", wintypes.DWORD),
        ("DataSize", wintypes.WORD),
        ("Reserved", wintypes.WORD),
        ("Data", ctypes.c_void_p),
        ("Options", IP_OPTION_INFORMATION),
    ]


IPAddr = wintypes.DWORD
HANDLE = wintypes.HANDLE


if IS_WINDOWS:
    iphlpapi.IcmpCreateFile.restype = HANDLE
    iphlpapi.IcmpCreateFile.argtypes = []

    iphlpapi.IcmpCloseHandle.restype = wintypes.BOOL
    iphlpapi.IcmpCloseHandle.argtypes = [HANDLE]

    iphlpapi.IcmpSendEcho.restype = wintypes.DWORD
    iphlpapi.IcmpSendEcho.argtypes = [
        HANDLE,          # IcmpHandle
        IPAddr,          # DestinationAddress
        ctypes.c_void_p, # RequestData
        wintypes.WORD,   # RequestSize
        ctypes.c_void_p, # RequestOptions
        ctypes.c_void_p, # ReplyBuffer
        wintypes.DWORD,  # ReplySize
        wintypes.DWORD,  # Timeout
    ]

    ws2_32.inet_addr.restype = IPAddr
    ws2_32.inet_addr.argtypes = [ctypes.c_char_p]


@dataclass(frozen=True)
class IcmpPingResult:
    ok: bool
    rtt_ms: Optional[int] = None
    status_code: int = 0


class IcmpClient:
    def __init__(self) -> None:
        if not IS_WINDOWS:
            raise RuntimeError("ICMP client is Windows-only")

        self._handle = iphlpapi.IcmpCreateFile()
        if not self._handle:
            raise OSError("IcmpCreateFile failed")

        self._payload = b"klimozawr"
        self._reply_size = ctypes.sizeof(ICMP_ECHO_REPLY) + len(self._payload) + 32
        self._reply_buf = ctypes.create_string_buffer(self._reply_size)

    def close(self) -> None:
        if self._handle:
            iphlpapi.IcmpCloseHandle(self._handle)
            self._handle = None

    def ping_once(self, ip: str, timeout_ms: int) -> IcmpPingResult:
        ip_bytes = ip.encode("ascii", errors="ignore")
        dest = ws2_32.inet_addr(ip_bytes)
        if dest == 0xFFFFFFFF:  # INADDR_NONE
            return IcmpPingResult(False, None, status_code=1)

        req_data = ctypes.c_char_p(self._payload)
        req_size = wintypes.WORD(len(self._payload))

        # zero reply buffer
        ctypes.memset(self._reply_buf, 0, self._reply_size)

        ret = iphlpapi.IcmpSendEcho(
            self._handle,
            dest,
            ctypes.cast(req_data, ctypes.c_void_p),
            req_size,
            None,
            ctypes.cast(self._reply_buf, ctypes.c_void_p),
            wintypes.DWORD(self._reply_size),
            wintypes.DWORD(timeout_ms),
        )

        if ret == 0:
            # timeout or error
            return IcmpPingResult(False, None, status_code=0)

        reply = ICMP_ECHO_REPLY.from_buffer_copy(self._reply_buf.raw[: ctypes.sizeof(ICMP_ECHO_REPLY)])
        # Status == 0 means IP_SUCCESS
        if reply.Status == 0:
            return IcmpPingResult(True, int(reply.RoundTripTime), status_code=0)
        return IcmpPingResult(False, None, status_code=int(reply.Status))

    def ping_three(self, ip: str, timeout_ms: int) -> list[Optional[int]]:
        rtts: list[Optional[int]] = []
        for _ in range(3):
            r = self.ping_once(ip, timeout_ms=timeout_ms)
            rtts.append(r.rtt_ms if r.ok else None)
        return rtts
