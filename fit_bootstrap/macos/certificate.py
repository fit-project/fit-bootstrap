from __future__ import annotations

import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from fit_common.core import debug


class CertificateManager:
    CERT_PATH = Path(
        str(files("fit_assets").joinpath("mitmproxy/mitmproxy-ca-cert.pem"))
    )
    debug(f"Certificate path: {CERT_PATH}")
    KEYCHAIN = "/Library/Keychains/System.keychain"

    def __init__(self):
        self.cert_path = self.CERT_PATH
        self.keychain = self.KEYCHAIN
        self.cert_sha1 = self.__compute_sha1() if self.cert_path.exists() else None

    def __compute_sha1(self) -> str | None:
        if not self.cert_path.exists():
            debug(f"Certificate not found: {self.cert_path}")
            return None

        try:
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in",
                    str(self.cert_path),
                    "-noout",
                    "-fingerprint",
                    "-sha1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            fingerprint = result.stdout.split("=")[1].replace(":", "")
            return fingerprint.strip()
        except FileNotFoundError:
            debug("❌ OpenSSL not found. Install via: brew install openssl")
            return None
        except (subprocess.CalledProcessError, IndexError) as e:
            debug(f"Error computing SHA1: {e}")
            return None

    def __cert_exists_in_keychain(self, keychain: str | None = None) -> bool:
        if not self.cert_sha1:
            return False

        try:
            result = subprocess.run(
                ["security", "find-certificate", "-a", "-Z", keychain or self.keychain],
                capture_output=True,
                text=True,
                check=False,
            )

            return self.cert_sha1 in result.stdout
        except subprocess.CalledProcessError as e:
            debug(f"Error searching for certificate: {e}")
            return False

    def add_cert(self, keychain: str | None = None) -> int:
        if not self.cert_path.exists():
            debug(f"❌ Certificate not found: {self.cert_path}")
            debug("Start mitmproxy once to generate it.")
            return 1

        if not self.cert_sha1:
            debug("❌ Unable to compute certificate SHA1")
            return 1

        keychain_path = keychain or self.keychain
        debug(
            f"➕ Adding mitmproxy certificate (SHA1={self.cert_sha1}) to {keychain_path}"
        )

        if self.__cert_exists_in_keychain(keychain_path):
            debug("ℹ️ Certificate already present, skipping.")
            return 0

        try:
            cmd = [
                "security",
                "add-trusted-cert",
                "-r",
                "trustRoot",
            ]
            if keychain_path == self.KEYCHAIN:
                cmd.append("-d")
            cmd += [
                "-k",
                keychain_path,
                str(self.cert_path),
            ]
            askpass = Path(__file__).parent / "askpass.sh"
            env = os.environ.copy()
            if askpass.exists():
                env["SUDO_ASKPASS"] = str(askpass)
                env["FIT_ASKPASS_MODE"] = "pyside"
                env["FIT_ASKPASS_PYTHON"] = sys.executable
                if os.environ.get("FIT_BOOTSTRAP_DEBUG") == "1":
                    env["FIT_ASKPASS_DEBUG"] = "1"
                    if "FIT_ASKPASS_LOG" in os.environ:
                        env["FIT_ASKPASS_LOG"] = os.environ["FIT_ASKPASS_LOG"]
                env["DISPLAY"] = env.get("DISPLAY", ":0")
                result = subprocess.run(
                    ["sudo", "-A", *cmd],
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False,
                )
            else:
                result = subprocess.run(
                    ["sudo", *cmd],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                stdout = result.stdout.strip()
                duplicate = (
                    "already exists" in stderr.lower()
                    or "already exists" in stdout.lower()
                )
                if not duplicate:
                    debug(f"❌ Error during installation: {stderr or stdout}")
                    return 1
            debug("✅ Certificate installed and trusted.")
            return 0
        except subprocess.CalledProcessError as e:
            debug(f"❌ Error during installation: {e}")
            if e.stdout:
                debug(f"❌ Installer stdout: {e.stdout.strip()}")
            if e.stderr:
                debug(f"❌ Installer stderr: {e.stderr.strip()}")
            return 1
