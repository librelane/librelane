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
from typing import ClassVar, Set, Tuple, List
from decimal import Decimal
from typing import Optional

from .step import ViewsUpdate, MetricsUpdate, Step, StepError, DeferredStepError, State

from ..logging import info, debug, verbose
from ..config import Variable
from ..common import Filter, parse_metric_modifiers
from ..state import DesignFormat


@Step.factory.register()
class NetlistAssignStatements(Step):
    """
    Raises a StepError if the Netlist has an ``assign`` statement in it.

    ``assign`` statements are known to cause bugs in some PnR tools.
    """

    id = "Checker.NetlistAssignStatements"
    name = "Netlist Assign Statement Checker"

    inputs = [DesignFormat.NETLIST]
    outputs = []

    config_vars = [
        Variable(
            "ERROR_ON_NL_ASSIGN_STATEMENTS",
            bool,
            "Whether to emit an error or simply warn about the existence",
            default=True,
        )
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        assign_rx = re.compile(r"^\s*\bassign\b")
        netlist_in = str(state_in[DesignFormat.NETLIST])
        emit_error = self.config["ERROR_ON_NL_ASSIGN_STATEMENTS"]
        found = False
        with open(netlist_in, "r", encoding="utf8") as f:
            for i, line in enumerate(f, start=1):
                if assign_rx.search(line) is not None:
                    found = True
                    (self.err if emit_error else self.warn)(
                        f"{os.path.relpath(netlist_in)}:{i}: assign statement found in netlist"
                    )
        if found and self.config["ERROR_ON_NL_ASSIGN_STATEMENTS"]:
            raise StepError("One or more assign statements found in the netlist.")
        return {}, {}


class MetricChecker(Step):
    """
    Raises a (deferred) error if a Decimal metric exceeds a certain threshold.
    """

    inputs = []
    outputs = []

    metric_name: ClassVar[str] = NotImplemented
    metric_description: ClassVar[str] = NotImplemented
    deferred: ClassVar[bool] = True
    error_on_var: Optional[Variable] = None

    @classmethod
    def get_help_md(Self, **kwargs):  # pragma: no cover
        threshold_string = Self.get_threshold_description(None)
        if threshold_string is None:
            threshold_string = str(Self.get_threshold(None))
        dynamic_docstring = "Raises"
        if Self.deferred:
            dynamic_docstring += " a deferred error"
        else:
            dynamic_docstring += " an immediate error"
        dynamic_docstring += f" if {Self.metric_description} (metric: ``{Self.metric_name}``) are >= {threshold_string}."
        dynamic_docstring += (
            " Doesn't raise an error depending on error_on_var if defined."
        )

        return super().get_help_md(docstring_override=dynamic_docstring, **kwargs)

    def get_threshold(self: Optional["MetricChecker"]) -> Optional[Decimal]:
        return Decimal(0)

    def get_threshold_description(self: Optional["MetricChecker"]) -> Optional[str]:
        return None

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        threshold = self.get_threshold()

        if threshold is None:
            self.warn(
                f"Threshold for {self.metric_description} is not set. The checker will be skipped."
            )
        else:
            metric_value = state_in.metrics.get(self.metric_name)
            if metric_value is not None:
                if metric_value > threshold:
                    error_msg = f"{metric_value} {self.metric_description} found."
                    if (
                        hasattr(self, "error_on_var")
                        and self.error_on_var
                        and not self.config.get(self.error_on_var.name)
                    ):
                        debug(self.config.get(self.error_on_var.name))
                        self.warn(f"{error_msg}")
                    elif self.deferred:
                        self.err(f"{error_msg} - deferred")
                        raise DeferredStepError(error_msg)
                    else:
                        self.err(f"{error_msg}")
                        raise StepError(error_msg)

                else:
                    info(f"Check for {self.metric_description} clear.")
            else:
                self.warn(
                    f"The {self.metric_description} metric was not found. Are you sure the relevant step was run?"
                )

        return {}, {}


@Step.factory.register()
class YosysUnmappedCells(MetricChecker):
    id = "Checker.YosysUnmappedCells"
    name = "Unmapped Cells Checker"
    deferred = False

    metric_name = "design__instance_unmapped__count"
    metric_description = "Unmapped Yosys instances"

    error_on_var = Variable(
        "ERROR_ON_UNMAPPED_CELLS",
        bool,
        "Checks for unmapped cells after synthesis and quits immediately if so.",
        deprecated_names=["QUIT_ON_UNMAPPED_CELLS", "CHECK_UNMAPPED_CELLS"],
        default=True,
    )
    config_vars = [error_on_var]


@Step.factory.register()
class YosysSynthChecks(MetricChecker):
    id = "Checker.YosysSynthChecks"
    name = "Yosys Synth Checks"
    deferred = False

    metric_name = "synthesis__check_error__count"
    metric_description = "Yosys check errors"
    error_on_var = Variable(
        "ERROR_ON_SYNTH_CHECKS",
        bool,
        "Quits the flow immediately if one or more synthesis check errors are flagged. This checks for combinational loops and/or wires with no drivers.",
        default=True,
        deprecated_names=["QUIT_ON_SYNTH_CHECKS"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class TrDRC(MetricChecker):
    id = "Checker.TrDRC"
    name = "Routing DRC Checker"
    long_name = "Routing Design Rule Checker"

    metric_name = "route__drc_errors"
    metric_description = "Routing DRC errors"

    error_on_var = Variable(
        "ERROR_ON_TR_DRC",
        bool,
        "Checks for DRC violations after routing and exits the flow if any was found.",
        default=True,
        deprecated_names=["QUIT_ON_TR_DRC"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class MagicDRC(MetricChecker):
    id = "Checker.MagicDRC"
    name = "Magic DRC Checker"
    long_name = "Magic Design Rule Checker"

    metric_name = "magic__drc_error__count"
    metric_description = "Magic DRC errors"

    error_on_var = Variable(
        "ERROR_ON_MAGIC_DRC",
        bool,
        "Checks for DRC violations after magic DRC is executed and exits the flow if any was found.",
        default=True,
        deprecated_names=["QUIT_ON_MAGIC_DRC"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class IllegalOverlap(MetricChecker):
    id = "Checker.IllegalOverlap"
    name = "Illegal Overlap Checker"
    long_name = "Spice Extraction-based Illegal Overlap Checker"

    metric_name = "magic__illegal_overlap__count"
    metric_description = "Magic Illegal Overlap errors"

    error_on_var = Variable(
        "ERROR_ON_ILLEGAL_OVERLAPS",
        bool,
        "Checks for illegal overlaps during Magic extraction. In some cases, these imply existing undetected shorts in the design. It raises an error at the end of the flow if so.",
        default=True,
        deprecated_names=["QUIT_ON_ILLEGAL_OVERLAPS"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class DisconnectedPins(MetricChecker):
    id = "Checker.DisconnectedPins"
    name = "Disconnected Pins Checker"
    deferred = False

    metric_name = "design__critical_disconnected_pin__count"
    metric_description = "critical disconnected pins"

    error_on_var = Variable(
        "ERROR_ON_DISCONNECTED_PINS",
        bool,
        "Checks for disconnected instance pins after detailed routing and quits immediately if so.",
        default=True,
        deprecated_names=["QUIT_ON_DISCONNECTED_PINS"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class WireLength(MetricChecker):
    id = "Checker.WireLength"
    name = "Wire Length Threshold Checker"

    metric_name = "route__wirelength__max"
    metric_description = "Threshold-surpassing long wires"

    error_on_var = Variable(
        "ERROR_ON_LONG_WIRE",
        bool,
        "Checks if any wire length exceeds the threshold set in the PDK. If so, an error is raised at the end of the flow.",
        default=True,
        deprecated_names=["QUIT_ON_LONG_WIRE"],
    )
    config_vars = [error_on_var]

    def get_threshold(self) -> Optional[Decimal]:
        threshold = self.config["WIRE_LENGTH_THRESHOLD"]
        assert threshold is None or isinstance(threshold, Decimal)
        return threshold

    def get_threshold_description(self) -> Optional[str]:
        return "the threshold specified in the configuration file."


@Step.factory.register()
class XOR(MetricChecker):
    id = "Checker.XOR"
    name = "XOR Difference Checker"
    long_name = "Magic vs. KLayout XOR Difference Checker"

    metric_name = "design__xor_difference__count"
    metric_description = "XOR differences"

    error_on_var = Variable(
        "ERROR_ON_XOR_ERROR",
        bool,
        "Checks for geometric differences between the Magic and KLayout stream-outs. If any exist, raise an error at the end of the flow.",
        default=True,
        deprecated_names=["QUIT_ON_XOR_ERROR"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class LVS(MetricChecker):
    id = "Checker.LVS"
    name = "LVS Error Checker"
    long_name = "Layout vs. Schematic Error Checker"

    metric_name = "design__lvs_error__count"
    metric_description = "LVS errors"

    error_on_var = Variable(
        "ERROR_ON_LVS_ERROR",
        bool,
        "Checks for LVS errors after Netgen is executed. If any exist, it raises an error at the end of the flow.",
        default=True,
        deprecated_names=["QUIT_ON_LVS_ERROR"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class PowerGridViolations(MetricChecker):
    id = "Checker.PowerGridViolations"
    name = "Power Grid Violation Checker"

    metric_name = "design__power_grid_violation__count"
    metric_description = "power grid violations (as reported by OpenROAD PSM- you may ignore these if LVS passes)"

    error_on_var = Variable(
        "ERROR_ON_PDN_VIOLATIONS",
        bool,
        "Checks for unconnected nodes in the power grid. If any exists, an error is raised at the end of the flow.",
        default=True,
        deprecated_names=["QUIT_ON_PDN_VIOLATIONS", "FP_PDN_CHECK_NODES"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class LintErrors(MetricChecker):
    id = "Checker.LintErrors"
    name = "Lint Errors Checker"
    long_name = "Lint Errors Checker"
    deferred = False

    metric_name = "design__lint_error__count"
    metric_description = "Lint errors"

    error_on_var = Variable(
        "ERROR_ON_LINTER_ERRORS",
        bool,
        "Quit immediately on any linter errors.",
        default=True,
        deprecated_names=["QUIT_ON_VERILATOR_ERRORS", "QUIT_ON_LINTER_ERRORS"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class LintWarnings(MetricChecker):
    id = "Checker.LintWarnings"
    name = "Lint Warnings Checker"
    long_name = "Lint Warnings Checker"
    deferred = False

    metric_name = "design__lint_warning__count"
    metric_description = "Lint warnings"

    error_on_var = Variable(
        "ERROR_ON_LINTER_WARNINGS",
        bool,
        "Raise an error immediately on any linter warnings.",
        default=False,
        deprecated_names=["QUIT_ON_VERILATOR_WARNINGS", "QUIT_ON_LINTER_WARNINGS"],
    )
    config_vars = [error_on_var]


@Step.factory.register()
class LintTimingConstructs(MetricChecker):
    id = "Checker.LintTimingConstructs"
    name = "Lint Timing Error Checker"
    long_name = "Lint Timing Errors Checker"
    deferred = False

    metric_name = "design__lint_timing_construct__count"
    metric_description = "Lint Timing Errors"

    error_on_var = Variable(
        "ERROR_ON_LINTER_TIMING_CONSTRUCTS",
        bool,
        "Quit immediately on any discovered timing constructs during linting.",
        default=True,
        deprecated_names=["QUIT_ON_LINTER_TIMING_CONSTRUCTS"],
    )
    config_vars = [error_on_var]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metric_value = state_in.metrics.get(self.metric_name)

        if metric_value is not None:
            if metric_value > 0:
                error_msg = "Timing constructs found in the RTL. Please remove them or wrap them around an ifdef. It heavily unrecommended to rely on timing constructs for synthesis."
                self.err(f"{error_msg}")
                raise StepError(error_msg)
            else:
                info(f"Check for {self.metric_description} clear.")
        else:
            self.warn(
                f"The {self.metric_description} metric was not found. Are you sure the relevant step was run?"
            )

        return {}, {}


@Step.factory.register()
class KLayoutDRC(MetricChecker):
    id = "Checker.KLayoutDRC"
    name = "KLayout DRC Checker"
    long_name = "KLayout Design Rule Checker"

    metric_name = "klayout__drc_error__count"
    metric_description = "KLayout DRC errors"

    error_on_var = Variable(
        "ERROR_ON_KLAYOUT_DRC",
        bool,
        "Checks for DRC violations after KLayout DRC is executed and exits the flow if any was found.",
        default=True,
        deprecated_names=["QUIT_ON_KLAYOUT_DRC"],
    )
    config_vars = [error_on_var]


class TimingViolations(MetricChecker):
    """
    Abstract class for timing violations.

    This class creates `*_VIOLATION_CORNERS` variable for a subclass based on
    with a name based on `violation_type`. The default value is `[""]` which
    indicates matching no corners. This can be overriden by `corner_override`

    :cvar violation_type:
        Type of the timing violation. Used in log messages.

    :cvar corner_override:
        Overrides the subclass's `*_VIOLATION_CORNERS` variable.

    :cvar match_none_wildcard:
        Wildcard used to match no corners.
    """

    name = "Timing Violations Checker"
    long_name = "Timing Violations Checker"

    violation_type: str = NotImplemented
    match_none_wildcard = ""
    corner_override: Optional[List[str]] = None
    base_corner_var_name = "TIMING_VIOLATION_CORNERS"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.config_vars = cls.config_vars.copy()
        cls.config_vars += [
            Variable(
                cls.base_corner_var_name,
                List[str],
                "A list of wildcards matching IPVT corners to use during checking for timing violations.",
                pdk=True,
                deprecated_names=["TIMING_VIOLATIONS_CORNERS"],
            ),
            cls.get_corner_variable(),
        ]

    @classmethod
    def get_corner_variable(cls) -> Variable:
        replace_by = cls.violation_type.upper().replace(" ", "_")
        variable = Variable(
            cls.base_corner_var_name.replace("TIMING", replace_by),
            Optional[List[str]],
            f"A list of wildcards matching IPVT corners to use during checking for {cls.violation_type} violations.",
        )
        if cls.corner_override:
            variable.default = cls.corner_override
        return variable

    def get_corner_wildcards(self):
        wildcards = self.config.get(self.get_corner_variable().name) or self.config.get(
            self.base_corner_var_name
        )
        assert wildcards is not None
        wildcards = [
            wildcard
            for wildcard in wildcards
            if wildcard is not self.match_none_wildcard
        ]
        return wildcards

    def check_timing_violations(
        self,
        metric_basename: str,
        state_in: State,
        threshold: Optional[Decimal],
        violation_type: str,
    ):
        if not threshold:
            threshold = Decimal(0)

        metrics = {
            key: value
            for key, value in state_in.metrics.items()
            if metric_basename in key
        }
        debug("Metrics ▶")
        debug(metrics)
        if not metrics:
            self.warn(f"No metrics found for {metric_basename}.")
        else:
            metric_corners = set(
                [parse_metric_modifiers(key)[1]["corner"] for key in metrics.keys()]
            )

            all_config_wildcards = set(self.get_corner_wildcards())
            corner_filter = Filter(all_config_wildcards)
            matched_config_wildcards: Set[str] = set()
            for corner in metric_corners:
                matched_config_wildcards.update(
                    corner_filter.get_matching_wildcards(corner)
                )
            unmatched_config_wildcards = all_config_wildcards - matched_config_wildcards

            matched_corners = set(corner_filter.filter(metric_corners))
            unmatched_corners = metric_corners - matched_corners

            all_violating_corners = set(
                [
                    corner
                    for corner in metric_corners
                    if metrics[f"{metric_basename}:{corner}"] > threshold
                ]
            )

            matched_violating_corners = all_violating_corners.intersection(
                matched_corners
            )

            err_violating_corner = matched_violating_corners
            warn_violating_corner = all_violating_corners - matched_violating_corners

            debug("All corners ▶")
            debug(metric_corners)
            debug("Corners unmatched by config ▶")
            debug(unmatched_corners)
            debug("Violations at corners causing errors ▶")
            debug(err_violating_corner)
            debug("Violations at corners causing warnings ▶")
            debug(warn_violating_corner)

            err_msg = []
            warn_msg = []
            if len(unmatched_config_wildcards):
                err_msg.append(
                    f"One or more wildcards specified in {self.get_corner_variable().name} did not match any corners:"
                )
                for wildcard in sorted(unmatched_config_wildcards):
                    err_msg.append(f"- {wildcard}")

            if len(warn_violating_corner):
                warn_msg.append(
                    f"{violation_type.title()} violations found in the following corners:"
                )
                for corner in sorted(warn_violating_corner):
                    warn_msg.append(f"* {corner}")

            if err_violating_corner:
                err_msg.append(
                    f"{violation_type.title()} violations found in the following corners:"
                )
                for corner in sorted(err_violating_corner):
                    err_msg.append(f"* {corner}")

            if warn_msg:
                self.warn("\n".join(warn_msg))
            if not err_violating_corner:
                verbose(f"No {violation_type} violations found")
            if err_msg:
                raise DeferredStepError("\n".join(err_msg))

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        self.check_timing_violations(
            f"{self.metric_name}__corner",
            state_in,
            self.get_threshold(),
            self.violation_type,
        )

        return {}, {}


@Step.factory.register()
class SetupViolations(TimingViolations):
    id = "Checker.SetupViolations"
    name = "Setup Timing Violations Checker"
    long_name = "Setup Timing Violations Checker"
    violation_type = "setup"

    metric_name = "timing__setup_vio__count"


@Step.factory.register()
class MaxCapViolations(TimingViolations):
    id = "Checker.MaxCapViolations"
    name = "Max Cap Violations Checker"
    long_name = "Maximum Capacitance Violations Checker"
    violation_type = "max cap"

    metric_name = "design__max_cap_violation__count"
    corner_override = [""]


@Step.factory.register()
class MaxSlewViolations(TimingViolations):
    id = "Checker.MaxSlewViolations"
    name = "Max Slew Violations Checker"
    long_name = "Maximum Slew Violations Checker"
    violation_type = "max slew"

    metric_name = "design__max_slew_violation__count"
    corner_override = [""]


@Step.factory.register()
class HoldViolations(TimingViolations):
    id = "Checker.HoldViolations"
    name = "Hold Timing Violations Checker"
    long_name = "Hold Timing Violations Checker"
    violation_type = "hold"

    metric_name = "timing__hold_vio__count"
