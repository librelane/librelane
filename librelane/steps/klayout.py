# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
#
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
import sys
import site
import shlex
import shutil
import subprocess
from os.path import abspath
from base64 import b64encode
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional, List, Literal, Sequence, Tuple, Union

from .step import ViewsUpdate, MetricsUpdate, Step, StepError, StepException

from ..config import Variable
from ..logging import info
from ..state import DesignFormat, State
from ..common import Path, get_script_dir, mkdirp, _get_process_limit


DesignFormat(
    "klayout_gds",
    "klayout.gds",
    "GDSII Stream (KLayout)",
    alts=["KLAYOUT_GDS"],
).register()


class KLayoutStep(Step):
    config_vars = [
        Variable(
            "KLAYOUT_TECH",
            Path,
            "A path to the KLayout layer technology (.lyt) file.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_PROPERTIES",
            Path,
            "A path to the KLayout layer properties (.lyp) file.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_DEF_LAYER_MAP",
            Path,
            "A path to the KLayout LEF/DEF layer mapping (.map) file.",
            pdk=True,
        ),
    ]

    def run_pya_script(
        self,
        cmd: Sequence[Union[str, os.PathLike]],
        log_to: Optional[Union[str, os.PathLike]] = None,
        silent: bool = False,
        report_dir: Optional[Union[str, os.PathLike]] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        env = env or os.environ.copy()
        # Pass site packages
        python_path_elements = site.getsitepackages() + sys.path
        if current_pythonpath := env.get("PYTHONPATH"):
            python_path_elements.append(current_pythonpath)

        env["PYTHONPATH"] = ":".join(python_path_elements)
        return super().run_subprocess(cmd, log_to, silent, report_dir, env, **kwargs)

    def get_cli_args(
        self,
        *,
        layer_info: bool = True,
        include_lefs: bool = False,
        include_gds: bool = False,
    ) -> List[str]:
        result = []
        if layer_info:
            lyp = abspath(self.config["KLAYOUT_PROPERTIES"])
            lyt = abspath(self.config["KLAYOUT_TECH"])
            lym = abspath(self.config["KLAYOUT_DEF_LAYER_MAP"])
            if None in [lyp, lyt, lym]:
                raise StepError(
                    "Cannot open design in KLayout as the PDK does not appear to support KLayout."
                )
            result += ["--lyp", lyp, "--lyt", lyt, "--lym", lym]

        if include_lefs:
            tech_lefs = self.toolbox.filter_views(self.config, self.config["TECH_LEFS"])
            if len(tech_lefs) != 1:
                raise StepException(
                    "Misconfigured SCL: 'TECH_LEFS' must return exactly one Tech LEF for its default timing corner."
                )

            lef_args = [
                "--input-lef",
                abspath(tech_lefs[0]),
            ]

            for lef in self.config["CELL_LEFS"]:
                lef_args.append("--input-lef")
                lef_args.append(abspath(lef))

            macro_lefs = self.toolbox.get_macro_views(self.config, DesignFormat.LEF)
            for lef in macro_lefs:
                lef_args.append("--input-lef")
                lef_args.append(abspath(lef))

            if extra_lefs := self.config["EXTRA_LEFS"]:
                for lef in extra_lefs:
                    lef_args.append("--input-lef")
                    lef_args.append(abspath(lef))

            if io_pad_lefs := self.config["PAD_LEFS"]:
                for lef in io_pad_lefs:
                    lef_args.append("--input-lef")
                    lef_args.append(abspath(lef))

            result += lef_args

        if include_gds:
            gds_args: List[str] = []

            for gds in self.config["CELL_GDS"]:
                gds_args.append("--with-gds-file")
                gds_args.append(gds)

            for gds in self.toolbox.get_macro_views(self.config, DesignFormat.GDS):
                gds_args.append("--with-gds-file")
                gds_args.append(str(gds))

            if extra_gds := self.config["EXTRA_GDS"]:
                for gds in extra_gds:
                    gds_args.append("--with-gds-file")
                    gds_args.append(gds)

            if io_pads_gds := self.config["PAD_GDS"]:
                for gds in io_pads_gds:
                    gds_args.append("--with-gds-file")
                    gds_args.append(gds)

            result += gds_args

        return result


@Step.factory.register()
class Render(KLayoutStep):
    """
    Renders a PNG of the layout using KLayout.

    DEF is required as an input, but if a GDS-II view
    exists in the input state, it will be used instead.
    """

    id = "KLayout.Render"
    name = "Render Image (w/ KLayout)"

    inputs = [DesignFormat.DEF]
    outputs = []

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        input_view = state_in[DesignFormat.DEF]
        if gds := state_in.get(DesignFormat.GDS):
            input_view = gds

        assert isinstance(input_view, Path)

        self.run_pya_script(
            [
                sys.executable,
                os.path.join(get_script_dir(), "klayout", "render.py"),
                abspath(input_view),
                "--output",
                abspath(os.path.join(self.step_dir, "out.png")),
            ]
            + self.get_cli_args(include_lefs=True),
            silent=True,
        )

        return {}, {}


@Step.factory.register()
class StreamOut(KLayoutStep):
    """
    Converts DEF views into GDSII streams using KLayout.

    The PDK must support KLayout for this step to work, otherwise
    it will be skipped.

    If ``PRIMARY_GDSII_STREAMOUT_TOOL`` is set to ``"klayout"``, both GDS and KLAYOUT_GDS
    will be updated, and if set to another tool, only ``KLAYOUT_GDS`` will be
    updated.
    """

    id = "KLayout.StreamOut"
    name = "GDSII Stream Out (KLayout)"

    inputs = [DesignFormat.DEF]
    outputs = [DesignFormat.GDS, DesignFormat.KLAYOUT_GDS]

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_CONFLICT_RESOLUTION",
            Optional[
                Literal["AddToCell", "OverwriteCell", "RenameCell", "SkipNewCell"]
            ],
            "Specifies the conflict resolution if a cell name conflict arises.",
            default="RenameCell",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates: ViewsUpdate = {}

        klayout_gds_out = os.path.join(
            self.step_dir,
            f"{self.config['DESIGN_NAME']}.{DesignFormat.KLAYOUT_GDS.extension}",
        )
        kwargs, env = self.extract_env(kwargs)

        self.run_pya_script(
            [
                sys.executable,
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "stream_out.py",
                ),
                state_in[DesignFormat.DEF.id],
                "--output",
                abspath(klayout_gds_out),
                "--top",
                self.config["DESIGN_NAME"],
                "--conflict-resolution",
                self.config["KLAYOUT_CONFLICT_RESOLUTION"],
            ]
            + self.get_cli_args(include_lefs=True, include_gds=True),
            env=env,
        )

        views_updates[DesignFormat.KLAYOUT_GDS] = Path(klayout_gds_out)

        if self.config["PRIMARY_GDSII_STREAMOUT_TOOL"] == "klayout":
            gds_path = os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.gds")
            shutil.copy(klayout_gds_out, gds_path)
            views_updates[DesignFormat.GDS] = Path(gds_path)

        return views_updates, {}

    def layout_preview(self) -> Optional[str]:
        if self.state_out is None:
            return None
        assert self.toolbox is not None

        if image := self.toolbox.render_png(self.config, self.state_out):
            image_encoded = b64encode(image).decode("utf8")
            return f'<img src="data:image/png;base64,{image_encoded}" />'

        return None


