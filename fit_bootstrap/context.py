from __future__ import annotations

from dataclasses import dataclass
import getpass
import platform
import socket
from typing import List


@dataclass(frozen=True)
class AcquisitionContext:
    os_type: str
    os_version: str
    username: str
    host_ip: str
    dns_servers: List[str]


    @staticmethod
    def _resolve_host_ip() -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except OSError:
                return "unknown"

    @staticmethod
    def _read_dns_servers() -> List[str]:
        servers: List[str] = []
        try:
            with open("/etc/resolv.conf", "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.lower().startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            servers.append(parts[1])
        except OSError:
            pass
        return servers

    @classmethod
    def collect(cls) -> "AcquisitionContext":
        return cls(
            os_type=platform.system(),
            os_version=platform.platform(),
            username=getpass.getuser(),
            host_ip=cls._resolve_host_ip(),
            dns_servers=cls._read_dns_servers(),
        )
