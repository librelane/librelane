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
The State Module
----------------

This module manages the State of a Design before and after the execution of an
LibreLane step. The State is essentially a list of views in various formats in
addition to the cumulative set of metrics created by previous Steps.
"""
from .design_format import DesignFormat, DesignFormatObject
from .state import State, InvalidState, StateElement
