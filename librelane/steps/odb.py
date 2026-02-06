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
import os
import re
import json
import shutil
from math import inf
from decimal import Decimal
from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from ..common import Path, get_script_dir, aggregate_metrics
from ..config import Instance, Macro, Variable
from ..logging import info, verbose
from ..state import DesignFormat, State

from .openroad import DetailedPlacement, GlobalRouting
from .openroad_alerts import OpenROADAlert, OpenROADOutputProcessor
from .common_variables import io_layer_variables, dpl_variables, grt_variables
from .step import (
    CompositeStep,
    DefaultOutputProcessor,
    MetricsUpdate,
    Step,
    StepError,
    StepException,
    ViewsUpdate,
)
from .tclstep import TclStep

inf_rx = re.compile(r"\b(-?)inf\b")


class OdbpyStep(Step):
    inputs = [DesignFormat.ODB]
    outputs = [DesignFormat.ODB, DesignFormat.DEF]

    output_processors = [OpenROADOutputProcessor, DefaultOutputProcessor]

    alerts: Optional[List[OpenROADAlert]] = None

    def on_alert(self, alert: OpenROADAlert) -> OpenROADAlert:
        if alert.code in [
            "ORD-0039",  # .openroad ignored with -python
            "ODB-0220",  # LEF thing obsolete
        ]:
            return alert
        if alert.cls == "error":
            self.err(str(alert), extra={"key": alert.code})
        elif alert.cls == "warning":
            self.warn(str(alert), extra={"key": alert.code})
        return alert

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        self.alerts = None

        kwargs, env = self.extract_env(kwargs)

        automatic_outputs = set(self.outputs).intersection(
            [DesignFormat.ODB, DesignFormat.DEF]
        )

        views_updates: ViewsUpdate = {}
        command = self.get_command()
        for output in automatic_outputs:
            filename = f"{self.config['DESIGN_NAME']}.{output.value.extension}"
            file_path = os.path.join(self.step_dir, filename)
            command.append(f"--output-{output.value.id}")
            command.append(file_path)
            views_updates[output] = Path(file_path)

        command += [
            str(state_in[DesignFormat.ODB]),
        ]

        env["PYTHONPATH"] = (
            f'{os.path.join(get_script_dir(), "odbpy")}:{env.get("PYTHONPATH")}'
        )
        check = False
        if "check" in kwargs:
            check = kwargs.pop("check")

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )
        generated_metrics = subprocess_result["generated_metrics"]

        # 1. Parse warnings and errors
        self.alerts = subprocess_result.get("openroad_alerts") or []
        if subprocess_result["returncode"] != 0:
            error_strings = [
                str(alert) for alert in self.alerts if alert.cls == "error"
            ]
            if len(error_strings):
                error_string = "\n".join(error_strings)
                raise StepError(
                    f"{self.id} failed with the following errors:\n{error_string}"
                )
            else:
                raise StepException(
                    f"{self.id} failed unexpectedly. Please check the logs and file an issue."
                )
        # 2. Metrics
        metrics_path = os.path.join(self.step_dir, "or_metrics_out.json")
        if os.path.exists(metrics_path):
            or_metrics_out = json.loads(open(metrics_path).read(), parse_float=Decimal)
            for key, value in or_metrics_out.items():
                if value == "Infinity":
                    or_metrics_out[key] = inf
                elif value == "-Infinity":
                    or_metrics_out[key] = -inf
            generated_metrics.update(or_metrics_out)

        metric_updates_with_aggregates = aggregate_metrics(generated_metrics)

        return views_updates, metric_updates_with_aggregates

    def get_command(self) -> List[str]:
        metrics_path = os.path.join(self.step_dir, "or_metrics_out.json")

        tech_lefs = self.toolbox.filter_views(self.config, self.config["TECH_LEFS"])
        if len(tech_lefs) != 1:
            raise StepException(
                "Misconfigured SCL: 'TECH_LEFS' must return exactly one Tech LEF for its default timing corner."
            )

        lefs = ["--input-lef", str(tech_lefs[0])]
        for lef in self.config["CELL_LEFS"]:
            lefs.append("--input-lef")
            lefs.append(lef)
        if extra_lefs := self.config["EXTRA_LEFS"]:
            for lef in extra_lefs:
                lefs.append("--input-lef")
                lefs.append(lef)
        if (design_lef := self.state_in.result()[DesignFormat.LEF]) and (
            DesignFormat.LEF in self.inputs
        ):
            lefs.append("--design-lef")
            lefs.append(str(design_lef))
        return (
            [
                "openroad",
                "-exit",
                "-no_splash",
                "-metrics",
                str(metrics_path),
                "-python",
                self.get_script_path(),
            ]
            + self.get_subcommand()
            + lefs
        )

    @abstractmethod
    def get_script_path(self) -> str:
        pass

    def get_subcommand(self) -> List[str]:
        return []


