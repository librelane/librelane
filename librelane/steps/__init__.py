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

"""
The Step Module
---------------

This modules includes various functions for importing and/or generating LibreLane
configuration objects. Configuration objects are the primary input to a flow.
"""

# You'll notice some TclStep subclasses are exposed separately-
# this is for documentation.

from . import checker as Checker
from . import gdsfill as GdsFill
from . import klayout as KLayout
from . import magic as Magic
from . import misc as Misc
from . import netgen as Netgen
from . import odb as Odb
from . import openroad as OpenROAD
from . import verilator as Verilator
from . import yosys as Yosys
from .magic import MagicStep
from .netgen import NetgenStep
from .odb import ECOBuffer, ECODiode, OdbpyStep
from .openroad import OpenROADStep
from .openroad_alerts import (
    OpenROADAlert,
    OpenROADOutputProcessor,
    SupportsOpenROADAlerts,
)
from .step import (
    DefaultOutputProcessor,
    DeferredStepError,
    MetricsUpdate,
    OutputProcessor,
    Step,
    StepError,
    StepException,
    StepNotFound,
    ViewsUpdate,
)
from .tclstep import TclStep
from .yosys import YosysStep

__all__ = [
    "Checker",
    "DefaultOutputProcessor",
    "DeferredStepError",
    "ECOBuffer",
    "ECODiode",
    "GdsFill",
    "KLayout",
    "Magic",
    "MagicStep",
    "MetricsUpdate",
    "Misc",
    "Netgen",
    "NetgenStep",
    "Odb",
    "OdbpyStep",
    "OpenROAD",
    "OpenROADAlert",
    "OpenROADOutputProcessor",
    "OpenROADStep",
    "OutputProcessor",
    "Step",
    "StepError",
    "StepException",
    "StepNotFound",
    "SupportsOpenROADAlerts",
    "TclStep",
    "Verilator",
    "ViewsUpdate",
    "Yosys",
    "YosysStep",
]
