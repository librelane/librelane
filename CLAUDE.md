# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

OpenLane 2 is a Python framework for ASIC design flows, orchestrating EDA tools (OpenROAD, Yosys, Magic, Netgen, KLayout, CVC) to take RTL through synthesis, place-and-route, and produce GDSII. Development has moved to [LibreLane](https://github.com/librelane/librelane).

## Build & Dev Setup

Uses **Poetry** as the build system. Python 3.8+ compatibility is enforced.

```sh
make venv              # Create venv with all dev deps (uses poetry export internally)
source venv/bin/activate
```

**Nix** is the recommended way to get a full environment with EDA tools:
```sh
nix develop            # Dev shell with all tools
nix run .#openlane -- --pdk-root ~/.volare ./designs/spm/config.json
```

**Local Nix tools** are available at `/nix/var/nix/profiles/default/bin/` (not on PATH by default):
```sh
/nix/var/nix/profiles/default/bin/nix-prefetch-url [--unpack] <url>   # Fetch and hash a URL
/nix/var/nix/profiles/default/bin/nix-hash --to-sri --type sha256 <hash>  # Convert to SRI format
```
Use these to compute Nix hashes locally instead of waiting for CI hash-mismatch round-trips.
- `fetchFromGitHub` uses `--unpack` (hashes the unpacked tree)
- `fetchPypi` does NOT use `--unpack` (hashes the raw tarball)

## Common Commands

| Command | Purpose |
|---|---|
| `make lint` | Run black --check, flake8, mypy |
| `make venv` | Create/refresh the virtualenv |
| `make dist` | Build wheel/sdist via poetry |
| `make docs` | Build Sphinx HTML docs |
| `make docker-image` | Build Docker image via Nix |

### Linting individually
```sh
black --check .                # Formatting check (auto-fix: black .)
flake8 .                       # Style + flake8-no-implicit-concat, flake8-pytest-style
mypy --check-untyped-defs .    # Type checking (custom stubs in type_stubs/)
```

## Testing

```sh
python3 -m pytest -n auto                                    # All unit tests (parallel)
python3 -m pytest test/config/test_config.py                 # Single file
python3 -m pytest test/steps/test_step.py::test_name         # Single test
```

**Step integration tests** (require PDK + `test/steps/all` submodule):
```sh
python3 -m pytest -n auto --step-rx "." -k test_all_steps --pdk-root="./.volare-sky130"
```

**Custom pytest options** (defined in `test/conftest.py`):
- `--step-rx <regex>` — filter which steps to test (default `^$` skips all integration tests)
- `--pdk-root <path>` — path to PDK root directory
- `--keep-tmp` — don't delete temp directories after tests

## Architecture

### Core Pipeline: Flow → Step → State

1. **Flow** — a sequence (or DAG) of Steps. `SequentialFlow` runs steps linearly; the `Classic` flow is the default RTL-to-GDS flow.
2. **Step** — a single operation that transforms State. Takes input State, runs work (usually an external tool), returns `(ViewsUpdate, MetricsUpdate)`.
3. **State** — immutable dict mapping `DesignFormat` enum members to file paths, plus accumulated metrics.
4. **Config** — typed, validated configuration variables loaded from JSON + PDK Tcl files.

### Step Hierarchy

```
Step (ABC)  — openlane/steps/step.py
├── TclStep           — runs a Tcl script in an EDA tool
│   ├── YosysStep     — Yosys synthesis
│   ├── OpenROADStep  — OpenROAD place-and-route
│   ├── MagicStep     — Magic DRC/extraction/stream-out
│   └── NetgenStep    — Netgen LVS
├── OdbpyStep         — Python-based OpenROAD DB manipulation
├── CompositeStep     — groups multiple steps as one
└── Pure Python steps — Checker steps, misc
```

### Registration / Plugin System

Both `Flow` and `Step` use factory registries:
```python
@Step.factory.register()
class MyStep(Step):
    id = "Tool.StepName"  # Convention: "ToolGroup.StepName"
    ...
```

Plugins are auto-discovered packages named `openlane_plugin_*` (via `openlane/plugins.py`).

### OutputProcessor Protocol

Steps communicate metrics from subprocess stdout using special locus strings:
- `%OL_METRIC <name> <value>` / `%OL_METRIC_F` / `%OL_METRIC_I` — emit metrics
- `%OL_CREATE_REPORT <file>` / `%OL_END_REPORT` — redirect stdout to a report file

### Key Modules

| Module | Purpose |
|---|---|
| `openlane/flows/flow.py` | Flow ABC, FlowFactory, FlowProgressBar |
| `openlane/flows/sequential.py` | SequentialFlow (linear step execution) |
| `openlane/flows/classic.py` | Classic RTL-to-GDS flow |
| `openlane/steps/step.py` | Step ABC, OutputProcessor, StepError |
| `openlane/steps/tclstep.py` | TclStep base for Tcl-based EDA tools |
| `openlane/config/config.py` | Config loading and resolution |
| `openlane/config/variable.py` | Variable types (str, bool, Decimal, Path, etc.) |
| `openlane/state/state.py` | State class |
| `openlane/state/design_format.py` | DesignFormat enum (NETLIST, DEF, GDS, etc.) |
| `openlane/common/toolbox.py` | Shared cache/temp directory within a run |
| `openlane/common/misc.py` | `@protected`, `@final` decorators, slugify, mkdirp |

### Run Directory Layout

Design runs are stored at `<design_dir>/runs/<tag>/` with numbered subdirectories per step (e.g., `01-Yosys.Synthesis/`).

## Pre-commit Checks

**Always run before committing:**
```sh
make lint              # Runs black --check, flake8, mypy (matches CI)
```

Or individually:
```sh
black --check .                # Formatting (auto-fix: black .)
flake8 .                       # Style linting
mypy --check-untyped-defs .    # Type checking
ruff check .                   # Syntax check (py38 parse-only, configured in pyproject.toml)
```

## Code Style Notes

- **Python 3.8 compatibility** — no walrus operator (`:=`), no f-string `=` specifier, no `match` statements
- **Formatter**: `black` (line-length 88)
- **Type annotations required** — mypy is enforced in CI
- Step IDs follow `"ToolGroup.StepName"` convention matching the module name
- `@protected` and `@final` decorators in `openlane.common` enforce method access patterns

## CLI Entry Points

| Command | Module |
|---|---|
| `openlane` | `openlane.__main__:cli` |
| `openlane.steps` | `openlane.steps.__main__:cli` |
| `openlane.config` | `openlane.config.__main__:cli` |
| `openlane.state` | `openlane.state.__main__:cli` |
| `openlane.env_info` | `openlane:env_info_cli` |
