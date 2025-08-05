# Copyright 2025 LibreLane Contributors
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
from ..common.cli import formatter_settings
from ..flows import Flow
from ..steps import Step
from ..logging import console

import cloup


@cloup.command(formatter_settings=formatter_settings)
@cloup.argument("step_or_flow")
@cloup.pass_context
def cli(ctx, step_or_flow):
    """
    Displays rich help for the step or flow in question.
    """
    if TargetFlow := Flow.factory.get(step_or_flow):
        TargetFlow.display_help()
    elif TargetStep := Step.factory.get(step_or_flow):
        TargetStep.display_help()
    else:
        console.log(f"Unknown Flow or Step '{step_or_flow}'.")
        ctx.exit(-1)


if __name__ == "__main__":
    cli()
