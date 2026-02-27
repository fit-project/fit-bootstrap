from fit_common.core import debug, get_context

from fit_bootstrap.macos.certificate import CertificateManager
from fit_bootstrap.macos.permission import PermissionChecker
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


class MacBootstrap:
    def __init__(self):
        self._permission_checker = PermissionChecker()

    def __result_from_code(
        self, code: int, message: str | None = None
    ) -> BootstrapResult:
        if code == 0:
            return BootstrapResult(code=0, signal=BootstrapSignal.OK)
        return BootstrapResult(code=code, signal=BootstrapSignal.ERROR, message=message)

    def install_certificate(self) -> BootstrapResult:
        debug("PRE-FLIGHT: verifying CA certificate", context=get_context(self))
        cert_manager = CertificateManager()
        if cert_manager.add_cert() != 0:
            message = "Certificate installation failed"
            debug(f"❌ {message}", context=get_context(self))
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.CERTIFICATE_NOT_INSTALLED,
                message=message,
            )
        return self.__result_from_code(0)

    def ensure_permissions(self) -> BootstrapResult:
        debug("ℹ️ verifying screen recording permissions", context=get_context(self))
        return self._permission_checker.run()
