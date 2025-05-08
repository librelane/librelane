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
import os

from .tcl import TclUtils
from .metrics import parse_metric_modifiers, aggregate_metrics
from . import metrics
from .generic_dict import (
    GenericDictEncoder,
    GenericDict,
    GenericImmutableDict,
    copy_recursive,
)
from .misc import (
    idem,
    get_librelane_root,
    get_script_dir,
    get_opdks_rev,
    slugify,
    protected,
    final,
    mkdirp,
    zip_first,
    format_size,
    format_elapsed_time,
    Filter,
    get_latest_file,
    process_list_file,
    _get_process_limit,
)
from .types import (
    is_number,
    is_real_number,
    is_string,
    Number,
    Path,
    AnyPath,
    ScopedFile,
)
from .toolbox import Toolbox
from .drc import DRC, Violation
from . import cli
from .tpe import get_tpe, set_tpe
from .ring_buffer import RingBuffer
