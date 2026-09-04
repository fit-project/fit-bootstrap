from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from fit_bootstrap.constants import FIT_MITM_CONF_DIR, FIT_USER_APP_PATH
from fit_bootstrap.linux import mitm_ca

FP_A = "A" * 64
FP_B = "B" * 64


@pytest.mark.unit
def test_configured_conf_dir_is_deterministic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    monkeypatch.delenv(FIT_MITM_CONF_DIR, raising=False)
    expected = (tmp_path / "mitmproxy" / "conf").resolve()
    assert mitm_ca.configured_conf_dir() == expected
    assert os.environ[FIT_MITM_CONF_DIR] == str(expected)


@pytest.mark.unit
def test_configured_conf_dir_rejects_external_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path / "app"))
    monkeypatch.setenv(FIT_MITM_CONF_DIR, str(tmp_path / "elsewhere"))
    assert mitm_ca.configured_conf_dir() is None


@pytest.mark.unit
def test_existing_valid_ca_is_preserved_and_permissions_restricted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    conf = tmp_path / "conf"
    conf.mkdir(mode=0o755)
    public = conf / mitm_ca.PUBLIC_CA_NAME
    private = conf / "mitmproxy-ca.pem"
    public.write_text("public")
    private.write_text("private")
    private.chmod(0o644)
    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", lambda path, openssl=None: FP_A if path == public else None)
    monkeypatch.setattr(mitm_ca, "private_key_matches_certificate", lambda *_a: True)
    monkeypatch.setattr(mitm_ca.subprocess, "Popen", lambda *_a, **_k: pytest.fail("must not generate"))
    result = mitm_ca.ensure_ca_material(conf)
    assert result.fingerprint == FP_A
    assert stat.S_IMODE(conf.stat().st_mode) == 0o700
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    assert private.read_text() == "private"


class _GeneratedProcess:
    def __init__(self, conf: Path, valid: dict[str, bool]) -> None:
        (conf / mitm_ca.PUBLIC_CA_NAME).write_text("public")
        (conf / "mitmproxy-ca.pem").write_text("private")
        valid["value"] = True
        self.terminated = False
        self.pid = 10

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout=None) -> int:
        return 0

    def kill(self) -> None:
        self.terminated = True


@pytest.mark.unit
def test_missing_ca_is_generated_on_loopback_and_process_stopped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    conf = tmp_path / "conf"
    valid = {"value": False}
    process: list[_GeneratedProcess] = []
    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", lambda path, openssl=None: FP_A if valid["value"] else None)
    monkeypatch.setattr(mitm_ca, "private_key_matches_certificate", lambda *_a: valid["value"])
    monkeypatch.setattr(mitm_ca, "_free_loopback_port", lambda: 43210)
    def popen(command, **kwargs):
        assert ["--listen-host", "127.0.0.1"] == command[-6:-4]
        assert "confdir=" + str(conf.resolve()) == command[-1]
        assert "shell" not in kwargs
        proc = _GeneratedProcess(conf, valid)
        process.append(proc)
        return proc
    monkeypatch.setattr(mitm_ca.subprocess, "Popen", popen)
    result = mitm_ca.ensure_ca_material(conf, timeout=0.2)
    assert result.outcome == mitm_ca.MitmCAOutcome.READY
    assert process[0].terminated
    assert stat.S_IMODE(conf.stat().st_mode) == 0o700
    assert stat.S_IMODE((conf / "mitmproxy-ca.pem").stat().st_mode) == 0o600


@pytest.mark.unit
def test_invalid_partial_files_are_quarantined_before_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    conf = tmp_path / "conf"
    conf.mkdir()
    (conf / mitm_ca.PUBLIC_CA_NAME).write_text("bad")
    (conf / "mitmproxy-ca.pem").write_text("bad-key")
    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", lambda *_a, **_k: None)
    monkeypatch.setattr(mitm_ca, "private_key_matches_certificate", lambda *_a: False)
    monkeypatch.setattr(mitm_ca, "_free_loopback_port", lambda: 1234)
    class Failed:
        def poll(self): return 1
    monkeypatch.setattr(mitm_ca.subprocess, "Popen", lambda *_a, **_k: Failed())
    result = mitm_ca.ensure_ca_material(conf, timeout=0)
    assert result.outcome == mitm_ca.MitmCAOutcome.GENERATION_FAILED
    assert list(conf.glob("mitmproxy-ca.pem.invalid-*"))
    assert not (conf / "mitmproxy-ca.pem").exists()