@Step.factory.register()
class XOR(KLayoutStep):
    """
    Performs an XOR operation on the Magic and KLayout GDS views. The idea is:
    if there's any difference between the GDSII streams between the two tools,
    one of them have it wrong and that may lead to ambiguity.
    """

    id = "KLayout.XOR"
    name = "KLayout vs. Magic XOR"

    inputs = [
        DesignFormat.MAG_GDS,
        DesignFormat.KLAYOUT_GDS,
    ]
    outputs = []

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_XOR_THREADS",
            Optional[int],
            "Specifies number of threads used in the KLayout XOR check. If unset, this will be equal to your machine's thread count.",
        ),
        Variable(
            "KLAYOUT_XOR_IGNORE_LAYERS",
            Optional[List[str]],
            "KLayout layers to ignore during XOR operations.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_XOR_TILE_SIZE",
            Optional[int],
            "The tile size to parallelize the XOR process with.",
            pdk=True,
            units="µm",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        ignored = ""
        if ignore_list := self.config["KLAYOUT_XOR_IGNORE_LAYERS"]:
            ignored = ";".join(ignore_list)

        layout_a = state_in[DesignFormat.MAG_GDS]
        if layout_a is None:
            self.warn("No Magic stream-out has been performed. Skipping XOR process…")
            return {}, {}
        layout_b = state_in[DesignFormat.KLAYOUT_GDS]
        if layout_b is None:
            self.warn("No KLayout stream-out has been performed. Skipping XOR process…")
            return {}, {}

        assert isinstance(layout_a, Path)
        assert isinstance(layout_b, Path)

        kwargs, env = self.extract_env(kwargs)

        tile_size_options = []
        if tile_size := self.config["KLAYOUT_XOR_TILE_SIZE"]:
            tile_size_options += ["--tile-size", str(tile_size)]

        thread_count = self.config["KLAYOUT_XOR_THREADS"] or _get_process_limit()
        info(f"Running XOR with {thread_count} threads…")

        subprocess_result = self.run_subprocess(
            [
                "ruby",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xor.drc",
                ),
                "--output",
                abspath(os.path.join(self.step_dir, "xor.xml")),
                "--top",
                self.config["DESIGN_NAME"],
                "--threads",
                thread_count,
                "--ignore",
                ignored,
                abspath(layout_a),
                abspath(layout_b),
            ]
            + tile_size_options,
            env=env,
        )

        return {}, subprocess_result["generated_metrics"]


