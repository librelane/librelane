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
from typing import Dict, List, Tuple

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

        ┏━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃ SYNTH_STRATEGY ┃ Gates ┃ Area (µm²)    ┃ Worst R2R Setup Slack (ns) ┃ Worst Setup Slack (ns) ┃ Total -ve Setup Slack (ns) ┃
        ┡━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
        │ AREA 0         │ 6692  │ 88675.046400  │ 8.601737                   │ 8.066582297115897      │ 0.0                        │
        │ AREA 1         │ 6776  │ 88750.118400  │ 8.196377                   │ 7.965740292847976      │ 0.0                        │
        │ AREA 2         │ 6720  │ 88352.236800  │ 8.628829                   │ 8.628828562575336      │ 0.0                        │
        │ AREA 3         │ 11620 │ 110656.128000 │ 8.688749                   │ 8.688749521355085      │ 0.0                        │
        │ DELAY 0        │ 6797  │ 91976.963200  │ 8.135016                   │ 8.13501644628924       │ 0.0                        │
        │ DELAY 1        │ 6877  │ 92278.502400  │ 8.828732                   │ 8.828731773329311      │ 0.0                        │
        │ DELAY 2        │ 6891  │ 92394.864000  │ 8.775793                   │ 6.444352789363264      │ 0.0                        │
        │ DELAY 3        │ 6792  │ 91675.424000  │ 9.102930                   │ 8.078121511470991      │ 0.0                        │
        │ DELAY 4        │ 8533  │ 98833.539200  │ 8.665778                   │ 8.665778562236717      │ 0.0                        │
        └────────────────┴───────┴───────────────┴────────────────────────────┴────────────────────────┴────────────────────────────┘

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

        results: Dict[
            str, Tuple[Decimal, Decimal, Decimal, Decimal, Decimal] | None
        ] = {}
        for config, future in synth_futures:
            strategy = config["SYNTH_STRATEGY"]
            results[strategy] = None
            try:
                state = future.result()
                results[strategy] = (
                    state.metrics["design__instance__count"],
                    state.metrics["design__instance__area"],
                    state.metrics["timing__setup_r2r__ws"],
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
        max_r2r_slack = max(map(lambda x: x[2], successful_results.values()))
        max_slack = max(map(lambda x: x[3], successful_results.values()))
        max_tns = max(map(lambda x: x[4], successful_results.values()))

        table = rich.table.Table()
        table.add_column("SYNTH_STRATEGY")
        table.add_column("Gates")
        table.add_column("Area (µm²)")
        table.add_column("Worst R2R Setup Slack (ns)")
        table.add_column("Worst Setup Slack (ns)")
        table.add_column("Total -ve Setup Slack (ns)")
        for key, result in results.items():
            gates_s = "[red]Failed"
            area_s = "[red]Failed"
            r2r_slack_s = "[red]Failed"
            slack_s = "[red]Failed"
            tns_s = "[red]Failed"
            if result is not None:
                gates, area, r2r_slack, slack, tns = result
                gates_s = f"{'[green]' if gates == min_gates else ''}{gates}"
                area_s = f"{'[green]' if area == min_area else ''}{area}"
                r2r_slack_s = (
                    f"{'[green]' if r2r_slack == max_r2r_slack else ''}{r2r_slack}"
                )
                slack_s = f"{'[green]' if slack == max_slack else ''}{slack}"
                tns_s = f"{'[green]' if tns == max_tns else ''}{tns}"
            table.add_row(key, gates_s, area_s, r2r_slack_s, slack_s, tns_s)

        console.print(table)
        assert self.run_dir is not None
        file_console = rich.console.Console(
            file=open(os.path.join(self.run_dir, "summary.rpt"), "w", encoding="utf8"),
            width=160,
        )
        file_console.print(table)

        success("Flow complete.")
        return (initial_state, step_list)