@pytest.mark.unit
def test_generation_timeout_always_kills_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", lambda *_a, **_k: None)
    monkeypatch.setattr(mitm_ca, "private_key_matches_certificate", lambda *_a: False)
    monkeypatch.setattr(mitm_ca, "_free_loopback_port", lambda: 1234)
    class Hanging:
        killed = False
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=None):
            if timeout is not None: raise subprocess.TimeoutExpired("mitmdump", timeout)
            return 0
        def kill(self): self.killed = True
    proc = Hanging()
    monkeypatch.setattr(mitm_ca.subprocess, "Popen", lambda *_a, **_k: proc)
    result = mitm_ca.ensure_ca_material(tmp_path / "conf", timeout=0)
    assert result.outcome == mitm_ca.MitmCAOutcome.GENERATION_FAILED
    assert proc.killed


@pytest.mark.unit
def test_sha256_fingerprint_and_ca_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cert = tmp_path / "ca.pem"
    cert.write_text("certificate")
    calls = iter([
        subprocess.CompletedProcess([], 0, "X509v3 Basic Constraints: critical\n CA:TRUE\n", ""),
        subprocess.CompletedProcess([], 0, "sha256 Fingerprint=" + ":".join("AA" for _ in range(32)), ""),
    ])
    monkeypatch.setattr(mitm_ca.subprocess, "run", lambda command, **kwargs: next(calls))
    assert mitm_ca.certificate_fingerprint(cert, "/usr/bin/openssl") == FP_A


@pytest.mark.unit
def test_is_trusted_verifies_ca_against_trust_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cert = tmp_path / "ca.pem"
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mitm_ca.subprocess, "run", run)

    assert mitm_ca._is_trusted(cert, "/usr/bin/openssl")
    assert calls == [
        (
            ["/usr/bin/openssl", "verify", str(cert)],
            {"capture_output": True, "text": True, "check": False},
        )
    ]
    command, kwargs = calls[0]
    assert "shell" not in kwargs
    assert "sudo" not in command
    assert "pkexec" not in command
    assert "-purpose" not in command
    assert "sslserver" not in command


@pytest.mark.unit
def test_is_trusted_returns_false_for_untrusted_ca(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        mitm_ca.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 2),
    )

    assert not mitm_ca._is_trusted(tmp_path / "ca.pem", "/usr/bin/openssl")


@pytest.mark.unit
def test_is_trusted_returns_false_on_execution_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def run(_command, **_kwargs):
        raise OSError("openssl unavailable")

    monkeypatch.setattr(mitm_ca.subprocess, "run", run)

    assert not mitm_ca._is_trusted(tmp_path / "ca.pem", "/usr/bin/openssl")


def _prepare_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, installed: str | None, trusted: bool):
    conf = tmp_path / "mitmproxy" / "conf"
    conf.mkdir(parents=True)
    source = conf / mitm_ca.PUBLIC_CA_NAME
    source.write_text("public")
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    monkeypatch.setenv(FIT_MITM_CONF_DIR, str(conf))
    monkeypatch.setattr(mitm_ca, "ensure_ca_material", lambda _path: mitm_ca.MitmCAResult(mitm_ca.MitmCAOutcome.READY, FP_A))
    def fingerprint(path, openssl=None):
        return FP_A if path.resolve() == source.resolve() else installed
    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", fingerprint)
    monkeypatch.setattr(mitm_ca, "_is_trusted", lambda *_a: trusted)
    monkeypatch.setattr(mitm_ca.shutil, "which", lambda name: "/usr/bin/" + name)
    return source


@pytest.mark.unit
def test_matching_installed_and_trusted_ca_needs_no_elevation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _prepare_install(monkeypatch, tmp_path, FP_A, True)
    monkeypatch.setattr(mitm_ca.subprocess, "run", lambda *_a, **_k: pytest.fail("no elevation expected"))
    assert mitm_ca.ensure_linux_mitm_ca().outcome == mitm_ca.MitmCAOutcome.READY


@pytest.mark.unit
@pytest.mark.parametrize(
    ("installed", "trusted", "expected"),
    [
        (None, False, mitm_ca.MitmCAStatus.NOT_INSTALLED),
        (FP_B, False, mitm_ca.MitmCAStatus.FINGERPRINT_MISMATCH),
        (FP_A, False, mitm_ca.MitmCAStatus.NOT_TRUSTED),
        (FP_A, True, mitm_ca.MitmCAStatus.READY),
    ],
)
def test_inspect_linux_mitm_ca_reports_unprivileged_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    installed: str | None,
    trusted: bool,
    expected: mitm_ca.MitmCAStatus,
) -> None:
    source = tmp_path / "ca.pem"
    monkeypatch.setattr(
        mitm_ca,
        "certificate_fingerprint",
        lambda *_args, **_kwargs: installed,
    )
    monkeypatch.setattr(mitm_ca, "_is_trusted", lambda *_args: trusted)

    inspection = mitm_ca.inspect_linux_mitm_ca(source, FP_A, "/usr/bin/openssl")

    assert inspection.status == expected


