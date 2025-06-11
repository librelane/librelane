#!/usr/bin/env python3
# Copyright 2021 Efabless Corporation
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

import os
import json

import yaml
import click

import ciel

__dir__ = os.path.dirname(os.path.abspath(__file__))
ol_dir = os.path.dirname(os.path.dirname(__dir__))

TEST_SETS_FILE = os.path.join(__dir__, "test_sets.yml")


@click.command()
@click.option(
    "--scl",
    "scls",
    multiple=True,
    default=["sky130A/sky130_fd_sc_hd"],
    help="Specify which PDK/SCL combination to use",
)
@click.option(
    "--json/--plain",
    "use_json",
    default=True,
    help="Print as plain text joined by whitespace instead of a JSON file. Omits PDKs.",
)
@click.argument("test_sets", nargs=-1)
def main(scls, use_json, test_sets):
    data_str = open(TEST_SETS_FILE).read()
    data = yaml.safe_load(data_str)
    test_set_data = filter(lambda e: e["scl"] in scls and e["name"] in test_sets, data)

    designs = list()
    empty_runner_script = "None"
    for test_set in list(test_set_data):
        pdk, scl = test_set["scl"].split("/")
        for design in test_set["designs"]:
            design_name = design
            test_name = design_name
            script = empty_runner_script
            config_filename = "config.json"
            ipm_version = "None"
            if not isinstance(design, str):
                design_name = design["name"]
                test_name = design.get("test_name", design_name)
                config_filename = design.get("config_file", config_filename)
                ipm_version = design.get("ipm", "None")
                script_filename = design.get("script")
                if script_filename:
                    script = os.path.join(
                        ol_dir, "test", "designs", design_name, script_filename
                    )
            config_file = os.path.join(
                ol_dir, "test", "designs", design_name, config_filename
            )
            run_dir = os.path.join(
                ol_dir, "test", "designs", design_name, "runs", f"{pdk}-{scl}"
            )
            pdk_family = None
            if family := ciel.Family.by_name.get(pdk):
                pdk_family = family.name
            else:
                for family in ciel.Family.by_name.values():
                    if pdk in family.variants:
                        pdk_family = family.name
                        break
            if pdk_family is None:
                raise Exception(
                    f"Failed to determine pdk_family of {design_name} {pdk}/{scl}"
                )
            designs.append(
                {
                    "name": design_name,
                    "config": config_file,
                    "run_dir": run_dir,
                    "pdk": pdk,
                    "scl": scl,
                    "script": script,
                    "ipm_version": ipm_version,
                    "pdk_family": pdk_family,
                    "test_name": test_name,
                }
            )

    if use_json:
        print(json.dumps({"design": designs}), end="")
    else:
        print(" ".join([design["name"] for design in designs]), end="")


if __name__ == "__main__":
    main()
