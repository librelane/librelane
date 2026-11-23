# Copyright 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
from .classic import Classic
from .flow import Flow


@Flow.factory.register()
class Basic(Classic):
    Substitutions = {
        "Verilator.*": None,
        "Checker.Lint*": None,
        "Yosys.EQY": None,
        # Needs full KLayout
        "KLayout.DRC": None,
        "Checker.KLayoutDRC": None,
    }
