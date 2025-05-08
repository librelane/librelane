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

import os
import traceback

import jinja2
from sphinx.config import Config
from sphinx.application import Sphinx

import librelane
import librelane.flows
import librelane.steps
import librelane.config
from librelane.common import slugify


def setup(app: Sphinx):
    app.connect("config-inited", generate_module_docs)
    return {"version": "1.0"}


def generate_module_docs(app: Sphinx, conf: Config):
    try:
        conf_py_path: str = conf._raw_config["__file__"]
        doc_root_dir: str = os.path.dirname(conf_py_path)

        template_relpath: str = conf.templates_path[0]
        all_templates_path = os.path.abspath(template_relpath)
        template_path = os.path.join(all_templates_path, "generate_configvar_docs")

        lookup = jinja2.FileSystemLoader(searchpath=template_path)

        # Mako-like environment
        env = jinja2.Environment(
            "<%",
            "%>",
            "${",
            "}",
            "<%doc>",
            "</%doc>",
            "%",
            "##",
            loader=lookup,
        )

        module = librelane.config.flow

        # 1. Flows
        template = env.get_template("flows.md")
        flow_factory = librelane.flows.Flow.factory

        with open(os.path.join(doc_root_dir, "reference", "flows.md"), "w") as f:
            f.write(
                template.render(
                    slugify=slugify,
                    flows=[
                        flow_factory.get(key)
                        for key in flow_factory.list()
                        if flow_factory.get(key).__doc__ is not None
                    ],
                )
            )

        # 2. Common PDK Vars
        template = env.get_template("common_pdk_vars.md")
        with open(
            os.path.join(doc_root_dir, "reference", "common_pdk_vars.md"), "w"
        ) as f:
            f.write(
                template.render(
                    slugify=slugify,
                    pdk_variables=module.pdk_variables,
                    scl_variables=module.scl_variables,
                )
            )

        # 3. Common Flow Vars
        template = env.get_template("common_vars.md")
        with open(
            os.path.join(doc_root_dir, "reference", "common_flow_vars.md"), "w"
        ) as f:
            f.write(
                template.render(
                    slugify=slugify,
                    option_variables=module.option_variables,
                )
            )

        # 4. Steps
        template = env.get_template("steps.md")
        step_factory = librelane.steps.Step.factory

        # Pre-processing
        by_category = {}
        for step in step_factory.list():
            category, _ = step.split(".")
            if by_category.get(category) is None:
                by_category[category] = []
            by_category[category].append((step, step_factory.get(step)))

        misc = ("Misc", by_category["Misc"])
        del by_category["Misc"]

        ## Sort Categories
        categories_sorted = list(sorted(by_category.items(), key=lambda c: c[0])) + [
            misc
        ]

        ## Sort Steps
        for i in range(0, len(categories_sorted)):
            category, step_list = categories_sorted[i]
            steps_sorted = list(sorted(step_list, key=lambda s: s[0]))
            categories_sorted[i] = (category, steps_sorted)

        # --

        with open(
            os.path.join(doc_root_dir, "reference", "step_config_vars.md"), "w"
        ) as f:
            f.write(
                template.render(
                    slugify=slugify,
                    factory=step_factory,
                    categories_sorted=categories_sorted,
                )
            )

    except Exception:
        print(traceback.format_exc())
        exit(-1)
