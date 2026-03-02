from __future__ import annotations

import os
from pathlib import Path

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
    monkeypatch.setattr(bootstrap_module, "find_free_port", lambda: 8091)
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


@pytest.mark.integration
def test_dispatch_macos_success_calls_signal_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(bootstrap_module, "is_bundled", lambda: False)
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_supported_os_configuration",
        lambda _context: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_screen_recoder_available",
        lambda: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "MacBootstrap",
        lambda: type(
            "_B",
            (),
            {
                "install_certificate": lambda self: BootstrapResult(
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

    captured: dict[str, object] = {}

    def _fake_relaunch(argv, env_overrides):
        captured["argv"] = argv
        captured["env"] = env_overrides
        return 0

    monkeypatch.setattr(bootstrap_module, "ensure_root_or_relaunch", _fake_relaunch)
    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)
    received: list[BootstrapResult] = []

    result = bootstrap._dispatch(
        on_signal=received.append,
        argv=["main.py", "--debug"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result.code == 0
    assert result.signal == BootstrapSignal.OK
    assert len(received) == 1
    assert received[0] == result
    relaunch_argv = captured["argv"]  # type: ignore[assignment]
    assert relaunch_argv[1:] == ["--debug"]  # type: ignore[index]
    assert Path(relaunch_argv[0]).is_absolute()  # type: ignore[index]
    env = captured["env"]  # type: ignore[assignment]
    assert env["FIT_BOOTSTRAP_STAGE"] == "gui"  # type: ignore[index]
    assert env["FIT_MITM_PORT"] == "8091"  # type: ignore[index]


@pytest.mark.integration
def test_dispatch_macos_certificate_failure_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_supported_os_configuration",
        lambda _context: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_screen_recoder_available",
        lambda: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "MacBootstrap",
        lambda: type(
            "_B",
            (),
            {
                "install_certificate": lambda self: BootstrapResult(
                    code=1,
                    signal=BootstrapSignal.ERROR,
                    message="cert failed",
                ),
                "ensure_permissions": lambda self: BootstrapResult(
                    code=0,
                    signal=BootstrapSignal.OK,
                    message=None,
                ),
            },
        )(),
    )

    called: list[bool] = []
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_root_or_relaunch",
        lambda *_a, **_k: called.append(True) or 0,
    )
    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT_WEB)

    result = bootstrap._dispatch(
        argv=["main.py"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result.signal == BootstrapSignal.ERROR
    assert called == []