@pytest.mark.unit
def test_matching_installed_ca_passes_preflight_without_reinstallation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    is_trusted = mitm_ca._is_trusted
    source = _prepare_install(monkeypatch, tmp_path, FP_A, True)
    monkeypatch.setattr(mitm_ca, "_is_trusted", is_trusted)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mitm_ca.subprocess, "run", run)

    assert mitm_ca.ensure_linux_mitm_ca().outcome == mitm_ca.MitmCAOutcome.READY
    assert mitm_ca.ensure_linux_mitm_ca_preflight() is None
    assert calls == [
        ["/usr/bin/openssl", "verify", str(source.resolve())],
        ["/usr/bin/openssl", "verify", str(source.resolve())],
    ]
    assert all("install" not in command and "pkexec" not in command for command in calls)


@pytest.mark.unit
@pytest.mark.parametrize("installed", [None, FP_B])
def test_installs_only_public_ca_and_updates_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, installed: str | None) -> None:
    source = _prepare_install(monkeypatch, tmp_path, installed, False)
    calls = []
    monkeypatch.setattr(mitm_ca, "_is_trusted", lambda *_a: len(calls) == 1)
    def run(command, **kwargs):
        calls.append(command)
        assert "shell" not in kwargs
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr(mitm_ca.subprocess, "run", run)
    fingerprints = iter([FP_A, installed, FP_A])
    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", lambda *_a, **_k: next(fingerprints))
    result = mitm_ca.ensure_linux_mitm_ca()
    assert result.outcome == mitm_ca.MitmCAOutcome.READY
    assert calls == [
        [
            "/usr/bin/pkexec",
            str(Path(mitm_ca.__file__).with_name("install_mitm_ca.sh")),
            str(source.resolve()),
        ]
    ]
    assert all("mitmproxy-ca.pem" not in arg for command in calls for arg in command)


@pytest.mark.unit
@pytest.mark.parametrize(("returncode", "expected"), [(126, mitm_ca.MitmCAOutcome.AUTH_CANCELLED), (1, mitm_ca.MitmCAOutcome.INSTALL_FAILED)])
def test_privileged_install_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, returncode: int, expected: mitm_ca.MitmCAOutcome) -> None:
    _prepare_install(monkeypatch, tmp_path, None, False)
    monkeypatch.setattr(mitm_ca.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, returncode))
    assert mitm_ca.ensure_linux_mitm_ca().outcome == expected


@pytest.mark.unit
def test_missing_update_ca_certificates_fails_without_elevation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _prepare_install(monkeypatch, tmp_path, None, False)
    monkeypatch.setattr(mitm_ca.shutil, "which", lambda name: None if name == "update-ca-certificates" else "/usr/bin/" + name)
    monkeypatch.setattr(mitm_ca.subprocess, "run", lambda *_a, **_k: pytest.fail("must not elevate"))
    assert mitm_ca.ensure_linux_mitm_ca().outcome == mitm_ca.MitmCAOutcome.TOOL_MISSING


@pytest.mark.unit
def test_post_install_fingerprint_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _prepare_install(monkeypatch, tmp_path, FP_B, False)
    monkeypatch.setattr(mitm_ca.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0))
    assert mitm_ca.ensure_linux_mitm_ca().outcome == mitm_ca.MitmCAOutcome.FINGERPRINT_MISMATCH


@pytest.mark.unit
def test_post_install_trust_verification_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _prepare_install(monkeypatch, tmp_path, FP_A, False)
    calls = {"fingerprint": 0}

    def fingerprint(_path, openssl=None):
        calls["fingerprint"] += 1
        return FP_A if calls["fingerprint"] != 2 else None

    monkeypatch.setattr(mitm_ca, "certificate_fingerprint", fingerprint)
    monkeypatch.setattr(
        mitm_ca.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0),
    )
    assert (
        mitm_ca.ensure_linux_mitm_ca().outcome
        == mitm_ca.MitmCAOutcome.TRUST_NOT_UPDATED
    )


@pytest.mark.unit
def test_update_ca_certificates_failure_is_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _prepare_install(monkeypatch, tmp_path, None, False)
    monkeypatch.setattr(
        mitm_ca.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1),
    )
    assert (
        mitm_ca.ensure_linux_mitm_ca().outcome
        == mitm_ca.MitmCAOutcome.INSTALL_FAILED
    )
