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
The LibreLane API
----------------

Documented elements of this API represent the primary programming interface for
the LibreLane infrastructure.

The various elements of LibreLane are organized into modules. You may import them
using their module name as follows:

.. code-block:: python

    import librelane.common

.. no-imported-members

.. comment
    .. data:: discovered_plugins

        A dictionary of detected LibreLane plugins, with the module name as a key and
        the module version as a version.
"""
from .plugins import discovered_plugins
from .__version__ import __version__
from .env_info import env_info_cli
