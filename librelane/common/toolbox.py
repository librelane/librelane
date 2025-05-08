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
import uuid
import shutil
import tempfile
import subprocess
from enum import IntEnum
from decimal import Decimal
from functools import lru_cache
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    List,
    Union,
)

import libparse
from deprecated.sphinx import deprecated


from .misc import mkdirp, gzopen
from .types import Path
from .metrics import aggregate_metrics
from .generic_dict import GenericImmutableDict, is_string
from ..state import DesignFormat
from ..common import Filter
from ..logging import debug, warn, err


class Toolbox(object):
    """
    An assisting object shared by a Flow and all its constituent Steps.

    The toolbox may create artifacts that are cached to avoid constant re-creation
    between steps.
    """

    def __init__(self, tmp_dir: str) -> None:
        # Only create before use, otherwise users will end up with
        # "librelane_run/tmp" created in their PWD because of the global toolbox
        self.tmp_dir = tmp_dir

        self.remove_cells_from_lib = lru_cache(16, True)(self.remove_cells_from_lib)  # type: ignore
        self.create_blackbox_model = lru_cache(16, True)(self.create_blackbox_model)  # type: ignore

    @deprecated(
        version="2.0.0b1",
        reason="Use 'aggregate_metrics' from 'librelane.common'",
        action="once",
    )
    def aggregate_metrics(
        self,
        input: Dict[str, Any],
        aggregator_by_metric: Dict[str, Tuple[Any, Callable[[Iterable], Any]]],
    ) -> Dict[str, Any]:
        return aggregate_metrics(input, aggregator_by_metric)

    def filter_views(
        self,
        config: Mapping[str, Any],
        views_by_corner: Mapping[str, Union[Path, Iterable[Path]]],
        timing_corner: Optional[str] = None,
    ) -> List[Path]:
        """
        Given a mapping from (wildcards of) corner names to views, this function
        enumerates all views matching either the default timing corner or
        an explicitly-provided override.

        :param config: The configuration. Used solely to extract the default
            corner.
        :param views_by_corner: The mapping from (wild cards) of corner names to
            views.
        :param corner: An explicit override for the default corner. Must be a
            fully qualified IPVT corner.
        :returns: The created list
        """
        timing_corner = timing_corner or config["DEFAULT_CORNER"]
        result: List[Path] = []

        for key in Filter(views_by_corner).get_matching_wildcards(timing_corner):
            value = views_by_corner[key]
            if is_string(value):
                result += [value]  # type: ignore
            else:
                result += list(value)  # type: ignore

        return result

    def get_macro_views(
        self,
        config: Mapping[str, Any],
        view: DesignFormat,
        timing_corner: Optional[str] = None,
        unless_exist: Union[None, DesignFormat, Sequence[DesignFormat]] = None,
    ) -> List[Path]:
        """
        For :class:`Config` objects (or similar Mappings) that have Macro
        information, this function gets all Macro views matching a certain
        :class:`DesignFormat` for either the default timing corner or an
        explicitly-provided override.

        :param config: The configuration.
        :param view: The design format to return views of.
        :param timing_corner: An explicit override for the default corner set
            by the configuration.
        :param corner: An explicit override for the default corner. Must be a
            fully qualified IPVT corner.
        :param unless_exist: If a Macro also has a view for these
            ``DesignFormat``\\s, do not return a result for the requested
            ``DesignFormat``\\.

            Useful for if you want to return say, Netlists if reliable LIB files
            do not exist.
        :returns: A list of the Macro views matched by the process described
            above.
        """
        from ..config import Macro

        timing_corner = timing_corner or config["DEFAULT_CORNER"]
        macros = config["MACROS"]
        result: List[Path] = []

        if macros is None:
            return result

        unless_exist = unless_exist or []
        if isinstance(unless_exist, DesignFormat):
            unless_exist = [unless_exist]

        for module, macro in macros.items():
            if not isinstance(macro, Macro):
                raise TypeError(
                    f"Misconstructed configuration: macro definition for key {module} is not of type 'Macro'."
                )

            views = macro.view_by_df(view)
            if views is None:
                continue

            alt_views: List[Path] = []
            for alternate_format in unless_exist:
                entry = macro.view_by_df(alternate_format)
                if entry is not None:
                    current = entry
                    if isinstance(current, dict):
                        current = self.filter_views(config, current, timing_corner)
                    elif not isinstance(current, list):
                        current = [current]
                    alt_views += current

            if len(alt_views) != 0:
                continue

            if isinstance(views, dict):
                views_filtered = self.filter_views(config, views, timing_corner)
                result += views_filtered
            elif isinstance(views, list):
                result += views
            elif views is not None:
                result += [Path(views)]

        return [element for element in result if str(element) != Path._dummy_path]

    def get_macro_views_by_priority(
        self,
        config: Mapping[str, Any],
        design_formats: Sequence[DesignFormat],
        timing_corner: Optional[str] = None,
    ) -> List[Tuple[Path, DesignFormat]]:
        result: List[Tuple[Path, DesignFormat]] = []
        formats_so_far: List[DesignFormat] = []
        for format in design_formats:
            views = self.get_macro_views(
                config,
                format,
                unless_exist=formats_so_far,
                timing_corner=timing_corner,
            )
            for view in views:
                result.append((view, format))
            formats_so_far.append(format)
        return result

    def get_timing_files_categorized(
        self,
        config: Mapping[str, Any],
        timing_corner: Optional[str] = None,
        prioritize_nl: bool = False,
    ) -> Tuple[str, List[Path], List[Path], List[Tuple[str, Path]]]:
        """
        Returns the lib files for a given configuration and timing corner.

        :param config: A configuration object or a similar mapping.
        :param timing_corner:
            A fully qualified IPVT corner to get SCL libs for.

            If not specified, the value for ``DEFAULT_CORNER`` from the SCL will
            be used.
        :param prioritize_nl:
            Do not return lib files for macros that have gate-Level Netlists and
            SPEF views.

            If set to ``false``\\, only lib files are returned.
        :returns: A tuple of:
            * The name of the timing corner
            * A list of lib files
            * A list of netlists
            * A list of tuples of instances and SPEFs
        """
        from ..config import Macro

        timing_corner = timing_corner or config["DEFAULT_CORNER"]

        all_libs: List[Path] = self.filter_views(config, config["LIB"], timing_corner)
        if len(all_libs) == 0:
            warn(f"No SCL lib files found for {timing_corner}.")

        all_netlists: List[Path] = []
        all_spefs: List[Tuple[str, Path]] = []

        macros = config["MACROS"]
        if macros is None:
            macros = {}

        for module, macro in macros.items():
            if not isinstance(macro, Macro):
                raise TypeError(
                    f"Misconstructed configuration: macro definition for key {module} is not of type 'Macro'."
                )
            if prioritize_nl:
                netlists = macro.nl
                if isinstance(netlists, Path):
                    netlists = [netlists]

                spefs = self.filter_views(
                    config,
                    macro.spef,
                    timing_corner,
                )
                if len(netlists) and not len(spefs):
                    warn(
                        f"Netlists found for macro {module}, but no parasitics extraction found at corner {timing_corner}. The netlist cannot be used for timing on this module."
                    )
                elif len(spefs) and not len(netlists):
                    warn(
                        f"Parasitics extraction(s) found for macro {module} at corner {timing_corner}, but no netlist found. The parasitics cannot be used for timing on this module."
                    )
                elif len(spefs) and len(netlists):
                    debug(f"Adding {[netlists + spefs]} to timing info…")
                    all_netlists += netlists
                    for spef in spefs:
                        for instance in macro.instances:
                            all_spefs.append((instance, spef))
                    continue
            # NL/SPEF not prioritized or not found
            libs = self.filter_views(
                config,
                macro.lib,
                timing_corner,
            )
            if not len(libs):
                warn(
                    f"No libs found for macro {module} at corner {timing_corner}. The module will be black-boxed."
                )
                continue
            debug(f"Adding {libs} to timing info…")
            all_libs += libs

        return (timing_corner, all_libs, all_netlists, all_spefs)

    def get_timing_files(
        self,
        config: Mapping[str, Any],
        timing_corner: Optional[str] = None,
        prioritize_nl: bool = False,
    ) -> Tuple[str, List[str]]:
        """
        Returns the lib files for a given configuration and timing corner.

        :param config: A configuration object or a similar mapping.
        :param timing_corner:
            A fully qualified IPVT corner to get SCL libs for.

            If not specified, the value for ``DEFAULT_CORNER`` from the SCL will
            be used.
        :param prioritize_nl:
            Do not return lib files for macros that have gate-Level Netlists and
            SPEF views.

            If set to ``false``\\, only lib files are returned.
        :returns: A tuple of:

            * The name of the timing corner
            * A heterogeneous list of files composed of: Lib files are returned as-is,
              Netlists are returned as-is, and SPEF files are returned in the
              format ``{instance_name}@{spef_path}``\\.

            It is left up to the step or tool to process this list as they see
            fit.
        """

        timing_corner, libs, netlists, spefs = self.get_timing_files_categorized(
            config=config,
            timing_corner=timing_corner,
            prioritize_nl=prioritize_nl,
        )
        results = [str(path) for path in libs + netlists]
        for instance, spef in spefs:
            results.append(f"{instance}@{spef}")
        return (timing_corner, results)

    def render_png(
        self,
        config: GenericImmutableDict[str, Any],
        state_in: GenericImmutableDict[str, Any],
    ) -> Optional[bytes]:  # pragma: no cover
        try:
            from ..steps import KLayout, StepError
            from ..config import Config, InvalidConfig
            from ..state import State

            # I'm too damn tired to figure out a way to forward-declare those two,
            # have fun if you want to
            if not isinstance(config, Config):
                raise TypeError("parameter config must be of type Config")

            if not isinstance(state_in, State):
                raise TypeError("parameter state_in must be of type State")

            with tempfile.TemporaryDirectory(prefix="librelane_klayout_tmp_") as d:
                render_step = KLayout.Render(config, state_in, _config_quiet=True)
                render_step.start(self, d)
                return open(os.path.join(d, "out.png"), "rb").read()
        except InvalidConfig:
            warn("PDK is incompatible with KLayout. Unable to generate preview.")
            return None
        except StepError as e:
            warn(f"Failed to generate preview: {e}.")
            return None

    def remove_cells_from_lib(
        self,
        input_lib_files: FrozenSet[str],
        excluded_cells: FrozenSet[str],
    ) -> List[str]:
        """
        Creates a new lib file with some cells removed.

        This function is memoized, i.e., results are cached for a specific set
        of inputs.

        :param input_lib_files: A `frozenset` of input lib files.
        :param excluded_cells: A `frozenset` of wildcards of cells to remove
            from the files.
        :returns: A path to the lib file with the removed cells.
        """
        mkdirp(self.tmp_dir)

        class State(IntEnum):
            initial = 0
            cell = 10
            excluded_cell = 11

        cell_start_rx = re.compile(r"(\s*)cell\s*\(\"?(.*?)\"?\)\s*\{")
        out_paths = []

        excluded_cells_filter = Filter(excluded_cells)

        for file in input_lib_files:
            input_lib_stream = gzopen(file)
            # can't be gzip -- abc cannot read gzipped lib files
            out_path = os.path.join(self.tmp_dir, f"{uuid.uuid4().hex}.lib")

            state = State.initial
            brace_count = 0
            output_file_handle = open(out_path, "w")
            write = lambda x: print(x, file=output_file_handle, end="")
            for line in input_lib_stream:
                if state == State.initial:
                    cell_m = cell_start_rx.search(line)
                    if cell_m is not None:
                        whitespace = cell_m[1]
                        cell_name = cell_m[2]
                        if excluded_cells_filter.match(cell_name):
                            state = State.excluded_cell
                            write(f"{whitespace}/* removed {cell_name} */\n")
                        else:
                            state = State.cell
                            write(line)
                        brace_count = 1
                    else:
                        write(line)
                elif state in [State.cell, State.excluded_cell]:
                    if "{" in line:
                        brace_count += 1
                    if "}" in line:
                        brace_count -= 1
                    if state == State.cell:
                        write(line)
                    if brace_count == 0:
                        state = State.initial

            output_file_handle.close()

            out_paths.append(out_path)

        return out_paths

    def create_blackbox_model(
        self,
        input_models: Union[frozenset, Tuple[str, ...]],
        defines: FrozenSet[str],
    ) -> str:
        mkdirp(self.tmp_dir)
        out_path = os.path.join(self.tmp_dir, f"{uuid.uuid4().hex}.bb.v")
        debug(f"Creating cell models for {input_models} at '{out_path}'…")
        bad_yosys_line = re.compile(r"^\s+(\w+|(\\\S+?))\s*\(.*\).*;")

        stack: List[Literal["specify", "primitive"]] = []
        with open(out_path, "w", encoding="utf8") as out:
            for model in input_models:
                try:
                    for line in open(model, "r", encoding="utf8"):
                        if len(stack) == 0:
                            if line.strip().startswith("specify"):
                                stack.append("specify")
                            elif line.strip().startswith("primitive"):
                                stack.append("primitive")
                            elif bad_yosys_line.search(line) is None:
                                print(line.strip("\n"), file=out)
                        else:
                            if line.strip().startswith("endspecify"):
                                current = stack.pop()
                                if current != "specify":
                                    raise ValueError(
                                        f"Invalid specify block in {model}"
                                    )
                                print("/* removed specify */", file=out)
                            elif line.strip().startswith("endprimitive"):
                                current = stack.pop()
                                if current != "primitive":
                                    raise ValueError(
                                        f"Invalid primitive block in {model}"
                                    )
                                print("/* removed primitive */", file=out)
                    print("", file=out)
                except ValueError as e:
                    err(f"Failed to pre-process input models for linting: {e}")

        yosys = shutil.which("yosys") or shutil.which("yowasp-yosys")

        if yosys is None:
            warn(
                "yosys and yowasp-yosys not found in PATH. This may trigger issues with blackboxing."
            )
            return out_path

        commands = ""
        for define in list(defines):
            commands += f"verilog_defines -D{define};\n"
        commands += f"read_verilog -sv -lib {out_path};\n"

        output_log_path = f"{out_path}_yosys.log"
        output_log = open(output_log_path, "wb")
        try:
            subprocess.check_call(
                [
                    yosys,
                    "-p",
                    f"""
                    {commands}
                    blackbox;
                    write_verilog -noattr -noexpr -nohex -nodec -defparam -blackboxes {out_path};
                    """,
                ],
                stdout=output_log,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            output_log.close()
            err(f"Failed to pre-process input models for linting with Yosys: {e}")
            err(open(output_log_path, "r", encoding="utf8").read())
            err("Will attempt to load models into linter as-is.")

        return out_path

    def get_lib_voltage(
        self,
        input_lib: str,
    ) -> Optional[Decimal]:
        """
        Extract the voltage from the default operating conditions of a liberty file.

        Returns ``None`` if and only if the ``default_operating_conditions`` key
        does not exist and the number of operating conditions enumerated is not
        exactly 1 (one).

        :param input_lib: The lib file in question
        :returns: The voltage in question
        """
        parser = libparse.LibertyParser(open(input_lib, encoding="utf8"))
        ast = parser.ast

        default_operating_conditions_id = None
        operating_conditions_raw = {}
        for child in ast.children:
            if child.id == "default_operating_conditions":
                default_operating_conditions_id = child.value
            if child.id == "operating_conditions":
                operating_conditions_raw[child.args[0]] = child

        if default_operating_conditions_id is None:
            if len(operating_conditions_raw) > 1:
                warn(
                    f"No default operating condition defined in lib file '{input_lib}', and the lib file has multiple operating conditions."
                )
                return None

            elif len(operating_conditions_raw) < 1:
                warn(f"Lib file '{input_lib}' has no operating conditions set.")
                return None
            default_operating_conditions_id = list(operating_conditions_raw.keys())[0]

        operating_conditions = operating_conditions_raw[default_operating_conditions_id]
        operating_condition_dict = {}
        for child in operating_conditions.children:
            operating_condition_dict[child.id] = child.value
        return Decimal(operating_condition_dict["voltage"])
