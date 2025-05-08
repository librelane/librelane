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
import sys
import json
from typing import Optional

import cloup

from ..common import get_latest_file
from ..common.cli import formatter_settings


@cloup.group(
    no_args_is_help=True,
    formatter_settings=formatter_settings,
)
def cli():
    pass


@cloup.command()
@cloup.option(
    "--extract-metrics-to",
    default=None,
)
@cloup.argument("run_dir")
def latest(extract_metrics_to: Optional[str], run_dir: str):
    exit_code = 0

    if latest_state := get_latest_file(run_dir, "state_*.json"):
        try:
            state = json.load(open(latest_state, encoding="utf8"))
        except json.JSONDecodeError as e:
            print(f"Latest state at {latest_state} is invalid: {e}", file=sys.stderr)
            exit(1)
        metrics = state["metrics"]
        print(latest_state, end="")
        if output := extract_metrics_to:
            json.dump(metrics, open(output, "w", encoding="utf8"))
    else:
        print("No state_*.json files found", file=sys.stderr)
        exit_code = 1

    exit(exit_code)


cli.add_command(latest)

if __name__ == "__main__":
    cli()
