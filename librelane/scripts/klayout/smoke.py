# Copyright 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
import sys

try:
    import importlib

    mod = importlib.import_module(globals().get("kmodule", "klayout.dbcore"))
    print(mod)
except Exception:
    try:
        import pya

        pya.Application.instance().exit(66)
    except AttributeError:
        sys.exit(66)
