# Copyright 2025 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
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
