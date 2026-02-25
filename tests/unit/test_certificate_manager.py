from __future__ import annotations

from pathlib import Path

import pytest

from fit_bootstrap.macos import certificate as certificate_module


@pytest.mark.unit
def test_add_cert_fails_when_certificate_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = certificate_module.CertificateManager()
    manager.cert_path = Path("/tmp/missing-cert.pem")
    manager.cert_sha1 = "ABCDEF"

    assert manager.add_cert() == 1


@pytest.mark.unit
def test_add_cert_fails_when_sha1_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("x", encoding="utf-8")

    manager = certificate_module.CertificateManager()
    manager.cert_path = cert_path
    manager.cert_sha1 = None

    assert manager.add_cert() == 1


@pytest.mark.unit
def test_add_cert_returns_success_when_cert_already_in_keychain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("x", encoding="utf-8")

    manager = certificate_module.CertificateManager()
    manager.cert_path = cert_path
    manager.cert_sha1 = "ABCDEF"
    monkeypatch.setattr(
        manager,
        "_CertificateManager__cert_exists_in_keychain",
        lambda _keychain=None: True,
    )

    assert manager.add_cert() == 0
