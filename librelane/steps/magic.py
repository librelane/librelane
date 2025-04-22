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
import shutil
import functools
import subprocess
from signal import SIGKILL
from decimal import Decimal
from abc import abstractmethod
from typing import Any, Literal, List, Optional, Tuple

from .step import (
    DefaultOutputProcessor,
    OutputProcessor,
    StepError,
    StepException,
    ViewsUpdate,
    MetricsUpdate,
    Step,
)
from .tclstep import TclStep
from ..state import DesignFormat, State

from ..config import Variable
from ..common import get_script_dir, DRC as DRCObject, Path, mkdirp


class MagicOutputProcessor(OutputProcessor):
    _error_patterns = [
        re.compile(rx)
        for rx in [
            r"DEF read.*\(Error\).*",
            r"LEF read.*\(Error\).*",
            r"Error while reading cell(?!.*Warning:).*",
            r".*Calma output error.*",
            r".*is an abstract view.*",
        ]
    ]

    key = "magic_output"

    def __init__(self, step: Step, report_dir: str, silent: bool) -> None:
        super().__init__(step, report_dir, silent)
        self.fatal_error_count = 0

    def process_line(self, line: str) -> bool:
        for pattern in self._error_patterns:
            if pattern.match(line):
                self.fatal_error_count += 1
                self.step.err(line)
                return True
        return False

    def result(self) -> Any:
        return {"fatal_error_count": self.fatal_error_count}


class MagicStep(TclStep):
    inputs = [DesignFormat.GDS]
    outputs = []

    output_processors = [MagicOutputProcessor, DefaultOutputProcessor]

    config_vars = [
        Variable(
            "MAGIC_DEF_LABELS",
            bool,
            "A flag to choose whether labels are read with DEF files or not. From magic docs: \"The '-labels' option to the 'def read' command causes each net in the NETS and SPECIALNETS sections of the DEF file to be annotated with a label having the net name as the label text.\" If LVS fails, try disabling this option.",
            default=True,
        ),
        Variable(
            "MAGIC_GDS_POLYGON_SUBCELLS",
            bool,
            'A flag to enable polygon subcells in magic for gds read potentially speeding up magic. From magic docs: "Put non-Manhattan polygons. This prevents interations with other polygons on the same plane and so reduces tile splitting."',
            default=False,
        ),
        Variable(
            "MAGIC_DEF_NO_BLOCKAGES",
            bool,
            "If set to true, blockages in DEF files are ignored. Otherwise, they are read as sheets of metal by Magic.",
            default=True,
        ),
        Variable(
            "MAGIC_INCLUDE_GDS_POINTERS",
            bool,
            "A flag to choose whether to include GDS pointers in the generated mag files or not.",
            default=False,
        ),
        Variable(
            "MAGICRC",
            Path,
            "A path to the `.magicrc` file which is sourced before running magic in the flow.",
            deprecated_names=["MAGIC_MAGICRC"],
            pdk=True,
        ),
        Variable(
            "MAGIC_TECH",
            Path,
            "A path to a Magic tech file which, mainly, has DRC rules.",
            deprecated_names=["MAGIC_TECH_FILE"],
            pdk=True,
        ),
        Variable(
            "MAGIC_PDK_SETUP",
            Path,
            "A path to a PDK-specific setup file sourced by `.magicrc`.",
            pdk=True,
        ),
        Variable(
            "CELL_MAGS",
            Optional[List[Path]],
            "A list of pre-processed concrete views for cells. Read as a fallback for undefined cells.",
            pdk=True,
        ),
        Variable(
            "CELL_MAGLEFS",
            Optional[List[Path]],
            "A list of pre-processed abstract LEF views for cells. Read as a fallback for undefined cells in scripts where cells are black-boxed.",
            pdk=True,
        ),
        Variable(
            "MAGIC_CAPTURE_ERRORS",
            bool,
            "Capture errors print by Magic and quit when a fatal error is encountered."
            + " Fatal errors are determined heuristically. It is not guaranteed that they are fatal errors."
            + " Hence this is function is gated by a variable."
            + " This function is needed because Magic does not throw errors.",
            default=True,
        ),
    ]

    @abstractmethod
    def get_script_path(self) -> str:
        pass

    def get_command(self) -> List[str]:
        return [
            "magic",
            "-dnull",
            "-noconsole",
            "-rcfile",
            self.config["MAGICRC"],
            os.path.join(get_script_dir(), "magic", "wrapper.tcl"),
        ]

    def prepare_env(self, env: dict, state: State) -> dict:
        env = super().prepare_env(env, state)

        env["_MAGIC_SCRIPT"] = self.get_script_path()
        env["MACRO_GDS_FILES"] = ""
        for gds in self.toolbox.get_macro_views(self.config, DesignFormat.GDS):
            env["MACRO_GDS_FILES"] += f" {gds}"

        return env

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        env = self.prepare_env(env, state_in)

        check = False
        if "check" in kwargs:
            check = kwargs.pop("check")

        command = self.get_command()

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )

        if (
            self.config["MAGIC_CAPTURE_ERRORS"]
            and subprocess_result["magic_output"]["fatal_error_count"]
        ):
            raise StepError("Encountered one or more fatal errors while running Magic.")

        generated_metrics = subprocess_result["generated_metrics"]

        views_updates: ViewsUpdate = {}
        for output in self.outputs:
            if output.value.multiple:
                # Too step-specific.
                continue
            path = Path(env[f"SAVE_{output.name}"])
            if not path.exists():
                continue
            views_updates[output] = path

        return views_updates, generated_metrics


