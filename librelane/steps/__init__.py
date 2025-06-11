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
from .step import (
    StepError,
    DeferredStepError,
    StepException,
    StepNotFound,
    Step,
    OutputProcessor,
    DefaultOutputProcessor,
    MetricsUpdate,
    ViewsUpdate,
)
from .tclstep import TclStep
from . import checker as Checker

# You'll notice some TclStep subclasses are exposed separately-
# this is for documentation.
from . import yosys as Yosys
from .yosys import YosysStep

from .openroad_alerts import (
    OpenROADAlert,
    OpenROADOutputProcessor,
    SupportsOpenROADAlerts,
)

from . import openroad as OpenROAD
from .openroad import OpenROADStep

from . import odb as Odb
from .odb import OdbpyStep, ECOBuffer, ECODiode

from . import magic as Magic
from .magic import MagicStep

from . import netgen as Netgen
from .netgen import NetgenStep

from . import klayout as KLayout
from . import misc as Misc
from . import verilator as Verilator
