#!/usr/bin/env python3
# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Adapted from OpenLane 2
#
# Copyright 2020-2021 Efabless Corporation
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
import argparse
import json
import os

def export_env(key: str, value: str):
    env_file = os.getenv("GITHUB_ENV", ".test_sets.env")
    with open(env_file, "w", encoding="utf8") as f:
        f.write(f"{key}={value}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("github_event_name")
    ns = ap.parse_args()
    export_env("TEST_SETS", "fastest_test_set")
    if ns.github_event_name in ["schedule", "workflow_dispatch"]:
        export_env("TEST_SETS", "fastest_test_set extended_test_set")
    elif ns.github_event_name == "pull_request" and "GITHUB_EVENT_PATH" in os.environ:
        with open(os.environ["GITHUB_EVENT_PATH"]) as f:
            gh_event = json.load(f)
        pr_body = gh_event["pull_request"]["body"] or ""

        if "[ci ets]" in pr_body:
            export_env("TEST_SETS", "fastest_test_set extended_test_set")