@Step.factory.register()
class WriteLEF(MagicStep):
    """
    Writes a LEF view of the design using the GDS using Magic.
    """

    id = "Magic.WriteLEF"
    name = "Write LEF (Magic)"

    inputs = [DesignFormat.GDS, DesignFormat.DEF]
    outputs = [DesignFormat.LEF]

    config_vars = MagicStep.config_vars + [
        Variable(
            "MAGIC_LEF_WRITE_USE_GDS",
            bool,
            "A flag to choose whether to use GDS for LEF writing. If not, then the extraction will be done using abstract LEF views.",
            default=False,
        ),
        Variable(
            "MAGIC_WRITE_FULL_LEF",
            bool,
            "A flag to specify whether or not the output LEF should include all shapes inside the macro or an abstracted view of the macro LEF view via magic.",
            default=False,
        ),
        Variable(
            "MAGIC_WRITE_LEF_PINONLY",
            bool,
            "If true, the LEF write will mark only areas that are port labels as pins, while marking the rest of each related net as an obstruction. Otherwise, the labeled port and the any connected metal on the same layer are marked as a pin.",
            default=False,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "magic", "lef.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        env["MAGTYPE"] = "mag"
        return super().run(state_in, **kwargs)


@Step.factory.register()
class StreamOut(MagicStep):
    """
    Converts DEF views into GDSII streams using Magic.

    If ``PRIMARY_GDSII_STREAMOUT_TOOL`` is set to ``"magic"``, both GDS and MAG_GDS
    will be updated, and if set to another tool, only ``MAG_GDS`` will be
    updated.
    """

    id = "Magic.StreamOut"
    name = "GDSII Stream Out (Magic)"

    inputs = [DesignFormat.DEF]
    outputs = [DesignFormat.GDS, DesignFormat.MAG_GDS, DesignFormat.MAG]

    config_vars = MagicStep.config_vars + [
        Variable(
            "DIE_AREA",
            Optional[Tuple[Decimal, Decimal, Decimal, Decimal]],
            'Specific die area to be used in floorplanning when `FP_SIZING` is set to `absolute`. Specified as a 4-corner rectangle "x0 y0 x1 y1".',
            units="µm",
        ),
        Variable(
            "MAGIC_ZEROIZE_ORIGIN",
            bool,
            "A flag to move the layout such that it's origin in the lef generated by magic is 0,0.",
            default=False,
        ),
        Variable(
            "MAGIC_DISABLE_CIF_INFO",
            bool,
            "A flag to disable writing Caltech Intermediate Format (CIF) hierarchy and subcell array information to the GDSII file.",
            default=True,
            deprecated_names=["MAGIC_DISABLE_HIER_GDS"],
        ),
        Variable(
            "MAGIC_MACRO_STD_CELL_SOURCE",
            Literal["PDK", "macro"],
            "If set to PDK, magic will use the PDK definition of the STD cells for macros inside the design."
            + " Otherwise, the macro is completely treated as a blackbox and magic will use the existing cell definition inside"
            + " the macro gds."
            + " This mode is only supported for macros specified in MACROS variable",
            default="macro",
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "magic", "def", "mag_gds.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)

        env = self.prepare_env(env, state_in)
        if die_area := state_in.metrics.get("design__die__bbox"):
            env["DIE_AREA"] = die_area

        env["MAGTYPE"] = "mag"

        if (
            self.config["MACROS"] is not None
            and self.config["MAGIC_MACRO_STD_CELL_SOURCE"] == "macro"
        ):
            macro_gds = []
            env_copy = env.copy()
            for macro in self.config["MACROS"].keys():
                macro_gdses = [str(path) for path in self.config["MACROS"][macro].gds]
                if len(macro_gdses) > 1:
                    raise StepException(
                        "Multiple GDSII files in one Macro currently unsupported when MAGIC_MACRO_STD_CELL_SOURCE is set to 'macro'."
                    )
                env_copy["_GDS_IN"] = macro_gdses[0]
                env_copy["_MACRO_NAME_IN"] = macro
                env_copy["_MAGIC_SCRIPT"] = os.path.join(
                    get_script_dir(), "magic", "get_bbox.tcl"
                )

                subprocess_result = super().run_subprocess(
                    self.get_command(),
                    env=env_copy,
                    log_to=os.path.join(self.step_dir, f"{macro}.get_bbox.log"),
                )
                generated_metrics = subprocess_result["generated_metrics"]

                if generated_metrics == {}:
                    raise StepError(
                        f"Failed to extract PR boundary from GDSII view of macro '{macro}'. Ensure that the GDSII view has a PR boundary layer."
                    )
                macro_gds.append([macro, macro_gdses, generated_metrics.values()])

            env["__MACRO_GDS"] = TclStep.value_to_tcl(macro_gds)

        views_updates, metrics_updates = super().run(
            state_in,
            env=env,
            **kwargs,
        )

        if self.config["PRIMARY_GDSII_STREAMOUT_TOOL"] == "magic":
            magic_gds_out = str(views_updates[DesignFormat.MAG_GDS])
            gds_path = os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.gds")
            shutil.copy(magic_gds_out, gds_path)
            views_updates[DesignFormat.GDS] = Path(gds_path)

        views_updates[DesignFormat.MAG] = Path(
            os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.mag")
        )

        return views_updates, metrics_updates


@Step.factory.register()
class DRC(MagicStep):
    """
    Performs `design rule checking <https://en.wikipedia.org/wiki/Design_rule_checking>`_
    on the GDSII stream using Magic.

    This also converts the results to a KLayout database, which can be loaded.

    The metrics will be updated with ``magic__drc_error__count``. You can use
    `the relevant checker <#Checker.MagicDRC>`_ to quit if that number is
    nonzero.
    """

    id = "Magic.DRC"
    name = "DRC"
    long_name = "Design Rule Checks"

    inputs = [DesignFormat.DEF, DesignFormat.GDS]
    outputs = []

    config_vars = MagicStep.config_vars + [
        Variable(
            "MAGIC_DRC_USE_GDS",
            bool,
            "A flag to choose whether to run the Magic DRC checks on GDS or not. If not, then the checks will be done on the DEF view of the design, which is a bit faster, but may be less accurate as some DEF/LEF elements are abstract.",
            default=True,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "magic", "drc.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)

        views_updates, metrics_updates = super().run(state_in, **kwargs)

        report_path = os.path.join(reports_dir, "drc_violations.magic.rpt")
        klayout_db_path = os.path.join(reports_dir, "drc_violations.magic.xml")

        # report_stats = os.stat(report_path)
        # drc_db_file = None
        # if report_stats.st_size >= 0:  # 134217728:
        #     drc_db_file = os.path.join(reports_dir, "drc.db")

        drc, bbox_count = DRCObject.from_magic(
            open(report_path, encoding="utf8"),
            # db_file=drc_db_file,
        )

        drc.to_klayout_xml(open(klayout_db_path, "wb"))

        metrics_updates["magic__drc_error__count"] = bbox_count

        return views_updates, metrics_updates


@Step.factory.register()
class SpiceExtraction(MagicStep):
    """
    Extracts a SPICE netlist from the GDSII stream. Used in Layout vs. Schematic
    checks.

    Also, the metrics will be updated with ``magic__illegal_overlap__count``. You can use
    `the relevant checker <#Checker.IllegalOverlap>`_ to quit if that number is
    nonzero.
    """

    id = "Magic.SpiceExtraction"
    name = "SPICE Extraction"
    long_name = "SPICE Model Extraction"

    inputs = [DesignFormat.GDS, DesignFormat.DEF]
    outputs = [DesignFormat.SPICE]

    config_vars = MagicStep.config_vars + [
        Variable(
            "MAGIC_EXT_USE_GDS",
            bool,
            "A flag to choose whether to use GDS for spice extraction or not. If not, then the extraction will be done using the DEF/LEF, which is faster.",
            default=False,
        ),
        Variable(
            "MAGIC_EXT_ABSTRACT_CELLS",
            Optional[List[str]],
            "A list of regular experssions which are matched against the cells of a "
            + "the design. Matches are abstracted (black-boxed) during SPICE extraction.",
        ),
        Variable(
            "MAGIC_NO_EXT_UNIQUE",
            bool,
            "Enables connections by label in LVS by skipping `extract unique` in Magic extractions.",
            default=False,
            deprecated_names=["LVS_CONNECT_BY_LABEL"],
        ),
        Variable(
            "MAGIC_EXT_SHORT_RESISTOR",
            bool,
            "Enables adding resistors to shorts- resolves LVS issues if more than one top-level pin is connected to the same net, but may increase runtime and break some designs. Proceed with caution.",
            default=False,
        ),
        Variable(
            "MAGIC_EXT_ABSTRACT",
            bool,
            "Extracts a SPICE netlist based on black-boxed standard cells and macros (basically, anything with a LEF) rather than transistors. An error will be thrown if both this and `MAGIC_EXT_USE_GDS` is set to ``True``.",
            default=False,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "magic", "extract_spice.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["MAGIC_EXT_USE_GDS"] and self.config["MAGIC_EXT_ABSTRACT"]:
            raise StepException(
                "'MAGIC_EXT_USE_GDS' and 'MAGIC_EXT_ABSTRACT' cannot be both set to 'True'. The step cannot run."
            )

        kwargs, env = self.extract_env(kwargs)

        env["MAGTYPE"] = "maglef" if self.config["MAGIC_EXT_ABSTRACT"] else "mag"

        views_updates, metrics_updates = super().run(state_in, env=env, **kwargs)

        cif_scale = Decimal(open(os.path.join(self.step_dir, "cif_scale.txt")).read())
        feedback_path = os.path.join(self.step_dir, "feedback.txt")
        try:
            se_feedback, _ = DRCObject.from_magic_feedback(
                open(feedback_path, encoding="utf8"),
                cif_scale,
                self.config["DESIGN_NAME"],
            )
            illegal_overlap_count = functools.reduce(
                lambda a, b: a + len(b.bounding_boxes),
                [
                    v
                    for v in se_feedback.violations.values()
                    if "Illegal overlap" in v.description
                ],
                0,
            )
            with open(os.path.join(self.step_dir, "feedback.xml"), "wb") as f:
                se_feedback.to_klayout_xml(f)
            metrics_updates["magic__illegal_overlap__count"] = illegal_overlap_count
        except ValueError as e:
            self.warn(
                f"Failed to convert SPICE extraction feedback to KLayout database format: {e}"
            )
            metrics_updates["magic__illegal_overlap__count"] = (
                open(feedback_path, encoding="utf8").read().count("Illegal overlap")
            )
        return views_updates, metrics_updates


@Step.factory.register()
class OpenGUI(MagicStep):
    """
    Opens the DEF view in the Magic GUI.
    """

    id = "Magic.OpenGUI"
    name = "Open In GUI"

    inputs = [DesignFormat.DEF]
    outputs = []

    config_vars = MagicStep.config_vars + [
        Variable(
            "MAGIC_GUI_USE_GDS",
            bool,
            "Whether to prioritize GDS (if found) when running this step.",
            default=True,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "magic", "open.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)

        env = self.prepare_env(env, state_in)
        env = self._reroute_env(env)

        if DesignFormat.GDS in state_in:
            env["CURRENT_GDS"] = self.value_to_tcl(state_in[DesignFormat.GDS])

        cmd = [
            "magic",
            "-rcfile",
            self.config["MAGICRC"],
            self.get_script_path(),
        ]

        # Not run_subprocess- need stdin, stdout, stderr to be accessible to the
        # user normally
        magic = subprocess.Popen(
            cmd,
            env=env,
            cwd=self.step_dir,
        )
        try:
            magic.wait()
        except KeyboardInterrupt:
            magic.send_signal(SIGKILL)

        return {}, {}
