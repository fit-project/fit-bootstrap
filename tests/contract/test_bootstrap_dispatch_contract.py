from __future__ import annotations

import os

import pytest

from fit_bootstrap import bootstrap as bootstrap_module
from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.context import AcquisitionContext
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


def _patch_bootstrap_init_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap_module, "resolve_app_path", lambda: "/tmp/app")
    monkeypatch.setattr(bootstrap_module, "resolve_log_path", lambda: "/tmp/log")
    monkeypatch.setattr(bootstrap_module, "get_system_lang", lambda: "en")
    monkeypatch.setattr(bootstrap_module, "get_version", lambda: "1.0.0")
    monkeypatch.setattr(bootstrap_module, "find_free_port", lambda: 8090)
    monkeypatch.setattr(
        bootstrap_module.AcquisitionContext,
        "collect",
        classmethod(
            lambda _cls: AcquisitionContext(
                os_type="Darwin",
                os_version="macOS-14",
                username="alice",
                host_ip="10.0.0.3",
                public_ip="198.51.100.22",
                dns_servers=["1.1.1.1"],
            )
        ),
    )
    os.environ.pop("FIT_MITM_PORT", None)


@pytest.mark.contract
@pytest.mark.parametrize(
    ("platform", "expected_signal", "expected_message"),
    [
        ("win", BootstrapSignal.UNSUPPORTED_OS, "Windows is not supported yet"),
        ("lin", BootstrapSignal.UNSUPPORTED_OS, "Linux is not supported yet"),
    ],
)
def test_dispatch_unsupported_platform_contract(
    platform: str,
    expected_signal: BootstrapSignal,
    expected_message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: platform)
    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)

    result = bootstrap._dispatch()

    assert isinstance(result, BootstrapResult)
    assert result.code == 1
    assert result.signal == expected_signal
    assert result.message == expected_message


@pytest.mark.contract
def test_dispatch_admin_denied_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(bootstrap_module, "is_bundled", lambda: True)
    monkeypatch.setattr(
        bootstrap_module,
        "MacBootstrap",
        lambda: type(
            "_B",
            (),
            {
                "install_certificate": lambda self: BootstrapResult(  # noqa: ARG005
                    code=0,
                    signal=BootstrapSignal.OK,
                    message=None,
                ),
                "ensure_permissions": lambda self: BootstrapResult(
                    code=0,
                    signal=BootstrapSignal.OK,
                    message=None,
                ),
            },
        )(),
    )
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_root_or_relaunch",
        lambda *_a, **_k: 1,
    )
    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)

    result = bootstrap._dispatch(
        argv=["bootstrap.py", "--debug"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert isinstance(result, BootstrapResult)
    assert result.code == 1
    assert result.signal == BootstrapSignal.ADMIN_DENIED
    assert result.message == "Elevation failed"
