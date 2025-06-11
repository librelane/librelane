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
The Logging Module
------------------

As the name implies, this handles LibreLane's logging using the ``logging``
module and the ``rich`` library.
"""

from .logger import (
    LogLevels,
    LevelFilter,
    options,
    console,
    set_log_level,
    reset_log_level,
    get_log_level,
    register_additional_handler,
    deregister_additional_handler,
    verbose,
    debug,
    info,
    rule,
    success,
    warn,
    err,
    subprocess,
)
