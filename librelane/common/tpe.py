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
from .misc import _get_process_limit

from concurrent.futures import ThreadPoolExecutor

TPE = ThreadPoolExecutor(max_workers=_get_process_limit())


def set_tpe(tpe: ThreadPoolExecutor):
    """
    Allows replacing LibreLane's global ``ThreadPoolExecutor`` with a customized
    one.

    It will be used inside steps, so use different TPEs inside steps to avoid
    a deadlock.

    :param tpe: The replacement ThreadPoolExecutor
    """
    global TPE
    TPE = tpe


def get_tpe() -> ThreadPoolExecutor:
    """
    :returns: LibreLane's global ``ThreadPoolExecutor``. This is used to run
        steps, so do not use them inside steps to avoid a deadlock.
    """
    global TPE
    return TPE