@Step.factory.register()
class CheckMacroAntennaProperties(OdbpyStep):
    """
    Prints warnings if the LEF views of macros are missing antenna information.
    """

    id = "Odb.CheckMacroAntennaProperties"
    name = "Check Antenna Properties of Macros Pins in Their LEF Views"
    inputs = OdbpyStep.inputs
    outputs = []

    def get_script_path(self):
        return os.path.join(
            get_script_dir(),
            "odbpy",
            "check_antenna_properties.py",
        )

    def get_cells(self) -> List[str]:
        macros = self.config["MACROS"]
        cells = []
        if macros:
            cells = list(macros.keys())
        return cells

    def get_report_path(self) -> str:
        return os.path.join(self.step_dir, "report.yaml")

    def get_command(self) -> List[str]:
        args = ["--report-file", self.get_report_path()]
        for name in self.get_cells():
            args += ["--cell-name", name]
        return super().get_command() + args

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if not self.get_cells():
            info("No cells provided, skipping…")
            return {}, {}
        return super().run(state_in, **kwargs)


@Step.factory.register()
class CheckDesignAntennaProperties(CheckMacroAntennaProperties):
    """
    Prints warnings if the LEF view of the design is missing antenna information.
    """

    id = "Odb.CheckDesignAntennaProperties"
    name = "Check Antenna Properties of Pins in The Generated Design LEF view"
    inputs = CheckMacroAntennaProperties.inputs + [DesignFormat.LEF]

    def get_cells(self) -> List[str]:
        return [self.config["DESIGN_NAME"]]


@Step.factory.register()
class ApplyDEFTemplate(OdbpyStep):
    """
    Copies the floorplan of a "template" DEF file for a new design, i.e.,
    it will copy the die area, core area, and non-power pin names and locations.
    """

    id = "Odb.ApplyDEFTemplate"
    name = "Apply DEF Template"

    config_vars = [
        Variable(
            "FP_DEF_TEMPLATE",
            Optional[Path],
            "Points to the DEF file to be used as a template.",
        ),
        Variable(
            "FP_TEMPLATE_MATCH_MODE",
            Literal["strict", "permissive"],
            "Whether to require that the pin set of the DEF template and the design should be identical. In permissive mode, pins that are in the design and not in the template will be excluded, and vice versa.",
            default="strict",
        ),
        Variable(
            "FP_TEMPLATE_COPY_POWER_PINS",
            bool,
            "Whether to *always* copy all power pins from the DEF template to the design.",
            default=False,
        ),
    ]

    def get_script_path(self):
        return os.path.join(
            get_script_dir(),
            "odbpy",
            "apply_def_template.py",
        )

    def get_command(self) -> List[str]:
        args = [
            "--def-template",
            self.config["FP_DEF_TEMPLATE"],
            f"--{self.config['FP_TEMPLATE_MATCH_MODE']}",
        ]
        if self.config["FP_TEMPLATE_COPY_POWER_PINS"]:
            args.append("--copy-def-power")
        return super().get_command() + args

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["FP_DEF_TEMPLATE"] is None:
            info("No DEF template provided, skipping…")
            return {}, {}

        views_updates, metrics_updates = super().run(state_in, **kwargs)
        design_area_string = self.state_in.result().metrics.get("design__die__bbox")
        if design_area_string:
            template_area_string = metrics_updates["design__die__bbox"]
            template_area = [Decimal(point) for point in template_area_string.split()]
            design_area = [Decimal(point) for point in design_area_string.split()]
            if template_area != design_area:
                self.warn(
                    "The die area specificied in FP_DEF_TEMPLATE is different than the design die area. Pin placement may be incorrect."
                )
                self.warn(
                    f"Design area: {design_area_string}. Template def area: {template_area_string}"
                )
        return views_updates, {}