@Step.factory.register()
class DRC(KLayoutStep):
    """
    Runs DRC using KLayout.

    Unlike most steps, the KLayout scripts vary quite wildly by PDK. If a PDK
    is not supported by this step, it will simply be skipped.

    Currently, only sky130A and sky130B are supported.
    """

    id = "KLayout.DRC"
    name = "Design Rule Check (KLayout)"

    inputs = [
        DesignFormat.GDS,
    ]
    outputs = []

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_DRC_RUNSET",
            Optional[Path],
            "A path to KLayout DRC runset.",
            pdk=True,
            deprecated_names=["KLAYOUT_DRC_TECH_SCRIPT"],
        ),
        Variable(
            "KLAYOUT_DRC_OPTIONS",
            Optional[Dict[str, Union[bool, int, str]]],
            "Options passed directly to the KLayout DRC runset. They vary from one PDK to another.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_DRC_THREADS",
            Optional[int],
            "Specifies the number of threads to be used in KLayout DRC."
            + "If unset, this will be equal to your machine's thread count.",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metrics_updates: MetricsUpdate = {}
        if self.config["PDK"] in ["sky130A", "sky130B"]:
            metrics_updates = self.run_sky130(state_in, **kwargs)
        elif self.config["PDK"] in ["gf180mcuA", "gf180mcuB", "gf180mcuC", "gf180mcuD"]:
            metrics_updates = self.run_gf180mcu(state_in, **kwargs)
        elif self.config["PDK"] in ["ihp-sg13g2"]:
            metrics_updates = self.run_ihp_sg13g2(state_in, **kwargs)
        else:
            metrics_updates = self.run_generic(state_in, **kwargs)

        return {}, metrics_updates

    def run_generic(self, state_in: State, **kwargs) -> MetricsUpdate:
        kwargs, env = self.extract_env(kwargs)

        if not self.config["KLAYOUT_DRC_RUNSET"]:
            self.warn(
                f"KLAYOUT_DRC_RUNSET is unset. KLayout.DRC may not be supported for the {self.config['PDK']} PDK. This step will be skipped."
            )
            return {}

        drc_script_path = self.config["KLAYOUT_DRC_RUNSET"]

        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        lyrdb_report = os.path.join(reports_dir, "drc.klayout.lyrdb")
        json_report = os.path.join(reports_dir, "drc.klayout.json")

        input_view = state_in[DesignFormat.GDS]
        assert isinstance(input_view, Path)

        opts = []
        if self.config["KLAYOUT_DRC_OPTIONS"]:
            for k, v in self.config["KLAYOUT_DRC_OPTIONS"].items():
                opts.extend(
                    [
                        "-rd",
                        f"{k}={v}",
                    ]
                )

        threads = self.config["KLAYOUT_DRC_THREADS"] or str(_get_process_limit())
        if threads != "1":
            opts.extend(
                [
                    "-rd",
                    f"thr={threads}",
                    # Use "threads" if possible
                    "-rd",
                    f"threads={threads}",
                ]
            )

        info(f"Running KLayout DRC with {threads} threads…")

        self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                drc_script_path,
                "-rd",
                f"input={abspath(input_view)}",
                "-rd",
                f"topcell={self.config['DESIGN_NAME']}",
                "-rd",
                f"report={abspath(lyrdb_report)}",
                *opts,
            ]
        )

        subprocess_result = self.run_pya_script(
            [
                "python3",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xml_drc_report_to_json.py",
                ),
                f"--xml-file={abspath(lyrdb_report)}",
                f"--json-file={abspath(json_report)}",
                "--metric=klayout__drc_error__count",
            ],
            env=env,
            log_to=os.path.join(self.step_dir, "xml_drc_report_to_json.log"),
        )
        return subprocess_result["generated_metrics"]

    def run_sky130(self, state_in: State, **kwargs) -> MetricsUpdate:
        kwargs, env = self.extract_env(kwargs)
        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        drc_script_path = self.config["KLAYOUT_DRC_RUNSET"]
        lyrdb_report = os.path.join(reports_dir, "drc.klayout.lyrdb")
        json_report = os.path.join(reports_dir, "drc.klayout.json")
        feol = str(self.config["KLAYOUT_DRC_OPTIONS"]["feol"]).lower()
        beol = str(self.config["KLAYOUT_DRC_OPTIONS"]["beol"]).lower()
        floating_metal = str(
            self.config["KLAYOUT_DRC_OPTIONS"]["floating_metal"]
        ).lower()
        offgrid = str(self.config["KLAYOUT_DRC_OPTIONS"]["offgrid"]).lower()
        seal = str(self.config["KLAYOUT_DRC_OPTIONS"]["seal"]).lower()
        threads = self.config["KLAYOUT_DRC_THREADS"] or _get_process_limit()
        info(f"Running KLayout DRC with {threads} threads…")

        input_view = state_in[DesignFormat.GDS]
        assert isinstance(input_view, Path)

        # Not pya script - DRC script is not part of LibreLane
        self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                drc_script_path,
                "-rd",
                f"input={abspath(input_view)}",
                "-rd",
                f"topcell={self.config['DESIGN_NAME']}",
                "-rd",
                f"report={abspath(lyrdb_report)}",
                "-rd",
                f"feol={feol}",
                "-rd",
                f"beol={beol}",
                "-rd",
                f"floating_metal={floating_metal}",
                "-rd",
                f"offgrid={offgrid}",
                "-rd",
                f"seal={seal}",
                "-rd",
                f"threads={threads}",
            ],
            env=env,
        )

        subprocess_result = self.run_pya_script(
            [
                "python3",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xml_drc_report_to_json.py",
                ),
                f"--xml-file={abspath(lyrdb_report)}",
                f"--json-file={abspath(json_report)}",
                "--metric=klayout__drc_error__count",
            ],
            env=env,
            log_to=os.path.join(self.step_dir, "xml_drc_report_to_json.log"),
        )
        return subprocess_result["generated_metrics"]

    def run_gf180mcu(self, state_in: State, **kwargs) -> MetricsUpdate:
        kwargs, env = self.extract_env(kwargs)

        if not self.config["KLAYOUT_DRC_RUNSET"]:
            self.warn(
                f"KLAYOUT_DRC_RUNSET is unset. KLayout.DRC may not be supported for the {self.config['PDK']} PDK. This step will be skipped."
            )
            return {}

        drc_script_path = self.config["KLAYOUT_DRC_RUNSET"]

        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        lyrdb_report = os.path.join(reports_dir, "drc.klayout.lyrdb")
        json_report = os.path.join(reports_dir, "drc.klayout.json")

        input_view = state_in[DesignFormat.GDS]
        assert isinstance(input_view, Path)

        opts = []
        if self.config["KLAYOUT_DRC_OPTIONS"]:
            for k, v in self.config["KLAYOUT_DRC_OPTIONS"].items():
                opts.extend(
                    [
                        "-rd",
                        f"{k}={v}",
                    ]
                )

        threads = self.config["KLAYOUT_DRC_THREADS"] or str(_get_process_limit())
        if threads != "1":
            opts.extend(
                [
                    "-rd",
                    f"thr={threads}",
                ]
            )

        info(f"Running KLayout DRC with {threads} threads…")

        # Not pya script - DRC script is not part of OpenLane
        self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                drc_script_path,
                "-rd",
                f"input={abspath(input_view)}",
                "-rd",
                f"topcell={self.config['DESIGN_NAME']}",
                "-rd",
                f"report={abspath(lyrdb_report)}",
                *opts,
            ]
        )

        subprocess_result = self.run_pya_script(
            [
                "python3",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xml_drc_report_to_json.py",
                ),
                f"--xml-file={abspath(lyrdb_report)}",
                f"--json-file={abspath(json_report)}",
                "--metric=klayout__drc_error__count",
            ],
            env=env,
            log_to=os.path.join(self.step_dir, "xml_drc_report_to_json.log"),
        )
        return subprocess_result["generated_metrics"]

    def run_ihp_sg13g2(self, state_in: State, **kwargs) -> MetricsUpdate:
        kwargs, env = self.extract_env(kwargs)

        drc_script_path = self.config["KLAYOUT_DRC_RUNSET"]

        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        lyrdb_report = os.path.join(reports_dir, "drc.klayout.lyrdb")
        json_report = os.path.join(reports_dir, "drc.klayout.json")

        input_view = state_in[DesignFormat.GDS]
        assert isinstance(input_view, Path)

        opts = []
        if self.config["KLAYOUT_DRC_OPTIONS"]:
            for k, v in self.config["KLAYOUT_DRC_OPTIONS"].items():
                opts.extend(
                    [
                        "-rd",
                        f"{k}={v}",
                    ]
                )

        threads = self.config["KLAYOUT_DRC_THREADS"] or str(_get_process_limit())
        if threads != "1":
            opts.extend(
                [
                    "-rd",
                    f"thr={threads}",
                ]
            )

        info(f"Running KLayout DRC with {threads} threads…")

        # Not pya script - DRC script is not part of OpenLane
        self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                drc_script_path,
                "-rd",
                f"input={abspath(input_view)}",
                "-rd",
                f"topcell={self.config['DESIGN_NAME']}",
                "-rd",
                f"report={abspath(lyrdb_report)}",
                *opts,
            ]
        )

        subprocess_result = self.run_pya_script(
            [
                "python3",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xml_drc_report_to_json.py",
                ),
                f"--xml-file={abspath(lyrdb_report)}",
                f"--json-file={abspath(json_report)}",
                "--metric=klayout__drc_error__count",
            ],
            env=env,
            log_to=os.path.join(self.step_dir, "xml_drc_report_to_json.log"),
        )
        return subprocess_result["generated_metrics"]


