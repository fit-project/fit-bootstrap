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
    monkeypatch.setattr(bootstrap_module, "get_system_lang", lambda: "it")
    monkeypatch.setattr(bootstrap_module, "get_version", lambda: "1.0.0")
    monkeypatch.setattr(bootstrap_module, "find_free_port", lambda: 9080)
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_connectivity_available",
        lambda: None,
    )
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
                dns_servers=["1.1.1.1", "8.8.8.8"],
            )
        ),
    )


@pytest.mark.unit
def test_bootstrap_init_sets_expected_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.delenv("FIT_MITM_PORT", raising=False)

    bootstrap_module.Bootstrap(debug_enabled=True, caller=CallerProfile.FIT)

    assert os.environ["FIT_DEBUG_ENABLED"] == "1"
    assert os.environ["FIT_USER_APP_PATH"] == "/tmp/app"
    assert os.environ["FIT_LOG_APP_PATH"] == "/tmp/log"
    assert os.environ["FIT_OS_TYPE"] == "Darwin"
    assert os.environ["FIT_OS_VERSION"] == "macOS-14"
    assert os.environ["FIT_USERNAME"] == "alice"
    assert os.environ["FIT_HOST_IP"] == "10.0.0.3"
    assert os.environ["FIT_PUBLIC_IP"] == "198.51.100.22"
    assert os.environ["FIT_DNS"] == "1.1.1.1,8.8.8.8"
    assert os.environ["FIT_USER_SYSTEM_LANG"] == "it"
    assert os.environ["FIT_EXECUTION_ENV"] == "LOCAL_PC"
    assert os.environ["FIT_VERSION"] == "1.0.0"
    assert os.environ["FIT_MITM_PORT"] == "9080"


@pytest.mark.unit
def test_apply_caller_profile_falls_back_to_default_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(
        bootstrap_module,
        "find_free_port",
        lambda: (_ for _ in ()).throw(RuntimeError("no free port")),
    )
    monkeypatch.delenv("FIT_MITM_PORT", raising=False)

    bootstrap_module.Bootstrap(caller=CallerProfile.FIT_WEB)

    assert os.environ["FIT_MITM_PORT"] == "8080"


@pytest.mark.unit
def test_dispatch_macos_requires_bootstrap_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: "macos")
    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)

    result = bootstrap._dispatch()

    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == "Parametri di bootstrap mancanti"


@pytest.mark.unit
def test_dispatch_returns_certificate_failure_when_install_fails(
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

    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)
    result = bootstrap._dispatch(argv=["main.py"], stage_env="S", stage_gui="G")

    assert result.signal == BootstrapSignal.ERROR
    assert result.code == 1


@pytest.mark.unit
def test_dispatch_macos_relaunches_and_resolves_script_path(
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
    monkeypatch.setattr(bootstrap_module, "is_bundled", lambda: False)
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

    result = bootstrap._dispatch(
        argv=["main.py", "--debug"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result.signal == BootstrapSignal.OK
    relaunch_argv = captured["argv"]  # type: ignore[assignment]
    assert relaunch_argv[1:] == ["--debug"]  # type: ignore[index]
    assert Path(relaunch_argv[0]).is_absolute()  # type: ignore[index]
    env = captured["env"]  # type: ignore[assignment]
    assert env["FIT_BOOTSTRAP_STAGE"] == "gui"  # type: ignore[index]
    assert env["FIT_MITM_PORT"] == "9080"  # type: ignore[index]


@pytest.mark.unit
def test_dispatch_returns_admin_denied_on_failed_relaunch(
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
    monkeypatch.setattr(bootstrap_module, "is_bundled", lambda: True)
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
    monkeypatch.setattr(
        bootstrap_module, "ensure_root_or_relaunch", lambda *_a, **_k: 1
    )

    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)
    result = bootstrap._dispatch(
        argv=["bootstrap.py", "--x"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == (
        "Accesso ai privilegi di root negato.<br><br>"
        "<strong style=\"color:red\">FIT non può essere eseguita senza privilegi root.</strong>"
    )


@pytest.mark.unit
def test_dispatch_returns_unsupported_for_non_macos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    bootstrap = bootstrap_module.Bootstrap(caller=CallerProfile.FIT)
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

    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: "win")
    result = bootstrap._dispatch(
        argv=["main.py"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == (
        "Sistema operativo non supportato. <br><br>"
        "<strong style=\"color:red\">FIT è compatibile solo con macOS, Windows e Linux.</strong>"
    )

    monkeypatch.setattr(bootstrap_module, "get_platform", lambda: "lin")
    result = bootstrap._dispatch(
        argv=["main.py"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == (
        "Sistema operativo non supportato. <br><br>"
        "<strong style=\"color:red\">FIT è compatibile solo con macOS, Windows e Linux.</strong>"
    )


@pytest.mark.unit
def test_run_common_checks_returns_error_when_screen_recoder_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_supported_os_configuration",
        lambda _context: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_connectivity_available",
        lambda: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_screen_recoder_available",
        lambda: BootstrapResult(
            code=1,
            signal=BootstrapSignal.ERROR,
            message="screen recorder missing",
        ),
    )

    result = bootstrap_module.Bootstrap()._run_common_checks(
        argv=["main.py"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result is not None
    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR


@pytest.mark.unit
def test_run_common_checks_returns_error_when_os_requirements_not_met(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_supported_os_configuration",
        lambda _context: BootstrapResult(
            code=1,
            signal=BootstrapSignal.ERROR,
            message="FIT requires macOS 15 or later on arm64.",
        ),
    )

    result = bootstrap_module.Bootstrap()._run_common_checks(
        argv=["main.py"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result is not None
    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR


@pytest.mark.unit
def test_run_common_checks_returns_error_when_connectivity_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_init_dependencies(monkeypatch)
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_supported_os_configuration",
        lambda _context: None,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "ensure_connectivity_available",
        lambda: BootstrapResult(
            code=1,
            signal=BootstrapSignal.ERROR,
            message="no internet",
        ),
    )

    result = bootstrap_module.Bootstrap()._run_common_checks(
        argv=["main.py"],
        stage_env="FIT_BOOTSTRAP_STAGE",
        stage_gui="gui",
    )

    assert result is not None
    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == "no internet"
