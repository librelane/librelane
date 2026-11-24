# Copyright 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
"""
Common Serialize Submodule

Provides functions for loading and saving in the JSON and YAML formats, with
some special handling for LibreLane objects.

The functions are in the form ``{format}_{load,dump}{,s,p}``, where:
- No suffix parses/writes to a stream.
- The ``s`` suffix parses/returns a *s*tring.
- The ``p`` suffix parses/writes to a file *p*ath.

The YAML objects are internal and inputs/output may change for any reason on
any LibreLane minor or patch version. Please do not use them for now.
"""

from .json import (
    JSONError,
    json_dump,
    json_dumpp,
    json_dumps,
    json_load,
    json_loadp,
    json_loads,
)
from .yaml import (
    _YAMLError,
    _yaml_dump,
    _yaml_dumpp,
    _yaml_dumps,
    _yaml_load,
    _yaml_loadp,
    _yaml_loads,
)

__all__ = [
    "JSONError",
    "_YAMLError",
    "_yaml_dump",
    "_yaml_dumpp",
    "_yaml_dumps",
    "_yaml_load",
    "_yaml_loadp",
    "_yaml_loads",
    "json_dump",
    "json_dumpp",
    "json_dumps",
    "json_load",
    "json_loadp",
    "json_loads",
]
