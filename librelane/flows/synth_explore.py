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
from __future__ import annotations
from decimal import Decimal
import os

import rich
import rich.table
from concurrent.futures import Future
from typing import Dict, List, Optional, Tuple

from .flow import Flow
from ..state import State
from ..config import Config
from ..logging import success
from ..logging import options, console
from ..steps import Step, Yosys, OpenROAD, StepError


# "Synthesis Exploration" is a non-seqeuential flow that tries all synthesis
# strategies and shows which ones yield the best area XOR delay
@Flow.factory.register()
class SynthesisExploration(Flow):
    """
    Synthesis Exploration is a feature that tries multiple synthesis strategies
    (in the form of different scripts for the ABC utility) to try and find which
    strategy is better by either minimizing area or maximizing slack (and thus
    frequency.)

    The output is represented in a tabulated format, e.g.: ::

      ┏━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
      ┃                ┃       ┃               ┃ Worst Setup      ┃ Total Negative   ┃
      ┃ SYNTH_STRATEGY ┃ Gates ┃ Area (µm²)    ┃ Slack (ns)       ┃ Setup Slack (ns) ┃
      ┡━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
      │ AREA 0         │ 8781  │ 97141.916800  │ 6.288794         │ 0.0              │
      │ AREA 1         │ 8692  │ 96447.500800  │ 6.434102         │ 0.0              │
      │ AREA 2         │ 8681  │ 96339.897600  │ 6.276806         │ 0.0              │
      │ AREA 3         │ 11793 │ 111084.038400 │ 7.011374         │ 0.0              │
      │ DELAY 0        │ 8969  │ 101418.518400 │ 6.511191         │ 0.0              │
      │ DELAY 1        │ 8997  │ 101275.881600 │ 6.656564         │ 0.0              │
      │ DELAY 2        │ 9013  │ 101177.036800 │ 6.691765         │ 0.0              │
      │ DELAY 3        │ 8733  │ 99190.131200  │ 6.414865         │ 0.0              │
      │ DELAY 4        │ 8739  │ 101011.878400 │ 6.274565         │ 0.0              │
      └────────────────┴───────┴───────────────┴──────────────────┴──────────────────┘

    You can then update your config file with the best ``SYNTH_STRATEGY`` for your
    use-case so it can be used with other flows.
    """

    Steps = [
        Yosys.Synthesis,
        OpenROAD.CheckSDCFiles,
        OpenROAD.STAPrePNR,
    ]

    def run(
        self,
        initial_state: State,
        **kwargs,
    ) -> Tuple[State, List[Step]]:
        step_list: List[Step] = []

        self.progress_bar.set_max_stage_count(1)

        synth_futures: List[Tuple[Config, Future[State]]] = []
        self.progress_bar.start_stage("Synthesis Exploration")

        options.set_condensed_mode(True)

        for strategy in [
            "AREA 0",
            "AREA 1",
            "AREA 2",
            "AREA 3",
            "DELAY 0",
            "DELAY 1",
            "DELAY 2",
            "DELAY 3",
            "DELAY 4",
        ]:
            config = self.config.copy(SYNTH_STRATEGY=strategy)

            synth_step = Yosys.Synthesis(
                config,
                id=f"synthesis-{strategy}",
                state_in=initial_state,
            )
            synth_future = self.start_step_async(synth_step)
            step_list.append(synth_step)

            sdc_step = OpenROAD.CheckSDCFiles(
                config,
                id=f"sdc-{strategy}",
                state_in=synth_future,
            )
            sdc_future = self.start_step_async(sdc_step)
            step_list.append(sdc_step)

            sta_step = OpenROAD.STAPrePNR(
                config,
                state_in=sdc_future,
                id=f"sta-{strategy}",
            )

            step_list.append(sta_step)
            sta_future = self.start_step_async(sta_step)

            synth_futures.append((config, sta_future))

        results: Dict[str, Optional[Tuple[Decimal, Decimal, Decimal, Decimal]]] = {}
        for config, future in synth_futures:
            strategy = config["SYNTH_STRATEGY"]
            results[strategy] = None
            try:
                state = future.result()
                results[strategy] = (
                    state.metrics["design__instance__count"],
                    state.metrics["design__instance__area"],
                    state.metrics["timing__setup__ws"],
                    state.metrics["timing__setup__tns"],
                )
            except StepError:
                pass  # None == failure
        self.progress_bar.end_stage()
        options.set_condensed_mode(False)

        successful_results = {k: v for k, v in results.items() if v is not None}
        min_gates = min(map(lambda x: x[0], successful_results.values()))
        min_area = min(map(lambda x: x[1], successful_results.values()))
        max_slack = max(map(lambda x: x[2], successful_results.values()))
        max_tns = max(map(lambda x: x[3], successful_results.values()))

        table = rich.table.Table()
        table.add_column("SYNTH_STRATEGY")
        table.add_column("Gates")
        table.add_column("Area (µm²)")
        table.add_column("Worst Setup Slack (ns)")
        table.add_column("Total -ve Setup Slack (ns)")
        for key, result in results.items():
            gates_s = "[red]Failed"
            area_s = "[red]Failed"
            slack_s = "[red]Failed"
            tns_s = "[red]Failed"
            if result is not None:
                gates, area, slack, tns = result
                gates_s = f"{'[green]' if gates == min_gates else ''}{gates}"
                area_s = f"{'[green]' if area == min_area else ''}{area}"
                slack_s = f"{'[green]' if slack == max_slack else ''}{slack}"
                tns_s = f"{'[green]' if tns == max_tns else ''}{tns}"
            table.add_row(key, gates_s, area_s, slack_s, tns_s)

        console.print(table)
        assert self.run_dir is not None
        file_console = rich.console.Console(
            file=open(os.path.join(self.run_dir, "summary.rpt"), "w", encoding="utf8"),
            width=160,
        )
        file_console.print(table)

        success("Flow complete.")
        return (initial_state, step_list)
