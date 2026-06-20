# Copyright 2024 Efabless Corporation
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
import logging
import pkgutil
import importlib

discovered_plugins = {}
for _finder, _name, _ispkg in pkgutil.iter_modules():
    if _name.startswith("librelane_plugin_") or _name.startswith("openlane_plugin_"):
        try:
            discovered_plugins[_name] = importlib.import_module(_name)
        except Exception as _e:
            logging.getLogger(__name__).warning(
                f"Failed to load plugin '{_name}': {_e}"
            )
