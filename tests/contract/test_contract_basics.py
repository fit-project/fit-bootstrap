from __future__ import annotations

import pytest

from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


@pytest.mark.contract
def test_caller_profile_values_are_stable() -> None:
    assert CallerProfile.FIT.value == "fit"
    assert CallerProfile.FIT_WEB.value == "fit_web"


@pytest.mark.contract
def test_bootstrap_result_default_message_is_none() -> None:
    result = BootstrapResult(code=0, signal=BootstrapSignal.OK)

    assert result.message is None
