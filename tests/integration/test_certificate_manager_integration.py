from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from fit_bootstrap.macos import certificate as certificate_module


@pytest.mark.integration
def test_add_cert_invokes_security_add_trusted_cert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("dummy", encoding="utf-8")

    manager = certificate_module.CertificateManager()
    manager.cert_path = cert_path
    manager.cert_sha1 = "ABCDEF"

    monkeypatch.setattr(
        manager,
        "_CertificateManager__cert_exists_in_keychain",
        lambda _keychain=None: False,
    )
    monkeypatch.setattr(certificate_module, "is_admin", lambda: True)
    captured: dict[str, object] = {}

    def _fake_run(cmd, capture_output, text, env, check):  # noqa: ARG001
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(certificate_module.subprocess, "run", _fake_run)

    rc = manager.add_cert()

    assert rc == 0
    cmd = captured["cmd"]  # type: ignore[assignment]
    assert cmd[0:3] == ["security", "add-trusted-cert", "-r"]  # type: ignore[index]
    assert "-d" in cmd  # type: ignore[operator]
    assert cert_path.as_posix() in cmd  # type: ignore[operator]


@pytest.mark.integration
def test_add_cert_duplicate_message_is_treated_as_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("dummy", encoding="utf-8")

    manager = certificate_module.CertificateManager()
    manager.cert_path = cert_path
    manager.cert_sha1 = "ABCDEF"

    monkeypatch.setattr(
        manager,
        "_CertificateManager__cert_exists_in_keychain",
        lambda _keychain=None: False,
    )
    monkeypatch.setattr(certificate_module, "is_admin", lambda: True)
    monkeypatch.setattr(
        certificate_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(  # noqa: ARG005
            returncode=1,
            stdout="certificate already exists",
            stderr="",
        ),
    )

    assert manager.add_cert() == 0
