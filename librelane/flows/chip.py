# Copyright 2025 LibreLane Contributors
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
from .flow import Flow
from .classic import Classic
from ..steps import (
    OpenROAD,
    KLayout,
    Checker,
)


@Flow.factory.register()
class Chip(Classic):
    """
    A flow of type :class:`librelane.flows.SequentialFlow` that is used
    to implement complete chip designs. This includes pad ring generation,
    seal ring generation, filler insertion, and density check.
    """

    Substitutions = {
        # Generate the pad ring right after
        # setting the the power connections
        "+Odb.SetPowerConnections": OpenROAD.PadRing,
        # No pin placement necessary
        # -> pads are the BTerms
        "OpenROAD.IOPlacement": None,
        "Odb.CustomIOPlacement": None,
        # This is not a macro, there's no need to
        # write a LEF and check antenna properties
        "Magic.WriteLEF": None,
        "Odb.CheckDesignAntennaProperties": None,
        # Add finishing steps
        "+Checker.XOR": KLayout.Antenna,
        "+KLayout.Antenna": Checker.KLayoutAntenna,
        "+Checker.KLayoutAntenna": KLayout.SealRing,
        "+KLayout.SealRing": KLayout.Filler,
        "+KLayout.Filler": KLayout.Density,
        "+KLayout.Density": Checker.KLayoutDensity,
    }
