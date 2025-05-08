# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import re
import sys
import shutil
import inspect
import importlib
from typing import Callable, Optional

import pytest
from _pytest.fixtures import SubRequest


@pytest.fixture
def _step_enabled(request: SubRequest, test: str):
    step_rx = request.config.option.step_rx
    if re.search(step_rx, test) is None:
        pytest.skip()


@pytest.fixture
def pdk_root(request):
    import ciel
    from ciel.source import StaticWebDataSource
    from librelane.common import get_opdks_rev

    ciel_home = ciel.get_ciel_home(request.config.option.pdk_root)

    data_source = StaticWebDataSource(
        "https://fossi-foundation.github.io/ciel-releases"
    )

    version = ciel.fetch(
        ciel_home,
        "sky130",
        get_opdks_rev(),
        data_source=data_source,
    )

    return version.get_dir(ciel_home)


def try_call(fn: Callable, /, **kwargs):
    # Calls a function with only the functions it supports
    # as a hack, if one of the kwargs is exception and
    # fn does not have exception in its header, the exception
    # is raised
    sig = inspect.signature(fn)
    if (
        "exception" in kwargs
        and kwargs["exception"] is not None
        and "exception" not in sig.parameters
    ):
        raise kwargs["exception"] from None

    final_kwargs = {k: kwargs[k] for k in kwargs if k in sig.parameters}
    return fn(**final_kwargs)


def attribute_from_file(file: str, attribute: str):
    try:
        spec = importlib.util.spec_from_file_location(attribute, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, attribute):
            return getattr(module, attribute)
    except FileNotFoundError:
        pass


@pytest.mark.parametrize("test", pytest.tests)
@pytest.mark.usefixtures("_chdir_tmp", "_step_enabled")
def test_step_folder(test: str, pdk_root: str, caplog: pytest.LogCaptureFixture):
    from librelane.steps import Step
    from librelane.state import State
    from librelane.common import Toolbox, get_script_dir
    from librelane.steps.openroad_alerts import SupportsOpenROADAlerts

    sys.path.insert(0, os.getcwd())

    # ---

    # 0. Prepare Test Files and Handlers
    step, _ = test.split(os.path.sep, maxsplit=1)
    test_path = os.path.join(pytest.step_test_dir, test)
    shutil.copytree(test_path, ".", dirs_exist_ok=True)

    for file in os.listdir("."):
        if file.endswith(".ref"):
            referenced_file_path = open(file, encoding="utf8").read()
            final_path = os.path.join(".", file[:-4])
            referenced_file = os.path.join(pytest.step_common_dir, referenced_file_path)
            shutil.copy(referenced_file, final_path)

    process_input: Callable = attribute_from_file(
        os.path.join(os.getcwd(), "process_input.py"), "process_input"
    ) or (lambda state_in, config: (state_in, config))
    handler: Callable = attribute_from_file(
        os.path.join(os.getcwd(), "handler.py"), "handle"
    ) or (lambda: None)

    base_sdc = os.path.join(get_script_dir(), "base.sdc")
    shutil.copy(base_sdc, ".")

    # 1. Preprocess State and Config (if needed)
    state_in = os.path.join(".", "state_in.json")
    config = os.path.join(".", "config.json")

    Target = Step.factory.get(step)

    openroad_alerts = []
    if isinstance(Target, SupportsOpenROADAlerts):

        def on_alert(self, alert):
            nonlocal openroad_alerts
            openroad_alerts.append(alert)
            return alert

        Target.on_alert = on_alert

    state_in, config = try_call(
        process_input,
        state_in=state_in,
        config=config,
        step_cls=Target,
        pdk_root=pdk_root,
        test=test,
    )

    ## Create empty State if state_in.json is missing
    if state_in is None or (type(state_in) == str and not os.path.isfile(state_in)):
        state_in = State()

    # 2. Load and Launch Step
    target = Target.load(config, state_in, pdk_root)

    exception: Optional[Exception] = None
    try:
        target.start(
            toolbox=Toolbox("."),
            step_dir=".",
        )
    except Exception as e:
        exception = e

    # 3. Call handler
    try_call(
        handler,
        exception=exception,
        step=target,
        test=test,
        caplog=caplog,
        openroad_alerts=openroad_alerts,
    )
