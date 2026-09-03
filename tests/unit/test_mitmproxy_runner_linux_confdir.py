from pathlib import Path

import pytest

from fit_bootstrap import mitmproxy_runner
from fit_bootstrap.constants import (
    FIT_DEBUG_ENABLED,
    FIT_MITM_CONF_DIR,
    FIT_USER_APP_PATH,
)


@pytest.mark.unit
def test_linux_runner_passes_explicit_fit_confdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    conf = tmp_path / "mitmproxy" / "conf"
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    monkeypatch.setenv(FIT_MITM_CONF_DIR, str(conf))
    monkeypatch.setenv(FIT_DEBUG_ENABLED, "0")
    monkeypatch.setattr(mitmproxy_runner.sys, "platform", "linux")
    monkeypatch.setattr(mitmproxy_runner.time, "sleep", lambda _seconds: None)
    captured = {}
    class Process:
        pid = 123
        def poll(self): return None
    def popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Process()
    monkeypatch.setattr(mitmproxy_runner.subprocess, "Popen", popen)

    process = mitmproxy_runner.MitmproxyRunner().start()

    assert process is not None
    command = captured["command"]
    index = command.index("confdir=" + str(conf.resolve()))
    assert command[index - 1] == "--set"
    assert "shell" not in captured["kwargs"]