@Step.factory.register()
class LVS(KLayoutStep):
    id = "KLayout.LVS"
    name = "Layout Versus Schematic (KLayout)"

    inputs = [
        DesignFormat.CDL,
        DesignFormat.GDS,
    ]
    outputs = [DesignFormat.SPICE]

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_LVS_SCRIPT",
            Optional[Path],
            "A path to KLayout LVS script.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_LVS_OPTIONS",
            Optional[Dict[str, Union[bool, int, str]]],
            "Options passed directly to the KLayout LVS script. They vary from one PDK to another.",
            pdk=True,
        ),
    ]

    def run_ihp_sg13g2(
        self, state_in: State, **kwargs
    ) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)

        lvs_script_path = self.config["KLAYOUT_LVS_SCRIPT"]

        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        lvsdb_report = os.path.join(reports_dir, "lvs.klayout.lvsdb")

        input_view_gds = state_in[DesignFormat.GDS]
        input_view_cdl = state_in[DesignFormat.CDL]
        assert isinstance(input_view_gds, Path)
        assert isinstance(input_view_cdl, Path)

        output_spice = os.path.join(
            self.step_dir,
            f"{self.config['DESIGN_NAME']}.{DesignFormat.SPICE.value.extension}",
        )

        with NamedTemporaryFile("w") as f:
            # Merge all CDL inputs
            cdl_lst = [input_view_cdl]
            cdl_lst.extend(self.config["CELL_CDLS"] or [])
            cdl_lst.extend(self.config["EXTRA_CDLS"] or [])
            cdl_lst.extend(self.config["PAD_CDLS"] or [])

            for fn in cdl_lst:
                with open(fn, "r") as cdl_fh:
                    f.write(cdl_fh.read())

            opts = []
            if self.config["KLAYOUT_LVS_OPTIONS"]:
                for k, v in self.config["KLAYOUT_LVS_OPTIONS"].items():
                    opts.extend(
                        [
                            "-rd",
                            f"{k}={v}",
                        ]
                    )

            # Not pya script - LVS script is not part of LibreLane
            subprocess_result = self.run_subprocess(
                [
                    "klayout",
                    "-b",
                    "-zz",
                    "-r",
                    lvs_script_path,
                    "-rd",
                    f"input={abspath(input_view_gds)}",
                    "-rd",
                    f"schematic={abspath(f.name)}",
                    "-rd",
                    f"report={abspath(lvsdb_report)}",
                    "-rd",
                    f"target_netlist={abspath(output_spice)}",
                ]
                + opts,
                env=env,
            )

            with open(subprocess_result["log_path"]) as fh:
                for line in fh:
                    if "INFO : Congratulations! Netlists match" in line:
                        ok = True
                        break
                    elif "ERROR : Netlists don't match" in line:
                        ok = False
                        break
                else:
                    ok = False

        views_updates: ViewsUpdate = {
            DesignFormat.SPICE: Path(output_spice),
        }
        metrics_updates: MetricsUpdate = {
            "design__lvs_error__count": 0 if ok else 1,
        }

        return views_updates, metrics_updates

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metrics_updates: MetricsUpdate = {}
        views_updates: ViewsUpdate = {}
        if self.config["PDK"] in ["ihp-sg13g2"]:
            views_updates, metrics_updates = self.run_ihp_sg13g2(state_in, **kwargs)
        else:
            self.warn(
                f"KLayout LVS is not supported for the {self.config['PDK']} PDK. This step will be skipped."
            )

        return views_updates, metrics_updates


