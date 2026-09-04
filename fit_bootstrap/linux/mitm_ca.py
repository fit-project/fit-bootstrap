"""Linux-only lifecycle for FIT's per-user mitmproxy CA."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from fit_common.core import debug

from fit_bootstrap.constants import FIT_MITM_CONF_DIR, FIT_USER_APP_PATH
from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

PUBLIC_CA_NAME = "mitmproxy-ca-cert.pem"
PRIVATE_CA_NAMES = ("mitmproxy-ca.pem", "mitmproxy-ca.p12")
SYSTEM_CA_PATH = Path("/usr/local/share/ca-certificates/fit-mitmproxy-ca.crt")
_AUTH_CANCELLED_CODES = {126, 127}
_LOG_CONTEXT = "linux_mitm_ca"


class MitmCAOutcome(str, Enum):
    READY = "ready"
    INSTALL_REQUIRED = "install_required"
    CA_MISSING = "ca_missing"
    INVALID_CERTIFICATE = "invalid_certificate"
    GENERATION_FAILED = "generation_failed"
    TOOL_MISSING = "tool_missing"
    AUTH_CANCELLED = "auth_cancelled"
    INSTALL_FAILED = "install_failed"
    TRUST_NOT_UPDATED = "trust_not_updated"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"


class MitmCAStatus(str, Enum):
    READY = "ready"
    NOT_INSTALLED = "not_installed"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"
    NOT_TRUSTED = "not_trusted"


@dataclass(frozen=True)
class MitmCAResult:
    outcome: MitmCAOutcome
    fingerprint: str | None = None


@dataclass(frozen=True)
class MitmCAInspection:
    status: MitmCAStatus
    installed_fingerprint: str | None = None


def configured_conf_dir() -> Path | None:
    """Return the deterministic FIT confdir, rejecting an external override."""
    app_value = os.environ.get(FIT_USER_APP_PATH)
    if not app_value:
        return None
    app_dir = Path(app_value).expanduser().resolve()
    expected = (app_dir / "mitmproxy" / "conf").resolve()
    configured = os.environ.get(FIT_MITM_CONF_DIR)
    if configured and Path(configured).expanduser().resolve() != expected:
        return None
    os.environ[FIT_MITM_CONF_DIR] = str(expected)
    return expected


def certificate_fingerprint(
    cert_path: Path, openssl: str | None = None
) -> str | None:
    """Validate a public CA certificate and return its normalized SHA-256 digest."""
    binary = openssl or shutil.which("openssl")
    if binary is None or not cert_path.is_file():
        return None
    try:
        info = subprocess.run(
            [
                binary,
                "x509",
                "-in",
                str(cert_path.resolve()),
                "-noout",
                "-checkend",
                "0",
                "-text",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if info.returncode != 0 or "CA:TRUE" not in info.stdout.replace(" ", ""):
            return None
        digest = subprocess.run(
            [
                binary,
                "x509",
                "-in",
                str(cert_path.resolve()),
                "-noout",
                "-fingerprint",
                "-sha256",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if digest.returncode != 0 or "=" not in digest.stdout:
        return None
    value = digest.stdout.split("=", 1)[1].strip().replace(":", "").upper()
    valid = len(value) == 64 and all(c in "0123456789ABCDEF" for c in value)
    return value if valid else None


def private_key_matches_certificate(
    cert_path: Path, private_path: Path, openssl: str | None = None
) -> bool:
    """Check that mitmproxy's private CA key belongs to its public certificate."""
    binary = openssl or shutil.which("openssl")
    if binary is None or not cert_path.is_file() or not private_path.is_file():
        return False
    try:
        cert_key = subprocess.run(
            [binary, "x509", "-in", str(cert_path.resolve()), "-pubkey", "-noout"],
            capture_output=True,
            check=False,
        )
        private_key = subprocess.run(
            [binary, "pkey", "-in", str(private_path.resolve()), "-pubout"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return (
        cert_key.returncode == 0
        and private_key.returncode == 0
        and cert_key.stdout == private_key.stdout
    )


def ensure_ca_material(conf_dir: Path, timeout: float = 15.0) -> MitmCAResult:
    """Create the CA as the desktop user using a short-lived loopback process."""
    try:
        conf_dir = conf_dir.expanduser().resolve()
        conf_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        conf_dir.chmod(0o700)
    except OSError:
        return MitmCAResult(MitmCAOutcome.GENERATION_FAILED)

    public_ca = conf_dir / PUBLIC_CA_NAME
    fingerprint = certificate_fingerprint(public_ca)
    private_ca = conf_dir / PRIVATE_CA_NAMES[0]
    if fingerprint is not None and private_key_matches_certificate(
        public_ca, private_ca
    ):
        _restrict_private_material(conf_dir)
        return MitmCAResult(MitmCAOutcome.READY, fingerprint)

    # Preserve broken material while freeing canonical names for mitmproxy.
    suffix = f".invalid-{time.time_ns()}"
    try:
        for name in (PUBLIC_CA_NAME, *PRIVATE_CA_NAMES):
            path = conf_dir / name
            if path.exists():
                path.replace(conf_dir / f"{name}{suffix}")
    except OSError:
        return MitmCAResult(MitmCAOutcome.GENERATION_FAILED)

    try:
        port = _free_loopback_port()
    except OSError:
        return MitmCAResult(MitmCAOutcome.GENERATION_FAILED)
    command = _mitmdump_command() + [
        "--listen-host", "127.0.0.1", "--listen-port", str(port),
        "--set", f"confdir={conf_dir}",
    ]
    proc: subprocess.Popen[bytes] | None = None
    try:
        child_env = os.environ.copy()
        if getattr(sys, "frozen", False):
            child_env["FIT_MITM_LAUNCH"] = "1"
        proc = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=child_env,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if (
                certificate_fingerprint(public_ca) is not None
                and private_key_matches_certificate(public_ca, private_ca)
            ):
                break
            if proc.poll() is not None:
                break
            time.sleep(0.05)
    except (OSError, ValueError):
        return MitmCAResult(MitmCAOutcome.GENERATION_FAILED)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    fingerprint = certificate_fingerprint(public_ca)
    if fingerprint is None or not private_key_matches_certificate(
        public_ca, private_ca
    ):
        return MitmCAResult(MitmCAOutcome.GENERATION_FAILED)
    _restrict_private_material(conf_dir)
    return MitmCAResult(MitmCAOutcome.READY, fingerprint)


def ensure_linux_mitm_ca(*, allow_install: bool = True) -> MitmCAResult:
    """Ensure FIT's generated CA is the CA trusted by Debian's system store."""
    conf_dir = configured_conf_dir()
    if conf_dir is None:
        return MitmCAResult(MitmCAOutcome.CA_MISSING)
    openssl = shutil.which("openssl")
    update_certs = shutil.which("update-ca-certificates")
    if openssl is None or update_certs is None:
        return MitmCAResult(MitmCAOutcome.TOOL_MISSING)
    generated = ensure_ca_material(conf_dir)
    if generated.outcome != MitmCAOutcome.READY:
        return generated
    expected_fingerprint = generated.fingerprint
    if expected_fingerprint is None:
        return MitmCAResult(MitmCAOutcome.INVALID_CERTIFICATE)

    source = (conf_dir / PUBLIC_CA_NAME).resolve()
    if (
        source.parent != conf_dir
        or certificate_fingerprint(source, openssl) != expected_fingerprint
    ):
        return MitmCAResult(MitmCAOutcome.INVALID_CERTIFICATE)

    inspection = inspect_linux_mitm_ca(source, expected_fingerprint, openssl)
    debug(
        f"Linux mitm CA inspection: {inspection.status.value}",
        context=_LOG_CONTEXT,
    )
    if inspection.status == MitmCAStatus.READY:
        return MitmCAResult(MitmCAOutcome.READY, expected_fingerprint)
    if not allow_install:
        return MitmCAResult(MitmCAOutcome.INSTALL_REQUIRED, expected_fingerprint)

    pkexec = shutil.which("pkexec")
    helper = Path(__file__).with_name("install_mitm_ca.sh")
    if pkexec is None or not helper.is_file() or not os.access(helper, os.X_OK):
        return MitmCAResult(MitmCAOutcome.TOOL_MISSING)
    try:
        result = subprocess.run(
            [pkexec, str(helper), str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return MitmCAResult(MitmCAOutcome.INSTALL_FAILED)
    if result.returncode in _AUTH_CANCELLED_CODES:
        return MitmCAResult(MitmCAOutcome.AUTH_CANCELLED)
    if result.returncode != 0:
        debug(
            f"Linux mitm CA helper failed: {(result.stderr or '').strip()}",
            context=_LOG_CONTEXT,
        )
        return MitmCAResult(MitmCAOutcome.INSTALL_FAILED)

    installed_fingerprint = certificate_fingerprint(SYSTEM_CA_PATH, openssl)
    if installed_fingerprint != expected_fingerprint:
        return MitmCAResult(MitmCAOutcome.FINGERPRINT_MISMATCH)
    if not _is_trusted(source, openssl):
        return MitmCAResult(MitmCAOutcome.TRUST_NOT_UPDATED)
    return MitmCAResult(MitmCAOutcome.READY, expected_fingerprint)


def inspect_linux_mitm_ca(
    source: Path,
    expected_fingerprint: str,
    openssl: str,
) -> MitmCAInspection:
    """Inspect the system CA as the desktop user without requesting elevation."""
    installed_fingerprint = certificate_fingerprint(SYSTEM_CA_PATH, openssl)
    if installed_fingerprint is None:
        return MitmCAInspection(MitmCAStatus.NOT_INSTALLED)
    if installed_fingerprint != expected_fingerprint:
        return MitmCAInspection(
            MitmCAStatus.FINGERPRINT_MISMATCH,
            installed_fingerprint,
        )
    if not _is_trusted(source, openssl):
        return MitmCAInspection(MitmCAStatus.NOT_TRUSTED, installed_fingerprint)
    return MitmCAInspection(MitmCAStatus.READY, installed_fingerprint)


def ensure_linux_mitm_ca_preflight() -> BootstrapResult | None:
    result = ensure_linux_mitm_ca()
    return linux_mitm_ca_result_to_bootstrap(result)


def linux_mitm_ca_result_to_bootstrap(
    result: MitmCAResult,
) -> BootstrapResult | None:
    """Convert a CA lifecycle result into the bootstrap contract."""
    if result.outcome == MitmCAOutcome.READY:
        return None
    key = {
        MitmCAOutcome.INSTALL_REQUIRED: (
            "BOOSTSTRAP_LINUX_MITM_CA_INSTALL_REQUEST_MESSAGE"
        ),
        MitmCAOutcome.CA_MISSING: "BOOSTSTRAP_LINUX_MITM_CA_MISSING_MESSAGE",
        MitmCAOutcome.INVALID_CERTIFICATE: "BOOSTSTRAP_LINUX_MITM_CA_INVALID_MESSAGE",
        MitmCAOutcome.GENERATION_FAILED: (
            "BOOSTSTRAP_LINUX_MITM_CA_GENERATION_FAILED_MESSAGE"
        ),
        MitmCAOutcome.TOOL_MISSING: "BOOSTSTRAP_LINUX_MITM_CA_TOOL_MISSING_MESSAGE",
        MitmCAOutcome.AUTH_CANCELLED: "BOOSTSTRAP_LINUX_MITM_CA_AUTH_CANCELLED_MESSAGE",
        MitmCAOutcome.INSTALL_FAILED: "BOOSTSTRAP_LINUX_MITM_CA_INSTALL_FAILED_MESSAGE",
        MitmCAOutcome.TRUST_NOT_UPDATED: (
            "BOOSTSTRAP_LINUX_MITM_CA_TRUST_FAILED_MESSAGE"
        ),
        MitmCAOutcome.FINGERPRINT_MISMATCH: (
            "BOOSTSTRAP_LINUX_MITM_CA_FINGERPRINT_MESSAGE"
        ),
    }[result.outcome]
    return BootstrapResult(1, BootstrapSignal.ERROR, load_translations().get(key, ""))


def _is_trusted(cert_path: Path, openssl: str) -> bool:
    try:
        result = subprocess.run(
            [openssl, "verify", str(cert_path)],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def _restrict_private_material(conf_dir: Path) -> None:
    for name in PRIVATE_CA_NAMES:
        path = conf_dir / name
        if path.exists():
            path.chmod(0o600)


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _mitmdump_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [
        sys.executable,
        "-c",
        "from mitmproxy.tools.main import mitmdump; mitmdump()",
    ]
