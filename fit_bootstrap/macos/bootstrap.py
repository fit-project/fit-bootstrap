from fit_common.core import debug

from fit_bootstrap.macos.certificate import CertificateManager
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


class MacBootstrap:
    def __init__(self):
        pass

    def __result_from_code(
        self, code: int, message: str | None = None
    ) -> BootstrapResult:
        if code == 0:
            return BootstrapResult(code=0, signal=BootstrapSignal.OK)
        return BootstrapResult(code=code, signal=BootstrapSignal.ERROR, message=message)

    def install_certificate(self, *, debug_enabled: bool = False) -> BootstrapResult:
        debug("PRE-FLIGHT: verifying CA certificate")
        cert_manager = CertificateManager()
        if cert_manager.add_cert(debug_enabled=debug_enabled) != 0:
            message = "Certificate installation failed"
            debug(f"❌ {message}")
            return self.__result_from_code(1, message)
        return self.__result_from_code(0)

    def run(self, *, debug_enabled: bool = False) -> BootstrapResult:
        cert_result = self.install_certificate(debug_enabled=debug_enabled)
        if cert_result.code != 0:
            return cert_result
        return self.__result_from_code(0)
