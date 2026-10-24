# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
import json
import shlex
from dataclasses import dataclass
from subprocess import PIPE, Popen
from typing import ClassVar

with open("flake.lock", encoding="utf8") as f:
    flake_lock = json.load(f)

result = Popen(
    ["nix", "derivation", "show", "--recursive", "."],
    stdout=PIPE,
    encoding="utf8",
)

parsed = json.load(result.stdout)

result.wait()

included_flakes = {"nix-eda", "nixpkgs"}

for node, info in flake_lock["nodes"].items():
    if node not in included_flakes:
        continue
    original = info.get("original", {})
    locked = info["locked"]
    print(node, end="")
    if "ref" in original:
        print(f" {original['ref']}", end="")
    print(f" git revision {locked['rev']}")

print()


@dataclass
class Tool:
    drv_name: str
    owner: str
    repo: str

    version: str | None = None
    rev: str | None = None
    patches: int | None = None

    by_name: ClassVar[dict[str, "Tool"]] = {}
    by_repo: ClassVar[dict[(str, str), "Tool"]] = {}

    def __post_init__(self):
        Tool.by_name[self.drv_name] = self
        Tool.by_repo[(self.owner, self.repo)] = self


Tool("opensta", "The-OpenROAD-Project", "OpenSTA")
Tool("openroad", "The-OpenROAD-Project", "OpenROAD")
Tool("openroad-abc", "The-OpenROAD-Project", "abc")
Tool("yosys", "YosysHQ", "yosys")
Tool("netgen", "RTimothyEdwards", "netgen")
Tool("magic-vlsi", "RTimothyEdwards", "magic")
Tool("iverilog", "steveicarus", "iverilog")
Tool("verilator", "verilator", "verilator")
Tool("tcl", "tcltk", "tcl")
Tool("klayout", "KLayout", "KLayout")
Tool("python3", "python", "python")
Tool("ruby", "ruby", "ruby")

for path, info in parsed.items():
    drv_env = info["env"]
    if serialized := drv_env.get("__json"):
        drv_env = json.loads(drv_env["__json"])
    if path.endswith("source.drv"):
        # Match GitHub repos if possible
        owner, repo = drv_env.get("owner"), drv_env.get("repo")
        if tool := Tool.by_repo.get((owner, repo)):
            tool.rev = drv_env.get("rev")
    else:
        pname, version = drv_env.get("pname"), drv_env.get("version")
        if pname is None or pname not in drv_env.get("name", ""):
            pname = drv_env.get("name")  # note: version can be None
        if tool := Tool.by_name.get(pname):
            tool.drv_name = pname
            tool.version = version
            patches = drv_env.get("patches", "")
            if isinstance(patches, str):
                patches = shlex.split(patches)
            tool.patches = len(patches)

for name in sorted(Tool.by_name):
    tool = Tool.by_name[name]
    if not tool.version or tool.rev:
        pass
    print(f"{tool.drv_name}", end="")
    if tool.version:
        print(f" {tool.version}", end="")
    if tool.rev:
        print(f" git revision {tool.rev}", end="")
    if tool.patches:
        print(f" + {tool.patches} patches", end="")
    print()