@Step.factory.register()
class SetPowerConnections(OdbpyStep):
    """
    Uses JSON netlist and module information in Odb to add global power
    connections for macros at the top level of a design.

    If the JSON netlist is hierarchical (e.g. by using a keep hierarchy
    attribute) this Step emits a warning and does not attempt to connect any
    macros instantiated within submodules.
    """

    id = "Odb.SetPowerConnections"
    name = "Set Power Connections"
    inputs = [DesignFormat.JSON_HEADER, DesignFormat.ODB]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "power_utils.py")

    def get_subcommand(self) -> List[str]:
        return ["set-power-connections"]

    def get_command(self) -> List[str]:
        state_in = self.state_in.result()
        return super().get_command() + [
            "--input-json",
            str(state_in[DesignFormat.JSON_HEADER]),
        ]


@Step.factory.register()
class WriteVerilogHeader(OdbpyStep):
    """
    Writes a Verilog header of the module using information from the generated
    PDN, guarded by the value of ``VERILOG_POWER_DEFINE``, and the JSON header.
    """

    id = "Odb.WriteVerilogHeader"
    name = "Write Verilog Header"
    inputs = [DesignFormat.ODB, DesignFormat.JSON_HEADER]
    outputs = [DesignFormat.VERILOG_HEADER]

    config_vars = OdbpyStep.config_vars + [
        Variable(
            "VERILOG_POWER_DEFINE",
            Optional[str],
            "Specifies the name of the define used to guard power and ground connections in the output Verilog header.",
            deprecated_names=["SYNTH_USE_PG_PINS_DEFINES", "SYNTH_POWER_DEFINE"],
            default="USE_POWER_PINS",
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "power_utils.py")

    def get_subcommand(self) -> List[str]:
        return ["write-verilog-header"]

    def get_command(self) -> List[str]:
        state_in = self.state_in.result()
        command = super().get_command() + [
            "--output-vh",
            os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.vh"),
            "--input-json",
            str(state_in[DesignFormat.JSON_HEADER]),
        ]
        if self.config.get("VERILOG_POWER_DEFINE") is not None:
            command += ["--power-define", self.config["VERILOG_POWER_DEFINE"]]
        else:
            self.warn(
                "VERILOG_POWER_DEFINE undefined. Verilog Header will not include power ports."
            )

        return command

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates, metrics_updates = super().run(state_in, **kwargs)
        views_updates[DesignFormat.VERILOG_HEADER] = Path(
            os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.vh")
        )
        return views_updates, metrics_updates


@Step.factory.register()
class ManualMacroPlacement(OdbpyStep):
    """
    Performs macro placement using a simple configuration file. The file is
    defined as a line-break delimited list of instances and positions, in the
    format ``instance_name X_pos Y_pos Orientation``.

    If no macro instances are configured, this step is skipped.
    """

    id = "Odb.ManualMacroPlacement"
    name = "Manual Macro Placement"

    config_vars = [
        Variable(
            "MACRO_PLACEMENT_CFG",
            Optional[Path],
            "Path to an optional override for instance placement instead of the `MACROS` object for compatibility with LibreLane 1. If both are `None`, this step is skipped.",
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "placers.py")

    def get_subcommand(self) -> List[str]:
        return ["manual-macro-placement"]

    def get_command(self) -> List[str]:
        return super().get_command() + [
            "--config",
            os.path.join(self.step_dir, "placement.cfg"),
            "--fixed",
        ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        cfg_file = Path(os.path.join(self.step_dir, "placement.cfg"))
        if cfg_ref := self.config.get("MACRO_PLACEMENT_CFG"):
            self.warn(
                "Using 'MACRO_PLACEMENT_CFG' is deprecated. It is recommended to use the new 'MACROS' configuration variable."
            )
            shutil.copyfile(cfg_ref, cfg_file)
        elif macros := self.config.get("MACROS"):
            instance_count = sum(len(m.instances) for m in macros.values())
            if instance_count >= 1:
                with open(cfg_file, "w") as f:
                    for module, macro in macros.items():
                        if not isinstance(macro, Macro):
                            raise StepException(
                                f"Misconstructed configuration: macro definition for key {module} is not of type 'Macro'."
                            )
                        for name, data in macro.instances.items():
                            if data.location is not None:
                                if data.orientation is None:
                                    raise StepException(
                                        f"Instance {name} of macro {module} has a location configured, but no orientation."
                                    )
                                f.write(
                                    f"{name} {data.location[0]} {data.location[1]} {data.orientation}\n"
                                )
                            else:
                                verbose(
                                    f"Instance {name} of macro {module} has no location configured, ignoring…"
                                )

        if not cfg_file.exists():
            info(f"No instances found, skipping '{self.id}'…")
            return {}, {}

        return super().run(state_in, **kwargs)


@Step.factory.register()
class ReportWireLength(OdbpyStep):
    """
    Outputs a CSV of long wires, printed by length. Useful as a design aid to
    detect when one wire is connected to too many things.
    """

    outputs = []

    id = "Odb.ReportWireLength"
    name = "Report Wire Length"
    outputs = []

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "wire_lengths.py")

    def get_command(self) -> List[str]:
        return super().get_command() + [
            "--human-readable",
            "--report-out",
            os.path.join(self.step_dir, "wire_lengths.csv"),
        ]


@Step.factory.register()
class ReportDisconnectedPins(OdbpyStep):
    """
    Creates a table of disconnected pins in the design, updating metrics as
    appropriate.

    Disconnected pins may be marked "critical" if they are very likely to
    result in a dead design. We determine if a pin is critical as follows:

    * For the top-level macro: for these four kinds of pins: inputs, outputs,
      power inouts, and ground inouts, at least one of each kind must be
      connected or else all pins of a certain kind are counted as critical
      disconnected pins.
    * For instances:
        * Any unconnected input is a critical disconnected pin.
        * If there isn't at least one output connected, all disconnected
          outputs are critical disconnected pins.
        * Any disconnected power inout pins are critical disconnected pins.

    The metrics ``design__disconnected_pin__count`` and
    ``design__critical_disconnected_pin__count`` is updated. It is recommended
    to use the checker ``Checker.DisconnectedPins`` to check that there are
    no critical disconnected pins.
    """

    id = "Odb.ReportDisconnectedPins"
    name = "Report Disconnected Pins"

    config_vars = OdbpyStep.config_vars + [
        Variable(
            "IGNORE_DISCONNECTED_MODULES",
            Optional[List[str]],
            "Modules (or cells) to ignore when checking for disconnected pins.",
            pdk=True,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "disconnected_pins.py")

    def get_command(self) -> List[str]:
        command = super().get_command()
        if ignored_modules := self.config["IGNORE_DISCONNECTED_MODULES"]:
            for module in ignored_modules:
                command.append("--ignore-module")
                command.append(module)
        command.append("--write-full-table-to")
        command.append(os.path.join(self.step_dir, "full_disconnected_pins_table.txt"))
        return command


@Step.factory.register()
class AddRoutingObstructions(OdbpyStep):
    """
    Adds obstructions on metal layers which prevent shapes from being created in
    the designated areas.
    """

    id = "Odb.AddRoutingObstructions"
    name = "Add Obstructions"
    config_vars = [
        Variable(
            "ROUTING_OBSTRUCTIONS",
            Optional[List[str]],
            "Add routing obstructions to the design. If set to `None`, this step is skipped."
            + " Format of each obstruction item is: layer llx lly urx ury.",
            units="µm",
            default=None,
            deprecated_names=["GRT_OBS"],
        ),
    ]

    def get_obstruction_variable(self):
        return self.config_vars[0]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "defutil.py")

    def get_subcommand(self) -> List[str]:
        return ["add_obstructions"]

    def get_command(self) -> List[str]:
        command = super().get_command()
        if obstructions := self.config[self.config_vars[0].name]:
            for obstruction in obstructions:
                command.append("--obstructions")
                command.append(obstruction)
        return command

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config[self.get_obstruction_variable().name] is None:
            info(
                f"'{self.get_obstruction_variable().name}' is not defined. Skipping '{self.id}'…"
            )
            return {}, {}
        return super().run(state_in, **kwargs)


@Step.factory.register()
class RemoveRoutingObstructions(AddRoutingObstructions):
    """
    Removes any routing obstructions previously placed by
    <#Odb.AddRoutingObstructions>`_.
    """

    id = "Odb.RemoveRoutingObstructions"
    name = "Remove Obstructions"

    def get_subcommand(self) -> List[str]:
        return ["remove_obstructions"]


@Step.factory.register()
class AddPDNObstructions(AddRoutingObstructions):
    """
    Adds obstructions on metal layers which prevent shapes from being created in
    the designated areas.

    A soft-duplicate of <#Odb.AddRoutingObstructions>`_ , though this one uses
    a different variable name so the obstructions can be restricted for PDN
    steps only.
    """

    id = "Odb.AddPDNObstructions"
    name = "Add PDN obstructions"

    config_vars = [
        Variable(
            "PDN_OBSTRUCTIONS",
            Optional[List[str]],
            "Add routing obstructions to the design before PDN stage. If set to `None`, this step is skipped."
            + " Format of each obstruction item is: layer llx lly urx ury.",
            units="µm",
            default=None,
        ),
    ]


@Step.factory.register()
class RemovePDNObstructions(RemoveRoutingObstructions):
    """
    Removes any PDN obstructions previously placed by
    <#Odb.RemovePDNObstructions>`_.
    """

    id = "Odb.RemovePDNObstructions"
    name = "Remove PDN obstructions"

    config_vars = AddPDNObstructions.config_vars


_migrate_unmatched_io = lambda x: "unmatched_design" if x else "none"


@Step.factory.register()
class CustomIOPlacement(OdbpyStep):
    """
    Places I/O pins using a custom script, which uses a "pin order configuration"
    file.

    Check the reference documentation for the structure of said file.
    """

    id = "Odb.CustomIOPlacement"
    name = "Custom I/O Placement"
    long_name = "Custom I/O Pin Placement Script"

    config_vars = io_layer_variables + [
        Variable(
            "FP_IO_VLENGTH",
            Optional[Decimal],
            """
            The length of the pins with a north or south orientation. If unspecified by a PDK, the script will use whichever is higher of the following two values:
                * The pin width
                * The minimum value satisfying the minimum area constraint given the pin width
            """,
            units="µm",
            pdk=True,
        ),
        Variable(
            "FP_IO_HLENGTH",
            Optional[Decimal],
            """
            The length of the pins with an east or west orientation. If unspecified by a PDK, the script will use whichever is higher of the following two values:
                * The pin width
                * The minimum value satisfying the minimum area constraint given the pin width
            """,
            units="µm",
            pdk=True,
        ),
        Variable(
            "FP_PIN_ORDER_CFG",
            Optional[Path],
            "Path to the configuration file. If set to `None`, this step is skipped.",
        ),
        Variable(
            "ERRORS_ON_UNMATCHED_IO",
            Literal["none", "unmatched_design", "unmatched_cfg", "both"],
            "Controls whether to emit an error in: no situation, when pins exist in the design that do not exist in the config file, when pins exist in the config file that do not exist in the design, and both respectively. `both` is recommended, as the default is only for backwards compatibility with LibreLane 1.",
            default="unmatched_design",  # Backwards compatible with LibreLane 1
            deprecated_names=[
                ("QUIT_ON_UNMATCHED_IO", _migrate_unmatched_io),
            ],
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "io_place.py")

    def get_command(self) -> List[str]:
        length_args = []
        if self.config["FP_IO_VLENGTH"] is not None:
            length_args += ["--ver-length", self.config["FP_IO_VLENGTH"]]
        if self.config["FP_IO_HLENGTH"] is not None:
            length_args += ["--hor-length", self.config["FP_IO_HLENGTH"]]

        return (
            super().get_command()
            + [
                "--config",
                self.config["FP_PIN_ORDER_CFG"],
                "--hor-layer",
                self.config["FP_IO_HLAYER"],
                "--ver-layer",
                self.config["FP_IO_VLAYER"],
                "--hor-width-mult",
                str(self.config["FP_IO_VTHICKNESS_MULT"]),
                "--ver-width-mult",
                str(self.config["FP_IO_HTHICKNESS_MULT"]),
                "--hor-extension",
                str(self.config["FP_IO_HEXTEND"]),
                "--ver-extension",
                str(self.config["FP_IO_VEXTEND"]),
                "--unmatched-error",
                self.config["ERRORS_ON_UNMATCHED_IO"],
            ]
            + length_args
        )

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["FP_PIN_ORDER_CFG"] is None:
            info("No custom floorplan file configured, skipping…")
            return {}, {}
        return super().run(state_in, **kwargs)


@Step.factory.register()
class PortDiodePlacement(OdbpyStep):
    """
    Unconditionally inserts diodes on design ports diodes on ports,
    to mitigate the `antenna effect <https://en.wikipedia.org/wiki/Antenna_effect>`_.

    Useful for hardening macros, where ports may get long wires that are
    unaccounted for when hardening a top-level chip.

    The placement is **not legalized**.
    """

    id = "Odb.PortDiodePlacement"
    name = "Port Diode Placement Script"

    config_vars = [
        Variable(
            "DIODE_ON_PORTS",
            Literal["none", "in", "out", "both"],
            "Always insert diodes on ports with the specified polarities.",
            default="none",
        ),
        Variable(
            "GPL_CELL_PADDING",
            Decimal,
            "Cell padding value (in sites) for global placement. Used by this step only to emit a warning if it's 0.",
            units="sites",
            pdk=True,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "diodes.py")

    def get_subcommand(self) -> List[str]:
        return ["place"]

    def get_command(self) -> List[str]:
        cell, pin = self.config["DIODE_CELL"].split("/")

        return super().get_command() + [
            "--diode-cell",
            cell,
            "--diode-pin",
            pin,
            "--port-protect",
            self.config["DIODE_ON_PORTS"],
            "--threshold",
            "Infinity",
        ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["DIODE_ON_PORTS"] == "none":
            info("'DIODE_ON_PORTS' is set to 'none': skipping…")
            return {}, {}

        if self.config["GPL_CELL_PADDING"] == 0:
            self.warn(
                "'GPL_CELL_PADDING' is set to 0. This step may cause overlap failures."
            )

        return super().run(state_in, **kwargs)


@Step.factory.register()
class DiodesOnPorts(CompositeStep):
    """
    Unconditionally inserts diodes on design ports diodes on ports,
    to mitigate the `antenna effect <https://en.wikipedia.org/wiki/Antenna_effect>`_.

    Useful for hardening macros, where ports may get long wires that are
    unaccounted for when hardening a top-level chip.

    The placement is legalized by performing detailed placement and global
    routing after inserting the diodes.

    Prior to beta 16, this step did not legalize its placement: if you would
    like to retain the old behavior without legalization, try
    ``Odb.PortDiodePlacement``.
    """

    id = "Odb.DiodesOnPorts"
    name = "Diodes on Ports"
    long_name = "Diodes on Ports Protection Routine"

    Steps = [
        PortDiodePlacement,
        DetailedPlacement,
        GlobalRouting,
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["DIODE_ON_PORTS"] == "none":
            info("'DIODE_ON_PORTS' is set to 'none': skipping…")
            return {}, {}
        return super().run(state_in, **kwargs)


@Step.factory.register()
class FuzzyDiodePlacement(OdbpyStep):
    """
    Runs a custom diode placement script to mitigate the `antenna effect <https://en.wikipedia.org/wiki/Antenna_effect>`_.

    This script uses the `Manhattan length <https://en.wikipedia.org/wiki/Manhattan_distance>`_
    of a (non-existent) wire at the global placement stage, and places diodes
    if they exceed a certain threshold. This, however, requires some padding:
    `GPL_CELL_PADDING` and `DPL_CELL_PADDING` must be higher than 0 for this
    script to work reliably.

    The placement is *not* legalized.

    The original script was written by `Sylvain "tnt" Munaut <https://github.com/smunaut>`_.
    """

    id = "Odb.FuzzyDiodePlacement"
    name = "Fuzzy Diode Placement"

    config_vars = [
        Variable(
            "HEURISTIC_ANTENNA_THRESHOLD",
            Decimal,
            "A Manhattan distance above which a diode is recommended to be inserted by the heuristic inserter. If not specified, the heuristic algorithm.",
            units="µm",
            pdk=True,
        ),
        Variable(
            "GPL_CELL_PADDING",
            Decimal,
            "Cell padding value (in sites) for global placement. Used by this step only to emit a warning if it's 0.",
            units="sites",
            pdk=True,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "diodes.py")

    def get_subcommand(self) -> List[str]:
        return ["place"]

    def get_command(self) -> List[str]:
        cell, pin = self.config["DIODE_CELL"].split("/")

        threshold_opts = []
        if threshold := self.config["HEURISTIC_ANTENNA_THRESHOLD"]:
            threshold_opts = ["--threshold", threshold]

        return (
            super().get_command()
            + [
                "--diode-cell",
                cell,
                "--diode-pin",
                pin,
            ]
            + threshold_opts
        )

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["GPL_CELL_PADDING"] == 0:
            self.warn(
                "'GPL_CELL_PADDING' is set to 0. This step may cause overlap failures."
            )

        return super().run(state_in, **kwargs)


@Step.factory.register()
class HeuristicDiodeInsertion(CompositeStep):
    """
    Runs a custom diode insertion routine to mitigate the `antenna effect <https://en.wikipedia.org/wiki/Antenna_effect>`_.

    This script uses the `Manhattan length <https://en.wikipedia.org/wiki/Manhattan_distance>`_
    of a (non-existent) wire at the global placement stage, and places diodes
    if they exceed a certain threshold. This, however, requires some padding:
    `GPL_CELL_PADDING` and `DPL_CELL_PADDING` must be higher than 0 for this
    script to work reliably.

    The placement is then legalized by performing detailed placement and global
    routing after inserting the diodes.

    The original script was written by `Sylvain "tnt" Munaut <https://github.com/smunaut>`_.

    Prior to beta 16, this step did not legalize its placement: if you would
    like to retain the old behavior without legalization, try
    ``Odb.FuzzyDiodePlacement``.
    """

    id = "Odb.HeuristicDiodeInsertion"
    name = "Heuristic Diode Insertion"
    long_name = "Heuristic Diode Insertion Routine"

    Steps = [
        FuzzyDiodePlacement,
        DetailedPlacement,
        GlobalRouting,
    ]


@Step.factory.register()
class CellFrequencyTables(OdbpyStep):
    """
    Creates a number of tables to show the cell frequencies by:

    - Cells
    - Buffer cells only
    - Cell Function*
    - Standard Cell Library*

    * These tables only return meaningful info with PDKs distributed in the
      Open_PDKs format, i.e., all cells are named ``{scl}__{cell_fn}_{size}``.
    """

    id = "Odb.CellFrequencyTables"
    name = "Generate Cell Frequency Tables"

    def get_script_path(self):
        return os.path.join(
            get_script_dir(),
            "odbpy",
            "cell_frequency.py",
        )

    def get_buffer_list_file(self):
        return os.path.join(self.step_dir, "buffer_list.txt")

    def get_buffer_list_script(self):
        return os.path.join(get_script_dir(), "openroad", "buffer_list.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)

        env_copy = env.copy()
        lib_list = self.toolbox.filter_views(self.config, self.config["LIB"])
        env_copy["_PNR_LIBS"] = TclStep.value_to_tcl(lib_list)
        super().run_subprocess(
            ["openroad", "-no_splash", "-exit", self.get_buffer_list_script()],
            env=env_copy,
            log_to=self.get_buffer_list_file(),
        )
        return super().run(state_in, env=env, **kwargs)

    def get_command(self) -> List[str]:
        command = super().get_command()
        command.append("--buffer-list")
        command.append(self.get_buffer_list_file())
        command.append("--out-dir")
        command.append(self.step_dir)
        return command


@Step.factory.register()
class ManualGlobalPlacement(OdbpyStep):
    """
    This is an step to override the placement of one or more instances at
    user-specified locations.

    Alternatively, if this is a custom design with a few cells, this can be used
    in place of the global placement entirely.
    """

    id = "Odb.ManualGlobalPlacement"
    name = "Manual Global Placement"

    config_vars = OdbpyStep.config_vars + [
        Variable(
            "MANUAL_GLOBAL_PLACEMENTS",
            Optional[Dict[str, Instance]],
            description="A dictionary of instances to their global (non-legalized and unfixed) placement location.",
        )
    ]

    def get_script_path(self) -> str:
        return os.path.join(get_script_dir(), "odbpy", "placers.py")

    def get_subcommand(self) -> List[str]:
        return ["manual-global-placement"]

    def get_command(self) -> List[str]:
        assert self.config_path is not None, "get_command called before start()"
        return super().get_command() + ["--step-config", self.config_path]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["MANUAL_GLOBAL_PLACEMENTS"] is None:
            info("'MANUAL_GLOBAL_PLACEMENTS' not set, skipping…")
            return {}, {}
        return super().run(state_in, **kwargs)


@dataclass
class ECOBuffer:
    """
    :param target: The driver to insert an ECO buffer after or sink to insert an
        ECO buffer before, in the format instance_name/pin_name.
    :param buffer: The kind of buffer cell to use.
    :param placement: The coarse placement for this buffer (to be legalized.)
        If unset, depending on whether the target is a driver or a sink:

        - Driver: The placement will be the average of the driver and all sinks.

        - Sink: The placement will be the average of the sink and all drivers.
    """

    target: str
    buffer: str
    placement: Optional[Tuple[Decimal, Decimal]] = None


@Step.factory.register()
class InsertECOBuffers(OdbpyStep):
    """
    Experimental step to insert ECO buffers on either drivers or sinks after
    global or detailed routing. The placement is legalized and global routing is
    incrementally re-run for affected nets. Useful for manually fixing some hold
    violations.

    If run after detailed routing, detailed routing must be re-run as affected
    nets that are altered are removed and require re-routing.

    INOUT and FEEDTHRU ports are not supported.
    """

    id = "Odb.InsertECOBuffers"
    name = "Insert ECO Buffers"

    config_vars = (
        dpl_variables
        + grt_variables
        + [
            Variable(
                "INSERT_ECO_BUFFERS",
                Optional[List[ECOBuffer]],
                "List of buffers to insert",
            )
        ]
    )

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "eco_buffer.py")

    def get_command(self) -> List[str]:
        assert self.config_path is not None, "get_command called before start()"
        return super().get_command() + ["--step-config", self.config_path]


@dataclass
class ECODiode:
    """
    :param target: The sink whose net gets a diode connected, in the format
        instance_name/pin_name.
    :param placement: The coarse placement for this diode (to be legalized.)
        If unset, the diode is placed at the same location as the target
        instance, with legalization later moving it to a valid location.
    """

    target: str
    placement: Optional[Tuple[Decimal, Decimal]] = None


@Step.factory.register()
class InsertECODiodes(OdbpyStep):
    """
    Experimental step to create and attach ECO diodes to the nets of sinks after
    global or detailed routing. The placement is legalized and global routing is
    incrementally re-run for affected nets. Useful for manually fixing some
    antenna violations.

    If run after detailed routing, detailed routing must be re-run as affected
    nets that are altered are removed and require re-routing.
    """

    id = "Odb.InsertECODiodes"
    name = "Insert ECO Diodes"

    config_vars = (
        grt_variables
        + dpl_variables
        + [
            Variable(
                "INSERT_ECO_DIODES",
                Optional[List[ECODiode]],
                "List of sinks to insert diodes for.",
            )
        ]
    )

    def get_script_path(self):
        return os.path.join(get_script_dir(), "odbpy", "eco_diode.py")

    def get_command(self) -> List[str]:
        assert self.config_path is not None, "get_command called before start()"
        return super().get_command() + ["--step-config", self.config_path]

    def run(self, state_in: State, **kwargs):
        if self.config["DIODE_CELL"] is None:
            info(f"'DIODE_CELL' not set. Skipping '{self.id}'…")
            return {}, {}
        return super().run(state_in, **kwargs)
