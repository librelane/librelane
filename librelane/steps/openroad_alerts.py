# Copyright 2024 Efabless Corporation
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
import re
from dataclasses import dataclass
from typing import Literal, Optional, Protocol, List, runtime_checkable

from .step import OutputProcessor


openroad_alert_rx = re.compile(r"^\[(WARNING|ERROR)(?:\s+([A-Z]+\-\d+))?\]\s*(.+)")


@dataclass
class OpenROADAlert:
    """
    Data structure encapsulating an alert (warning or error) from OpenROAD.
    """

    cls: Literal["warning", "error"]
    code: Optional[str]
    message: str

    def __str__(self) -> str:
        code_prefix = ""
        if self.code is not None:
            code_prefix = f"[{self.code}] "
        return f"{code_prefix}{self.message}"


@runtime_checkable
class SupportsOpenROADAlerts(Protocol):
    """
    A listener for ``OpenROADOutputProcessor``. Fires whenever a line contains
    an alert.
    """

    def on_alert(self, alert: OpenROADAlert) -> OpenROADAlert:
        """
        :param alert: The alert found in the processed line
        :returns: The alert once again, modified at the step object's leisure
        """
        ...


class OpenROADOutputProcessor(OutputProcessor):
    """
    A special output processor for steps leveraging OpenROAD-based subprocesses.

    It captures `[ERROR]` and `[WARNING]` lines into a data structure where they
    can be further processed by the step itself rather than simply printed to
    the terminal.
    """

    key = "openroad_alerts"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.alerts: List[OpenROADAlert] = []
        if not isinstance(self.step, SupportsOpenROADAlerts):
            raise ValueError(
                "OpenROADOutputProcessor is only compatible with steps implementing the SupportsOpenROADAlerts protocol"
            )

    def process_line(self, line: str):
        """
        If a line contains an OpenROAD error/warning, it is processed and handed
        over to the step's ``on_alert`` method.

        :param line: The line in question
        :returns: ``True`` if the line has alerts, ``False`` if the line has
            no alerts
        """
        if match := openroad_alert_rx.match(line):
            cls = match[1].lower()
            code = None
            if match[2] is not None:
                code = match[2]
            message = match[3]
            alert = OpenROADAlert(cls, code, message)  # type: ignore
            assert isinstance(self.step, SupportsOpenROADAlerts)
            alert = self.step.on_alert(alert)
            self.alerts.append(alert)

            return True  # munch
        return False  # pass on to next output processor

    def result(self) -> List[OpenROADAlert]:
        """
        :returns: A list of OpenROAD alerts captured by this output processor
        """
        return self.alerts