@Step.factory.register()
class SealRing(KLayoutStep):
    """
    Adds a seal ring in the correct size to the GDS.
    """

    id = "KLayout.SealRing"
    name = "Seal Ring Generation"

    inputs = [DesignFormat.GDS]
    outputs = [DesignFormat.GDS]

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_SEALRING_SCRIPT",
            Optional[Path],
            "A path to KLayout seal ring script.",
            pdk=True,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metrics_updates: MetricsUpdate = {}
        views_updates: ViewsUpdate = {}
        if self.config["PDK"] in ["ihp-sg13g2"]:
            views_updates, metrics_updates = self.run_ihp_sg13g2(state_in, **kwargs)
        else:
            views_updates, metrics_updates = self.run_generic(state_in, **kwargs)

        return views_updates, metrics_updates

    def run_generic(
        self, state_in: State, **kwargs
    ) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates: ViewsUpdate = {}
        kwargs, env = self.extract_env(kwargs)

        if not self.config["KLAYOUT_SEALRING_SCRIPT"]:
            self.warn(
                f"KLAYOUT_SEALRING_SCRIPT is unset. KLayout.SealRing may not be supported for the {self.config['PDK']} PDK. This step will be skipped."
            )
            return views_updates, {}

        input_gds = state_in[DesignFormat.GDS]
        assert isinstance(input_gds, Path)
        output_gds = os.path.join(
            self.step_dir, f"{self.config['DESIGN_NAME']}.{DesignFormat.GDS.extension}"
        )

        script = self.config["KLAYOUT_SEALRING_SCRIPT"]

        env["PDK_ROOT"] = self.config["PDK_ROOT"]
        env["PDK"] = self.config["PDK"]

        self.run_pya_script(
            [
                "python3",
                script,
                "--input",
                abspath(input_gds),
                "--output",
                abspath(output_gds),
                "--die-width",
                f"{self.config['DIE_AREA'][2]:f}",
                "--die-height",
                f"{self.config['DIE_AREA'][3]:f}",
            ],
            env=env,
        )

        views_updates[DesignFormat.GDS] = Path(output_gds)

        return views_updates, {}

    def run_ihp_sg13g2(
        self, state_in: State, **kwargs
    ) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates: ViewsUpdate = {}
        kwargs, env = self.extract_env(kwargs)

        input_gds = state_in[DesignFormat.GDS]
        assert isinstance(input_gds, Path)
        output_gds = os.path.join(
            self.step_dir, f"{self.config['DESIGN_NAME']}.{DesignFormat.GDS.extension}"
        )

        script = self.config["KLAYOUT_SEALRING_SCRIPT"]

        env["PDK_ROOT"] = self.config["PDK_ROOT"]
        env["PDK"] = self.config["PDK"]

        # Set KLAYOUT_PATH so that KLayout can load the technology definition
        env["KLAYOUT_PATH"] = os.path.join(
            self.config["PDK_ROOT"], self.config["PDK"], "libs.tech", "klayout"
        )

        self.run_subprocess(
            [
                "klayout",
                "-zz",
                "-nc",
                "-n",
                "sg13g2",
                "-r",
                script,
                "-rd",
                f"width={self.config['DIE_AREA'][3]:f}",
                "-rd",
                f"height={self.config['DIE_AREA'][2]:f}",
                "-rd",
                f"input={abspath(input_gds)}",
                "-rd",
                f"output={abspath(output_gds)}",
            ],
            env=env,
        )

        views_updates[DesignFormat.GDS] = Path(output_gds)

        return views_updates, {}


