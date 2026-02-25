from __future__ import annotations

import io
from urllib import error

import pytest

from fit_bootstrap import context as context_module


class _FakeSocket:
    def __init__(self, ip: str = "192.168.1.55", fail_connect: bool = False) -> None:
        self._ip = ip
        self._fail_connect = fail_connect

    def __enter__(self) -> "_FakeSocket":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def connect(self, _endpoint) -> None:
        if self._fail_connect:
            raise OSError("connect failed")

    def getsockname(self) -> tuple[str, int]:
        return (self._ip, 0)


@pytest.mark.unit
def test_resolve_host_ip_uses_udp_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        context_module.socket, "socket", lambda *_args, **_kwargs: _FakeSocket()
    )

    assert context_module.AcquisitionContext._resolve_host_ip() == "192.168.1.55"


@pytest.mark.unit
def test_resolve_host_ip_falls_back_to_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        context_module.socket,
        "socket",
        lambda *_args, **_kwargs: _FakeSocket(fail_connect=True),
    )
    monkeypatch.setattr(context_module.socket, "gethostname", lambda: "myhost")
    monkeypatch.setattr(context_module.socket, "gethostbyname", lambda _h: "10.0.0.4")

    assert context_module.AcquisitionContext._resolve_host_ip() == "10.0.0.4"


@pytest.mark.unit
def test_resolve_public_ip_skips_invalid_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = iter(
        [
            error.URLError("no network"),
            "not-an-ip",
            "203.0.113.10",
        ]
    )

    class _Resp:
        def __init__(self, body: str) -> None:
            self._body = body

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            return None

        def read(self) -> bytes:
            return self._body.encode("utf-8")

    def _fake_urlopen(_endpoint: str, timeout: float):  # noqa: ARG001
        item = next(payloads)
        if isinstance(item, Exception):
            raise item
        return _Resp(item)

    monkeypatch.setattr(context_module.request, "urlopen", _fake_urlopen)

    assert context_module.AcquisitionContext._resolve_public_ip() == "203.0.113.10"


@pytest.mark.unit
def test_read_dns_servers_parses_nameserver_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    content = io.StringIO(
        "# comment\n\nnameserver 1.1.1.1\nsearch local\nnameserver 8.8.8.8\n"
    )
    monkeypatch.setattr("builtins.open", lambda *_args, **_kwargs: content)

    assert context_module.AcquisitionContext._read_dns_servers() == ["1.1.1.1", "8.8.8.8"]


@pytest.mark.unit
def test_collect_builds_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(context_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(context_module.platform, "platform", lambda: "macOS-14")
    monkeypatch.setattr(context_module.getpass, "getuser", lambda: "alice")
    monkeypatch.setattr(
        context_module.AcquisitionContext, "_resolve_host_ip", staticmethod(lambda: "10.0.0.2")
    )
    monkeypatch.setattr(
        context_module.AcquisitionContext, "_resolve_public_ip", staticmethod(lambda: "198.51.100.1")
    )
    monkeypatch.setattr(
        context_module.AcquisitionContext, "_read_dns_servers", staticmethod(lambda: ["9.9.9.9"])
    )

    ctx = context_module.AcquisitionContext.collect()

    assert ctx.os_type == "Darwin"
    assert ctx.os_version == "macOS-14"
    assert ctx.username == "alice"
    assert ctx.host_ip == "10.0.0.2"
    assert ctx.public_ip == "198.51.100.1"
    assert ctx.dns_servers == ["9.9.9.9"]
