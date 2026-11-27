# Copyright 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Adapted from OpenLane 2
#
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
Common Utilities Module
-----------------------

A number of common utility functions and classes used throughout the codebase.
"""

from .types import (
    AnyPath,
    Number,
    Path,
    ScopedFile,
    is_number,
    is_real_number,
    is_string,
)
from . import cli, metrics, serialize
from .drc import DRC, BoundingBox, Violation
from .generic_dict import (
    GenericDict,
    GenericDictEncoder,
    GenericImmutableDict,
    copy_recursive,
)
from .metrics import aggregate_metrics, parse_metric_modifiers
from .misc import (
    Filter,
    _get_process_limit,
    count_occurences,
    final,
    format_elapsed_time,
    format_size,
    get_ciel_pdk_hash,
    get_latest_file,
    get_librelane_root,
    get_pdk_hash,
    get_script_dir,
    idem,
    mkdirp,
    process_list_file,
    protected,
    recreate_tree,
    slugify,
    zip_first,
)
from .ring_buffer import RingBuffer
from .tcl import TclUtils
from .toolbox import Toolbox
from .tpe import get_tpe, set_tpe

__all__ = [
    "DRC",
    "AnyPath",
    "BoundingBox",
    "Filter",
    "GenericDict",
    "GenericDictEncoder",
    "GenericImmutableDict",
    "Number",
    "Path",
    "RingBuffer",
    "ScopedFile",
    "TclUtils",
    "Toolbox",
    "Violation",
    "_get_process_limit",
    "aggregate_metrics",
    "cli",
    "copy_recursive",
    "count_occurences",
    "final",
    "format_elapsed_time",
    "format_size",
    "get_ciel_pdk_hash",
    "get_latest_file",
    "get_librelane_root",
    "get_pdk_hash",
    "get_script_dir",
    "get_tpe",
    "idem",
    "is_number",
    "is_real_number",
    "is_string",
    "metrics",
    "mkdirp",
    "parse_metric_modifiers",
    "process_list_file",
    "protected",
    "recreate_tree",
    "serialize",
    "set_tpe",
    "slugify",
    "zip_first",
]