@Step.factory.register()
class Filler(KLayoutStep):
    """
    Generates the filler cells according to the design rules and adds them to the GDS.
    """

    id = "KLayout.Filler"
    name = "Filler Generation"

    inputs = [DesignFormat.GDS]
    outputs = [DesignFormat.GDS]

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_FILLER_SCRIPT",
            Optional[Path],
            "A path to KLayout filler script.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_FILLER_OPTIONS",
            Optional[Dict[str, Union[bool, int, str]]],
            "Options passed directly to the KLayout filler script. They vary from one PDK to another.",
            pdk=True,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metrics_updates: MetricsUpdate = {}
        views_updates: ViewsUpdate = {}
        if self.config["PDK"] in ["ihp-sg13g2"]:
            views_updates, metrics_updates = self.run_ihp_sg13g2(state_in, **kwargs)
        else:
            views_updates, metrics_updates = self.run_generic(state_in, **kwargs)

        return views_updates, metrics_updates

    def run_generic(
        self, state_in: State, **kwargs
    ) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates: ViewsUpdate = {}
        kwargs, env = self.extract_env(kwargs)

        if not self.config["KLAYOUT_FILLER_SCRIPT"]:
            self.warn(
                f"KLAYOUT_FILLER_SCRIPT is unset. KLayout.Filler may not be supported for the {self.config['PDK']} PDK. This step will be skipped."
            )
            return views_updates, {}

        input_gds = state_in[DesignFormat.GDS]
        assert isinstance(input_gds, Path)
        output_gds = os.path.join(
            self.step_dir, f"{self.config['DESIGN_NAME']}.{DesignFormat.GDS.extension}"
        )

        script = self.config["KLAYOUT_FILLER_SCRIPT"]

        opts = []
        if self.config["KLAYOUT_FILLER_OPTIONS"]:
            for k, v in self.config["KLAYOUT_FILLER_OPTIONS"].items():
                opts.extend(
                    [
                        "-rd",
                        f"{k}={v}",
                    ]
                )

        self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                script,
                "-rd",
                f"input={abspath(input_gds)}",
                "-rd",
                f"output={abspath(output_gds)}",
                *opts,
            ],
            env=env,
        )

        views_updates[DesignFormat.GDS] = Path(output_gds)

        return views_updates, {}

    def run_ihp_sg13g2(
        self, state_in: State, **kwargs
    ) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates: ViewsUpdate = {}
        kwargs, env = self.extract_env(kwargs)

        input_gds = state_in[DesignFormat.GDS]
        assert isinstance(input_gds, Path)
        output_gds = os.path.join(
            self.step_dir, f"{self.config['DESIGN_NAME']}.{DesignFormat.GDS.extension}"
        )

        script = self.config["KLAYOUT_FILLER_SCRIPT"]

        env["PDK_ROOT"] = self.config["PDK_ROOT"]
        env["PDK"] = self.config["PDK"]

        self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                script,
                "-rd",
                f"output_file={abspath(output_gds)}",
                abspath(input_gds),
            ],
            env=env,
        )

        views_updates[DesignFormat.GDS] = Path(output_gds)

        return views_updates, {}


