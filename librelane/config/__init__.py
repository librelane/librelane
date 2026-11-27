# Copyright 2025 LibreLane Contributors
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
The Configuration Module
------------------------

This modules includes various functions for importing and/or generating LibreLane
configuration objects. Configuration objects are the primary input to a flow.
"""

from .config import (
    AnyConfig,
    AnyConfigs,
    Config,
    InvalidConfig,
    Meta,
    PassedDirectoryError,
    UnknownExtensionError,
)
from .flow import flow_common_variables as universal_flow_config_variables
from .preprocessor import Keys
from .variable import Instance, Macro, Variable

__all__ = [
    "AnyConfig",
    "AnyConfigs",
    "Config",
    "Instance",
    "InvalidConfig",
    "Keys",
    "Macro",
    "Meta",
    "PassedDirectoryError",
    "UnknownExtensionError",
    "Variable",
    "universal_flow_config_variables",
]
