#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2024 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import re
from typing import List
from enum import IntEnum

from sphinx.application import Sphinx


def setup(app):
    app.connect("source-read", subst_migration_comparison)
    return {"version": "1.0", "parallel_read_safe": True}


migration_comparison_rx = re.compile(
    r"^(`{3,})!migration_comparison(\[\w*\])?(?:\s+(.+))?"
)


def subst_migration_comparison(app: Sphinx, docname: str, sourceRef: List[str]):
    class State(IntEnum):
        default = 0
        before = 1
        after = 2
        rationale = 3

    source = sourceRef[0]

    final_string = ""
    state = State.default
    before = ""
    after = ""
    rationale = ""
    closing = ""
    lines_in = source.splitlines()
    highlighting = None
    if lines_in[0] != "!register migration_comparison":
        return
    for line in lines_in[1:]:
        if state == State.default:
            if match := migration_comparison_rx.match(line):
                final_string += (match[3] or "") + "\n"
                state = State.before
                before = ""
                after = ""
                rationale = ""
                highlighting = None
                closing = match[1]
                if match[2] is not None:
                    highlighting = match[2].strip("[]")
            else:
                final_string += line + "\n"
        elif state == State.before:
            if line == "---":
                state = State.after
                continue
            before += line + "\n"
        elif state == State.after:
            if line == "---":
                state = State.rationale
                continue
            after += line + "\n"
        elif state == State.rationale:
            if line == closing:
                state = State.default
                if highlighting is not None:
                    before = f"```{highlighting}\n{before}\n```\n"
                    after = f"```{highlighting}\n{after}\n```\n"
                final_string += f"""
<table style="width: 100%; table-layout:fixed;">
<tr>
<th style="width: 50%;"> OpenLane </th>
<th style="width: 50%;"> LibreLane </th>
</tr>
<tr>
<td style="width: 50%;">
<div style="overflow:scroll; width:100%;">

{before}

</div>
</td>
<td style="width: 50%;">
<div style="overflow:scroll; width:100%;">

{after}

</div>
</td>
</tr>
</table>

{rationale}
"""

                continue
            rationale += line + "\n"

    sourceRef[0] = final_string