@Step.factory.register()
class Density(KLayoutStep):
    """
    Runs the density check on the GDS.
    """

    id = "KLayout.Density"
    name = "Density Check"

    inputs = [DesignFormat.GDS]
    outputs = []

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_DENSITY_RUNSET",
            Optional[Path],
            "A path to KLayout density runset.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_DENSITY_OPTIONS",
            Optional[Dict[str, Union[bool, int, str]]],
            "Options passed directly to the KLayout density runset. They vary from one PDK to another.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_DENSITY_THREADS",
            Optional[int],
            "Specifies the number of threads to be used in KLayout density check."
            + "If unset, this will be equal to your machine's thread count.",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metrics_updates: MetricsUpdate = {}
        views_updates: ViewsUpdate = {}

        metrics_updates = self.run_generic(state_in, **kwargs)

        return views_updates, metrics_updates

    def run_generic(self, state_in: State, **kwargs) -> MetricsUpdate:
        kwargs, env = self.extract_env(kwargs)

        if not self.config["KLAYOUT_DENSITY_RUNSET"]:
            self.warn(
                f"KLAYOUT_DENSITY_RUNSET is unset. KLayout.Density may not be supported for the {self.config['PDK']} PDK. This step will be skipped."
            )
            return {}

        input_gds = state_in[DesignFormat.GDS]
        assert isinstance(input_gds, Path)

        script = self.config["KLAYOUT_DENSITY_RUNSET"]

        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        lyrdb_report = os.path.join(reports_dir, "density.klayout.lyrdb")
        json_report = os.path.join(reports_dir, "density.klayout.json")

        opts = []
        if self.config["KLAYOUT_DENSITY_OPTIONS"]:
            for k, v in self.config["KLAYOUT_DENSITY_OPTIONS"].items():
                opts.extend(
                    [
                        "-rd",
                        f"{k}={v}",
                    ]
                )

        threads = self.config["KLAYOUT_DENSITY_THREADS"] or str(_get_process_limit())
        if threads != "1":
            opts.extend(
                [
                    "-rd",
                    f"thr={threads}",
                ]
            )

        info(f"Running KLayout density check with {threads} threads…")

        # Not a pya script
        subprocess_result = self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                script,
                "-rd",
                f"input={abspath(input_gds)}",
                "-rd",
                f"topcell={self.config['DESIGN_NAME']}",
                "-rd",
                f"report={abspath(lyrdb_report)}",
            ]
            + opts,
            env=env,
        )

        subprocess_result = self.run_pya_script(
            [
                "python3",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xml_drc_report_to_json.py",
                ),
                f"--xml-file={abspath(lyrdb_report)}",
                f"--json-file={abspath(json_report)}",
                "--metric=klayout__density_error__count",
            ],
            env=env,
            log_to=os.path.join(self.step_dir, "xml_drc_report_to_json.log"),
        )
        return subprocess_result["generated_metrics"]


