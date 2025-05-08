# Copyright 2020-2024 Efabless Corporation
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
from typing import Iterable, List, Union

try:
    import libyosys as ys
except ImportError:
    try:
        from pyosys import libyosys as ys
    except ImportError:
        ys.log_error(
            "Could not find pyosys in 'PYTHONPATH'-- make sure Yosys is compiled with ENABLE_PYTHON set to 1.",
            file=sys.stderr,
        )
        exit(-1)


def _Design_run_pass(self, *command):
    ys.Pass.call__YOSYS_NAMESPACE_RTLIL_Design__std_vector_string_(self, list(command))


ys.Design.run_pass = _Design_run_pass  # type: ignore


def _Design_tee(self, *command: Union[List[str], str], o: str):
    self.run_pass("tee", "-o", o, *command)


ys.Design.tee = _Design_tee  # type: ignore


def _Design_read_verilog_files(
    self: ys.Design,
    files: Iterable[str],
    *,
    top: str,
    synth_parameters: Iterable[str],
    includes: Iterable[str],
    defines: Iterable[str],
    use_synlig: bool = False,
    synlig_defer: bool = False,
):
    files = list(files)  # for easier concatenation
    include_args = [f"-I{dir}" for dir in includes]
    define_args = [f"-D{define}" for define in defines]
    chparams = {}
    synlig_chparam_args = []
    for chparam in synth_parameters:
        param, value = chparam.split("=", maxsplit=1)  # validate
        chparams[param] = value
        synlig_chparam_args.append(f"-P{param}={value}")

    if use_synlig and synlig_defer:
        self.run_pass("plugin", "-i", "synlig-sv")
        for file in files:
            self.run_pass(
                "read_systemverilog",
                "-defer",
                "-sverilog",
                *define_args,
                *include_args,
                file,
            )
        self.run_pass(
            "read_systemverilog",
            "-link",
            "-sverilog",
            "-top",
            top,
            *synlig_chparam_args,
        )
    elif use_synlig:
        self.run_pass("plugin", "-i", "synlig-sv")
        self.run_pass(
            "read_systemverilog",
            "-sverilog",
            "-top",
            top,
            *define_args,
            *include_args,
            *synlig_chparam_args,
            *files,
        )
    else:
        for file in files:
            self.run_pass(
                "read_verilog",
                "-defer",
                "-noautowire",
                "-sv",
                *include_args,
                *define_args,
                file,
            )
        for param, value in chparams.items():
            self.run_pass("chparam", "-set", param, value, top)


ys.Design.read_verilog_files = _Design_read_verilog_files  # type: ignore


def _Design_add_blackbox_models(
    self,
    models: Iterable[str],
    *,
    includes: Iterable[str],
    defines: Iterable[str],
):
    include_args = [f"-I{dir}" for dir in includes]
    define_args = [f"-D{define}" for define in defines]

    for model in models:
        model_path, ext = os.path.splitext(model)
        if ext == ".gz":
            # Yosys transparently handles gzip compression
            model_path, ext = os.path.splitext(model_path)

        if ext in [".v", ".sv", ".vh"]:
            self.run_pass(
                "read_verilog", "-sv", "-lib", *include_args, *define_args, model
            )
        elif ext in [".lib"]:
            self.run_pass(
                "read_liberty",
                "-lib",
                "-ignore_miss_dir",
                "-setattr",
                "blackbox",
                model,
            )
        else:
            ys.log_error(
                f"Black-box model '{model}' has an unrecognized file extension: '{ext}'.",
                file=sys.stderr,
            )
            sys.stderr.flush()
            exit(-1)


ys.Design.add_blackbox_models = _Design_add_blackbox_models  # type: ignore
