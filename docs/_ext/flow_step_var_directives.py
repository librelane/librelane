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
from docutils import nodes
from sphinx.application import Sphinx
from docutils.parsers.rst.states import Struct
import re

from librelane.common import slugify
from librelane.flows import Flow
from librelane.steps import Step
from librelane.config import universal_flow_config_variables

custom_text_rx = re.compile(r"([\s\S]+)\s+\<([A-Za-z_\-\.:]+)\>")


def librelane_object_reference_role(
    role: str, rawtext: str, text: str, lineno: int, inliner, options=None, content=None
):
    # Get target flow, ensure it exists
    text_clean = nodes.unescape(text)
    link_text, target = f"`{text_clean}`", text_clean
    if match := custom_text_rx.match(text_clean):
        link_text = match[1]
        target = match[2]

    factory = Flow.factory
    if role == "step":
        factory = Step.factory
    Target = factory.get(target)
    if Target is None:
        msg = inliner.reporter.warning(
            f"Referenced {role} '{target}' not found.",
            line=lineno,
        )
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    # Prepare context for nested parsing
    memo = Struct(
        document=inliner.document,
        reporter=inliner.reporter,
        language=inliner.language,
    )

    # Create parent node
    parent = nodes.inline(rawtext, "")

    # Parse role text for markup and add to parent
    processed, messages = inliner.parse(
        f"[{link_text}](#{role}-{slugify(target, lower=True)})", lineno, memo, parent
    )
    parent += processed

    # Return parent node, and any messages from nested parsing
    return [parent], messages


def librelane_var_reference_role(
    role: str, rawtext: str, text: str, lineno: int, inliner, options=None, content=None
):
    # Get target flow, ensure it exists
    text_clean = nodes.unescape(text)
    split = text_clean.split("::", maxsplit=1)
    if len(split) != 2:
        msg = inliner.reporter.warning(
            f"Invalid variable reference '{text_clean}'. If you want to reference a universal flow variable, try '::{text_clean}'.",
            line=lineno,
        )
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    parent, variable = split

    Parent = Flow.factory.get(parent) or Step.factory.get(parent)
    config_var_list = universal_flow_config_variables
    if parent == "":
        parent = None
    elif Parent is not None:
        config_var_list = Parent.config_vars
    else:
        msg = inliner.reporter.warning(
            f"Referenced flow/step '{parent}' not found.",
            line=lineno,
        )
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    found = None
    for config_var in config_var_list:
        if config_var.name == variable:
            found = config_var
            break

    if found is None:
        msg = inliner.reporter.warning(
            f"Referenced var '{text_clean}' not found.",
            line=lineno,
        )
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    identifier = found._get_docs_identifier(parent)

    # Prepare context for nested parsing
    memo = Struct(
        document=inliner.document,
        reporter=inliner.reporter,
        language=inliner.language,
    )

    # Create parent node
    parent = nodes.inline(rawtext, "")

    # Parse role text for markup and add to parent
    processed, messages = inliner.parse(
        f"[`{variable}`]({identifier})", lineno, memo, parent
    )
    parent += processed

    # Return parent node, and any messages from nested parsing
    return [parent], messages


def setup(app: Sphinx):
    app.add_role("flow", librelane_object_reference_role)
    app.add_role("step", librelane_object_reference_role)
    app.add_role("var", librelane_var_reference_role)