@Step.factory.register()
class Antenna(KLayoutStep):
    """
    Runs the antenna check on the GDS.
    """

    id = "KLayout.Antenna"
    name = "Antenna Check"

    inputs = [DesignFormat.GDS]
    outputs = []

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_ANTENNA_RUNSET",
            Optional[Path],
            "A path to KLayout antenna runset.",
            pdk=True,
        ),
        Variable(
            "KLAYOUT_ANTENNA_OPTIONS",
            Optional[Dict[str, Union[bool, int, str]]],
            "Options passed directly to the KLayout density runset. They vary from one PDK to another.",
            pdk=True,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        metrics_updates: MetricsUpdate = {}
        views_updates: ViewsUpdate = {}

        metrics_updates = self.run_generic(state_in, **kwargs)

        return views_updates, metrics_updates

    def run_generic(self, state_in: State, **kwargs) -> MetricsUpdate:
        kwargs, env = self.extract_env(kwargs)

        if not self.config["KLAYOUT_ANTENNA_RUNSET"]:
            self.warn(
                f"KLAYOUT_ANTENNA_RUNSET is unset. KLayout.Antenna may not be supported for the {self.config['PDK']} PDK. This step will be skipped."
            )
            return {}

        input_gds = state_in[DesignFormat.GDS]
        assert isinstance(input_gds, Path)

        script = self.config["KLAYOUT_ANTENNA_RUNSET"]

        reports_dir = os.path.join(self.step_dir, "reports")
        mkdirp(reports_dir)
        lyrdb_report = os.path.join(reports_dir, "antenna.klayout.lyrdb")
        json_report = os.path.join(reports_dir, "antenna.klayout.json")

        opts = []
        if self.config["KLAYOUT_ANTENNA_OPTIONS"]:
            for k, v in self.config["KLAYOUT_ANTENNA_OPTIONS"].items():
                opts.extend(
                    [
                        "-rd",
                        f"{k}={v}",
                    ]
                )

        info("Running KLayout antenna check…")

        # Not a pya script
        subprocess_result = self.run_subprocess(
            [
                "klayout",
                "-b",
                "-zz",
                "-r",
                script,
                "-rd",
                f"input={abspath(input_gds)}",
                "-rd",
                f"topcell={self.config['DESIGN_NAME']}",
                "-rd",
                f"report={abspath(lyrdb_report)}",
            ]
            + opts,
            env=env,
        )

        subprocess_result = self.run_pya_script(
            [
                "python3",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "xml_drc_report_to_json.py",
                ),
                f"--xml-file={abspath(lyrdb_report)}",
                f"--json-file={abspath(json_report)}",
                "--metric=klayout__antenna_error__count",
            ],
            env=env,
            log_to=os.path.join(self.step_dir, "xml_drc_report_to_json.log"),
        )
        return subprocess_result["generated_metrics"]


@Step.factory.register()
class OpenGUI(KLayoutStep):
    """
    Opens the DEF view in the KLayout GUI, with layers loaded and mapped
    properly. Useful to inspect ``.klayout.xml`` database files and the like.
    """

    id = "KLayout.OpenGUI"
    name = "Open In GUI"

    inputs = [DesignFormat.DEF]
    outputs = []

    config_vars = KLayoutStep.config_vars + [
        Variable(
            "KLAYOUT_EDITOR_MODE",
            bool,
            "Whether to run the KLayout GUI in editor mode or in viewer mode.",
            default=False,
        ),
        Variable(
            "KLAYOUT_GUI_USE_GDS",
            bool,
            "Whether to prioritize GDS (if found) when running this step.",
            default=True,
            deprecated_names=["KLAYOUT_PRIORITIZE_GDS"],
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        mode_args = []
        if self.config["KLAYOUT_EDITOR_MODE"]:
            mode_args.append("--editor")

        layout = state_in[DesignFormat.DEF]
        if self.config["KLAYOUT_GUI_USE_GDS"]:
            if gds := state_in.get(DesignFormat.GDS):
                layout = gds
        assert isinstance(layout, Path)

        env["KLAYOUT_ARGV"] = shlex.join(
            [
                abspath(layout),
            ]
            + self.get_cli_args(include_lefs=True)
        )

        cmd = (
            [
                shutil.which("klayout") or "klayout",
            ]
            + mode_args
            + [
                "-rm",
                os.path.join(
                    get_script_dir(),
                    "klayout",
                    "open_design.py",
                ),
            ]
        )

        # Not run_subprocess- need stdin, stdout, stderr to be accessible to the
        # user normally
        subprocess.check_call(
            cmd,
            env=env,
            cwd=self.step_dir,
        )

        return {}, {}
