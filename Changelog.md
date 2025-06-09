<!--
  * Using my modified version of mdformat:
  nix run .#mdformat -- --wrap 80 --end-of-line lf Changelog.md
-->

<!--
## CLI
## Steps
## Flows
## Tool Updates
## Testing
## Misc. Enhancements/Bugfixes
## API Breaks
## Documentation
-->

# 2.4.0

2.4.0 is the first version of LibreLane, a fork of the OpenLane 2 by its
original authors after Efabless Corporation has ceased operations.

## Steps

* `Odb.*`

  * Unified error handling with that of OpenROAD steps, i.e., dependent on the
    `[ERROR (code)]` alerts.
  * Metrics emitted from Odb steps are now also aggregated.
  * **API**: instance variable `.alerts` now holds emitted alerts until the next
    `start()`, similar to `.state_out`.

* Created `Odb.InsertECOBuffer`, `Odb.InsertECODiode`

  * New ECO steps using the variables `INSERT_ECO_BUFFERS` and
    `INSERT_ECO_DIODES` respectively to allow creation of buffers and diodes
    after (and only after global routing,) with an option to run it after
    detailed routing so long as detailed routing is run again afterwards.

* `OpenROAD.*`

  * **API**: instance variable `.alerts` now holds emitted alerts until the next
    `start()`, similar to `.state_out`.

## Documentation

* Variable types now link to dataclasses' API reference as appropriate.

## Tool Updates

* Volare replaced by [Ciel](https://github.com/fossi-foundation/ciel)@2.0.1
* nix-eda replaced by the
  [FOSSi Foundation fork](https://github.com/fossi-foundation/nix-eda)@2.1.3
* OpenLane Cachix replaced by an S3-based cache hosted at
  https://nix-cache.fossi-foundation.org

## Misc. Enhancements/Bugfixes

* Worked around an issue with Google Colaboratory where if `PATH` is set,
  Yosys's Python `sitepackages` are replaced with the global ones and everything
  breaks.

# 2.3.10

## Steps

* `Yosys.Synthesis`
  * `SYNTH_ELABORATE_FLATTEN` now passes the `-noscopeinfo` flag so scopeinfo
    cells are no longer emitted from Synthesis.

# 2.3.9

## Tool Updates

* Backported https://github.com/The-OpenROAD-Project/OpenROAD/pull/6743 to
  OpenROAD to fix GUI crashes on C++ standard libraries that are not libstdc++
  (aka: macOS.)

# 2.3.8

## Misc. Enhancements/Bugfixes

* Fixed substitutions in `config.json` being applied to all flows. It now only
  applies to the flow in meta.flow (which falls back to `Classic` if it's null.)

# 2.3.7

## Tool Updates

* Updated Docker requirement to tested version: 27.3.1
  * Added warning when Docker version is out of date.

## Documentation

* Updated documentation to reflect tested Docker version.
* Updated documentation to stop using a branch of the DetSys Nix Installer.

# 2.3.6

## Steps

* `Verilator.Lint`
  * Fixed missing `VERILOG_INCLUDE_DIRS` variable, which would cause designs
    that synthesize correctly to otherwise fail linting.

# 2.3.5

## Tool Updates

* `nix-eda` updated to 2.1.2
  * Pulls in a Python overlay fix and a fix for `gdstk`.

# 2.3.4

## Tool Updates

* Added patch to Yosys to resolve an early return issue that broke non-const
  asynchronous resets. See https://github.com/YosysHQ/yosys/issues/4712 for more
  info.

# 2.3.3

## Steps

* `OpenROAD.Floorplan`

  * Fixed an issue in `FP_SIZING`: `absolute` mode where if the die area's x0 >
    x1 or y0 > y1, the computed core area would no longer fit in the die area.
    Not that we recommend you ever do that, but technically OpenROAD allows it.

# 2.3.2

## Steps

* `Yosys.*`
  * Fixed blackbox Verilog and lib models causing a crash if they are gzipped
    and/or have the extension `.gz`.

## Tool Updates

* Relaxed requirement on `httpx` to include `0.28.X`, which has no removals
  compared to `0.27.0`.

## Documentation

* Clarified support for gzipped files in the Classic flow.

# 2.3.1

## Tool Updates

* KLayout now compiled with `-qt-binding`, which increases distribution size but
  allows for more features.

# 2.3.0

## Steps

* `OpenROAD.GlobalPlacement`

  * Exposed `-routability_check_overflow` argument as new variable
    `PL_ROUTABILITY_OVERFLOW_THRESHOLD`.

* `Yosys.*Synthesis`

  * Created new variable `SYNTH_HIERARCHY_MODE`, replacing `SYNTH_NO_FLAT`.
    There are three options, `flatten`, `deferred_flatten` and `keep`. The first
    two correspond to `SYNTH_NO_FLAT` being false and true respectively. The
    third keeps the hierarchy in the final netlist.
  * Created new variable `SYNTH_TIE_UNDEFINED` to customize whether undefined
    and undriven values are tied low, high, or left as-is.
  * Created new variable `SYNTH_WRITE_NOATTR` to allow attributes to be
    propagated to the final netlist.

* Created `Yosys.Resynthesis`

  * Like `Yosys.Synthesis`, but uses the current input state netlist as an input
    instead of RTL files

## CLI

* Added new option: `-e`/`--initial-state-element-override`: allows an element
  in the initial state to be overridden straight from the commandline.

# 2.2.9

## Steps

* `Yosys.JsonHeader`, `Yosys.Synthesis`

  * Fixed `VERILOG_INCLUDE_DIRS` being a list of strings instead of a list of
    `Path`s.

# 2.2.8

## Steps

* `Checker.*Violations`

  * Changed `TIMING_VIOLATION_CORNERS` to a PDK variable to avoid breaking PDKs
    without `tt` in corner names.

# 2.2.7

## Steps

* `OpenROAD.WriteViews`

  * Fixed step not being registered to factory object.

# 2.2.6

## Steps

* `OpenROAD.ResizerTimingPostGRT`

  * Fixed `GRT_RESIZER_GATE_CLONING` incorrectly applied to hold fixing instead
    of setup fixing.

* `OpenROAD.ResizerTimingPostCTS`

  * Fixed `PL_RESIZER_GATE_CLONING` incorrectly applied to hold fixing instead
    of setup fixing.

# 2.2.5

## Steps

* `Yosys.JsonHeader`, `Verilator.Lint`, `Odb.WriteVerilogHeader`

  * Fixed `VERILOG_POWER_DEFINE` not being optional which was an unintentional
    break from OpenLane 1.

    * Default value is still `USE_POWER_PINS`, but it can be explicitly unset.

## Misc. Enhancements/Bugfixes

* `openlane.config`: Fixed issue where preprocessor would ignore explicitly-set
  null values in configuration files.

# 2.2.4

## Tool Updates

* `yosys-sby`: Overlaid new hash for `yosys-0.46` tag because of a tag update
  upstream.

# 2.2.3

## Misc. Enhancements/Bugfixes

* Fixed incorrect error message when subtituting a step with one that has a
  nonexistent ID.

# 2.2.2

## Steps

* `Odb.*`

  * Fixed OpenROAD dropping user-set `PYTHONPATH` values.

## Tool Updates

* Use `NIX_PYTHONPATH` instead of `PYTHONPATH` in Docker and devshells to avoid
  collisions with user-set `PYTHONPATH` variables.

# 2.2.1

This patch has no functional changes to OpenLane proper.

## Tool Updates

* `flake.createOpenLaneShell` now gets OpenLane from `python3.pkgs`.
* Fixed issue with `flake.createOpenLaneShell` where plugins would not get
  included due to an operator precedence issue.

# 2.2.0

## CLI

* Exposed Flow.start(overwrite=) as `--overwrite`, which removes a run directory
  before running the flow (if it exists)

## Steps

* Created `Odb.ManualGlobalPlacement`

  * Can create a global placement for instances. Intended for
    manually-instantiated buffers that require a certain regional placement or
    similar.
  * Uses new variable `MANUAL_GLOBAL_PLACEMENTS`, a mapping from instance names
    to the `Instance` class.

* Created `Odb.CellFrequencyTables`

  * Creates a number of tables to show the cell frequencies by:
    * Cells
    * Buffer cells only
    * Cell Function
    * SCL

* `OpenROAD.*`

  * All steps that modify views now update design cell metrics using OpenROAD's
    `report_design_area_metrics`

* `OpenROAD.ResizerTimingPostGRT`

  * Added `GRT_RESIZER_RUN_GRT` to control whether global routing is re-run
    after this step, which is usually required but may be redundant in some
    custom flows.

* `OpenROAD.RepairDesignPostGRT`

  * Added `GRT_DESIGN_REPAIR_RUN_GRT` to control whether global routing is
    re-run after this step, which is usually required but may be redundant in
    some custom flows.

* `OpenROAD.STA*`

  * New report `clock.rpt` created with information about each clock in a
    specific domain

* `OpenROAD.WriteViews`

  * Added `OPENROAD_LEF_BLOAT_OCCUPIED_LAYERS` with a default value of `true`

* `Yosys.*Synthesis`

  * ABC scripts used now created dynamically and dumped as a `.abc` file into
    the step directory.
  * Implemented many of the
    [suggestions by @ravenslofty](https://github.com/efabless/openlane2/issues/524)
    from YosysHQ, some behind flags:
    * `SYNTH_ABC_DFF`: Adds `-dff` to `abc` invocations (except the ones inside
      `synth`)
    * `SYNTH_ABC_BOOTH`: Activates the
      [`booth`](https://yosyshq.readthedocs.io/projects/yosys/en/0.44/cmd/booth.html)
      pass as part of `synth`
    * `SYNTH_ABC_USE_MFS3`: Uses `mfs3` in all strategies before retime
    * `SYNTH_ABC_AREA_USE_NF`: Attempts delay-based mapping with a really high
      delay value instead of area-based mapping.

* `Yosys.JsonHeader`, `Yosys.*Synthesis`

  * **Internal**: * Steps are no longer `TclStep`s: rewritten in Python and now
    use `libyosys`. While there are no functional changes, this enhances the
    codebase's consistency and helps avoid tokenization-related security issues.

## Flows

* `Classic`
  * Emplaced `Odb.ManualGlobalPlacement` immediately preceding
    `OpenROAD.DetailedPlacement`.
  * Emplaced `Odb.CellFrequencyTables` after `OpenROAD.FillInsertion`

## Tool Updates

* OpenROAD -> `bbe940134bddf836894bfd1fe02153f4a38f8ae5`

  * OpenSTA -> `20925bb00965c1199c45aca0318c2baeb4042c5a`
  * Removed "stable" version of OpenSTA

* Updated nix-eda to `0814aa6`: more orthodox approach to managing dependencies
  by overlaying them on top of nixpkgs, which fixes an occasional "repeated
  allocation" issue and helps make override behavior more consistent.

  * Yosys and first-party plugins -> `0.46`
  * `klayout` -> `0.29.4`
  * `magic` -> `8.3.489`
  * `netgen` -> `1.5.278`
  * OpenROAD now used with new `withPythonPackages` features to use Python
    packages specifically for the OpenROAD environment

* OpenLane itself no longer included in `devShells.*.dev`, `devShells.*.docs`

  * These shells are intended to be actual dev shells, i.e. used to develop
    OpenLane, and needing OpenLane to pass tests to run these shells makes no
    sense.

* Open PDKs -> `0fe599b` (Recommended for chipIgnite 2409/2411+ shuttles)

## Misc. Enhancements/Bugfixes

* `openlane.common.metrics`
  * `aggregate_metrics()`: Added support for aggregation of N-modifier levels
* `openlane.config.Config`
  * YAML 1.2 configuration files now accepted using `.yaml` or `.yml`
    extensions, with the same featureset as JSON files.
  * The first configuration (file/dict) supplied no longer needs to be a
    complete configuration so long as any required variables are supplied in
    later configurations. Missing variables are only checked on the complete
    configuration.
  * Internally reworked how config files and command-line overrides are parsed.
* Fixed bug with deprecated variable translations of
  `{CLOCK,SIGNAL}_WIRE_RC_LAYERS`.

## Documentation

* Added info on YAML configuration files.
* Documentation for `Instance` dataclass generalized to include instances of
  cells and not macros.

# 2.1.11

## Steps

* `OpenROAD.STA*PnR`

  * Fixed `timing__*_r2r__ws__corner` metrics reporting the wrong value

# 2.1.10

## Misc. Enhancements/Bugfixes

* `openlane.config.Variable`

  * Fixed an issue when strict type-checking is disabled where empty strings
    would crash iterable objects.

## Tool Updates

* Fixed mypy to 1.9.0 to match NixOS 24.05.

* Checked `poetry.lock` into version control to improve reproducibility.

# 2.1.9

## Steps

* `OpenROAD.CheckAntennas`

  * Fixed table being printed to file with wrong width.

* `OpenROAD.STA*PnR`

  * Fixed table being printed to file with wrong width.

## Flows

* `SynthesisExploration`

  * Fixed table being printed to file with wrong width.

# 2.1.8

## Steps

* `OpenROAD.STA*PnR`

  * Fixed a bug in STA metrics where paths with exactly zero slack are counted
    as violations.

# 2.1.7

## Steps

* `Odb.Remove*Obstructions`

  * Rework obstruction matching code to not use IEEE 754 in any capacity
  * Fixed bug where non-integral obstructions would not be matched correctly
    (thanks @urish!)

# 2.1.6

## Steps

* `Yosys.Synthesis`

  * Fixed bug where `hilomap` command was invoked incorrectly (thanks @htfab!)

# 2.1.5

## Steps

* `Odb.SetPowerConnections`

  * Fixed an issue introduced in `2.1.1` where modules that are defined as part
    of hierarchical netlists would be considered macros and then cause a crash
    when they are inevitably not found in the design database.
    * Explicitly mention that macros that are not on the top level will not be
      connected, and emit warnings if a hierarchical netlist is detected.

## Documentation

* Updated macro documentation to further clarify how instances should be named
  and how names should be added to the configuration.

# 2.1.4

## Steps

* `OpenROAD.STA*PNR`
  * New environment variable made accessible to SDC files used during
    Multi-Corner STA steps, `OPENLANE_SDC_IDEAL_CLOCKS`, set to `1` for pre-PnR.
    Band-aid until the SDC situation is properly discussed and addressed (in a
    potentially breaking change.)
  * Fixed issue where the clock was always propagated after `STAPrePNR`
    regardless the information in the SDC file.
  * For backwards compatibility, `STAPrePNR` unsets all propagated clocks and
    the rest set all propagated clocks IF the SDC file lacks the strings
    `set_propagated_clock` or `unset_propagated_clock`.

# 2.1.3

## Tool Updates

* Bundled an downgraded OpenSTA bundled with OpenLane to work around critical
  bug for hierarchical static timing analysis:
  https://github.com/parallaxsw/OpenSTA/issues/82
  * Version of OpenSTA linked against OpenROAD unchanged.

## Testing

* CI now uses DeterminateSystems Nix Installer for all Nix installations as well
  as the Magic Nix Cache Action instead of the nonfunctional attempt at local
  file-based substituters

## Documentation

* Installation documents now use the less-brittle Determinate Systems Nix
  installer, as well as adding warnings about the `apt` version of Nix.

* Added an OpenROAD Flow Scripts-inspired Diagram to the Readme.

# 2.1.2

## Steps

* `OpenROAD.*`

  * Fixed an issue where the validation for `PDN_MACRO_CONNECTIONS` would
    partially match net names, unlike OpenROAD itself
  * Internal string escaping consistency

# 2.1.1

## Steps

* `Odb.SetPowerConnections`

  * Internally reworked pin detection behavior so power pins are found in the
    LEF first then matched in the Verilog, fixing a corner-cases where
    unconnected buses would be candidates for power pins, then promptly cause a
    crash as they only exist in the layout as separate pins.

* `OpenROAD.IOPlacement`, `OpenROAD.GlobalPlacementSkipIO`

  * `FP_IO_MODE` renamed to `FP_PPL_MODE`: translation behavior for OpenLane
    1-style FP_IO_MODE with integers added behind deprecated name `FP_IO_MODE`.

* `Yosys.*Synthesis`

  * Restored filtering of `defparam` from output netlists to avoid surprisingly
    still extant OpenSTA limitation.

## Testing

* Added file to exclude step unit tests purely to speed-up turnaround time for
  PRs (as sometimes a test would need to be deleted/temporarily disabled without
  updating the submodule, see #475 for a similar situation)

* Mac CI now uses an artifact of the PDK

  * Unlike the Linux runners, Mac runners:
    * Are disproportionately affected by rate-limiting: cannot pull from GitHub
      using Volare
    * Do not support caches created on Ubuntu, even with `enableCrossOsArchive`

# 2.1.0: The "Customization and Control" Update

## CLI

* Overhauled how the PDK commandline options work, using a decorator instead of
  doing everything in a callback
* `--smoke-test/--run-example` are now no longer callbacks, and `--run-example`
  now supports more options (e.g. another PDK, another flow, etc.)
* Docker subprocesses
  * Are now always run interactively and can be interrupted.
  * Are now run using `execlp`, replacing the Python interpreter altogether

## Steps

* Created `Checker.NetlistAssignStatements`

  * Outputs warnings or errors (depending on `ERROR_ON_NL_ASSIGN_STATEMENTS`)
    when `assign` statements are found in the netlist of the input state (assign
    statements cause some issues with some tools)

* `KLayout.OpenGUI`

  * Renamed `KLAYOUT_PRIORITIZE_GDS` to `KLAYOUT_GUI_USE_GDS` to be consistent
    with the Magic steps.
  * Script no longer relies on the `click` library as the internal Python
    interpreter more often than not has trouble finding the site packages (and
    indeed the site packages includes its own pya/klayout which is its own
    headache.)

* `Magic.*`

  * All steps now use a new processor,
    `openlane.steps.magic.MagicOutputProcessor`, to capture and count errors
  * Fixed `magicrc` being `abspath`'d before command invocation (breaks
    reproducibles)
  * `_MAGIC_SCRIPT` is now set in `prepare_env` instead of `run_subprocess` (so
    it can be intercepted for reproducibles)

* New step, `Magic.OpenGUI`, which opens either DEF files or GDS files in magic

* `Magic.SpiceExtraction`:

  * A `feedback.xml` is now created, with the contents being the SPICE
    Extraction feedback in the KLayout marker database format
  * Created `MAGIC_EXT_ABSTRACT_CELLS`: a list of regular expressions that are
    matched against the design's cells names what are abstracted (black-boxed)
    during extraction.

* `Netgen.LVS`:

  * Added `LVS_FLATTEN_CELLS`: A list of cells to flatten in LVS.
  * Added `LVS_INCLUDE_MARCOS_NETLIST`. If enabled macros' netlist are loaded
    when running LVS. Either `pnl` or `nl` or `vh` views are selected.
  * Updated Netgen setup file to equate cells inside macros where the GDS is
    generated with blackbox macro option

* `Odb.ApplyDEFTemplate`: Thanks [@smunaut](https://github.com/smunaut)

  * DEF template pin placement status (e.g. `PLACED`, `FIXED`) now always
    propagated to work around PDN generation removing placed but unconnected
    power pins.
  * Fixed crashes when copying power pins from a template where the net name and
    the power pin name may be different (or one net may be connected to multiple
    power pins.)

* `Odb.ReportDisconnectedPins`

  * Disconnected dummy instances created during CTS, prefixed `clkload`, are now
    ignored.

* `Odb.SetPowerConnections`

  * **Internal**: Restructure `power_utils.py` to provide better error messages
    and use dictionaries instead of oddball iterator-based filtering

* Created `OpenROAD.DEFtoODB`

  * Useful for custom flows, where the DEF is modified but the ODB needs to be
    updated to reflect these modifications

* `OpenROAD.*`

  * OpenROAD scripts now set `set_wire_rc` for the average values of the layers
    grouped by routing direction. All layers in the routing range are used if
    either `SIGNAL_WIRE_RC_LAYERS` or `CLOCK_WIRE_RC_LAYERS` are null.
  * Slight internal Tcl code reorganization.

* `OpenROAD.Floorplan`

  * Added soft placement obstructions via new variable `PL_SOFT_OBSTRUCTIONS`.

* `OpenROAD.RepairDesignPostGPL`

  * Added new variable `DESIGN_REPAIR_REMOVE_BUFFERS`, which will instruct
    OpenROAD to remove synthesis buffers so there's more flexibility during
    design repair: see
    https://github.com/The-OpenROAD-Project/OpenROAD/blob/ad54bbe88b561d1c30451d8a3c85ad11c1692905/src/rsz/README.md?plain=1#L185

* `Yosys.*`

  * Added new variable `YOSYS_LOG_LEVEL`, which controls the verbosity of Yosys
    output

* `Yosys.*Synthesis`

  * Moved the `rename` of top module to before selecting it. This fixes a
    problem DFFRAM where needed modules are optimised away and then synthesis
    fails. (Thanks @donnie-j!)

  * Syntheses with `SYNTH_ELABORATE_ONLY` no longer report undriven nets as a
    check error (frequently for some top-level integrations, output pins are
    left undriven entirely to save space.)

## Flows

* Created new mono-step flow, `OpenInMagic`, which runs `Magic.OpenGUI`
* `VHDLClassic` is now based on `Classic` with appropriate `Substitutions

## Tool Updates

* All tool nix derivations now have `rev`/`version` and `sha256` as one of their
  parameters, allowing them to be easily replaced with `.override`.

* OpenLane 2 now uses [nix-eda](https://github.com/efabless/nix-eda) for some of
  its dependencies

  * `nixpkgs` -> `24.05`
  * `klayout` -> `0.29.1`
  * `magic` -> `8.3.483`/`291ba96`
    * now uses tk with X11 on macOS, to prevent crashes when attempting to use
      the GUI
  * `netgen` -> `bf67d3c`
  * `forAllSystems` built into `nix-eda`, now composes overlays for nixpkgs
    based on the `withInputs` field, allowing for easier overriding

* `volare` -> `0.18.1`

* `ioplace_parser` -> `0.3.0`

* `openroad` -> `b16bda7`

  * Removed OpenLane-specific patch for querying existence of antenna
    information
  * `openroad-abc` -> `ef5389d`
    * `ABC_USE_NAMESPACE` now set, value also injected into header files
  * `opensta` -> `e01d3f1`

* Python build tool changed from `setuptools` to `poetry`, which properly
  verifies that all version ranges are within constraints

  * Updated wrong Python package version ranges that all happen to work

* Nix devshells now use [numtide/devshell](https://github.com/numtide/devshell),
  which creates an executable to enter the environment, allowing for easy
  repacking

* Docker image creation now uses a Nix derivation based on that of the official
  Nix Docker image, which includes a full Nix installation in the image (so
  users may add tools and apps in the container at their leisure.)

* `mdformat` promoted from overlay to `packages`.

## Misc. Enhancements/Bugfixes

* `openlane.flows.SequentialFlow`

  * Substitutions can now
    * be done at the class level by assigning to `Substitutions`
    * be done in `config.json` files using a dictionary in the field
      `.meta.substituting_steps`
    * emplace steps before or after existing steps, e.g. `+STEP`, `-STEP`
  * Step names for `from`, `to`, `skip` and `only` are now fuzzy-matched using
    `rapidfuzz` to give suggestions in error messages
    * If the environment variable
      `_i_want_openlane_to_fuzzy_match_steps_and_im_willing_to_accept_the_risks`
      is set to `1`, the suggestions are used automatically (not recommended)
  * Gating config vars are now simply removed if they do not target a valid step
    (so removed steps in a substituted flow do not cause a FlowException)

* `openlane.common`

  * `DRC`: Work around a weird macOS-only bug where boxes in exported KLayout
    marker databases would not function properly: see
    https://github.com/KLayout/klayout/issues/1550
  * `GenericDictEncoder`: Fixed crash when attempting to dump a Decimal of
    infinite value

* `openlane.common.config`

  * Trailing commas are now permitted when converting from a string format
    (which are necessary because of the ambiguity of lists of lists.)

* `openlane.steps.DefaultOutputProcessor`

  * `%OL_METRICS_F` now uses Decimals instead of Floats

* `openlane.steps.Step.create_reproducible`

  * `PDK_ROOT` now included if the PDK is included but not flattened so Magic
    steps can work

* `openlane.steps.TclStep`

  * **Internal**: Internal environment variables prefixed with `_` are no longer
    rerouted to `_env.tcl`, instead being passed raw (to help with creating
    reproducibles)

* Universal flow configuration variable

  * `DATA_WIRE_RC_LAYER` renamed to `SIGNAL_WIRE_RC_LAYERS`,
    `CLOCK_WIRE_RC_LAYER` renamed to `CLOCK_WIRE_RC_LAYERS`, with translation
    behavior and data type changed to `List[str]?`
  * Universal PDK variables `SIGNAL_WIRE_RC_LAYERS`/`CLOCK_WIRE_RC_LAYERS` no
    longer have default values for all PDKs (are null.)

* Fixed new typing inconsistencies exposed by mypy.

* Removed loop header genvar declaration from examples (limited compatibility
  with some tools)

## Documentation

* Created a new document on writing plugins.

* Updated the architecture document to reflect changes and clarify some
  elements.

* Updated documentation of the `state` submodule.

* Updated Usage/Writing Custom Flows to document step substitution

* Fixed a number of broken links.

# 2.0.11

## Misc Enhancements/Bugfixes

* Fixed a deadlock in some situations because of `OpenROAD.STAPrePNR` using the
  global thread-pool for OpenLane, which may be used to run the step itself.

# 2.0.10

## Tool Updates

* Relaxed `rich` version range to allow Rich 13.
  * Matches Volare's version range and allows CACE and OpenLane 2 to be
    installed in the same Python environment.

# 2.0.9

## CLI

* Fixed `--ef-save-views-to` saving to `signoff/<design>/openlane` instead of
  `signoff/<design>/openlane-signoff` (which makes less sense but is the
  established convention at Efabless.)

## Steps

* `OpenROAD.*`

  * Fixed environment contamination with deprecated variables that may be used
    by user-supplied PDN or SDC files.

* `OpenROAD.GeneratePDN`

  * Restored compatibility with some ancient OpenLane PDN config files.

## Tool Updates

* Updated `ioplace_parser` to `0.2.0`
  * Fixes regressions in pin regular expression parsing.

# 2.0.8

## Steps

* `Odb.DiodePortInsertion`, `Odb.DiodesOnPorts`
  * Fixed bug where diodes were never inserted on outputs, and added unit tests
    to that effect.

# 2.0.7

## Misc Enhancements/Bugfixes

* Overhauled Tcl configuration loading code to fix a number of bugs that may
  occur when a Tcl file sources another Tcl file, such as for TinyTapeout
  configs (thanks @htfab)

# 2.0.6

## Misc. Enhancements/Bugfixes

* Fixed a crash on Linux distributions where `/etc/lsb-release` includes
  comments.

# 2.0.5

## Misc. Enhancements/Bugfixes

* The flow warning summary now only shows the first instance of any warning
  emitted, instead showing two numbers for identical warnings in other steps and
  for similar warnings (e.g. same OpenROAD code.)

# 2.0.4

## Steps

* `Odb.SetPowerConnections`

  * Fixed bug where instances with special characters in their name and power
    pins are not equal to those of the SCL would not get connected.
  * Added assertion that exactly one pin is connected for every operation.

* `Yosys.GenerateJSONHeader`

  * Netlist is now flattened so `Odb.SetPowerConnections` can properly set pins
    for nested macros with power pin names not equal to those of the SCL.

# 2.0.3

## Tool Updates

* Updated OpenROAD to `d423155`, OpenSTA to `a7f3421`
  * Addresses an
    [antenna repair bug](https://github.com/efabless/openlane2/issues/459)

## Testing

* Updated a number of unit tests to reflect new OpenROAD error codes.
* Fixed failing design integration tests.

# 2.0.2

## Steps

* `Odb.ReportDisconnectedPins`
  * Fixed table not being written to step directory
  * Fixed bug where table widths were not being set properly
  * Fixed bug where pins with `USE SIGNAL` would be considered power pins

# 2.0.1

## Steps

* `OpenROAD.*`
* Fixed alert about unmatched regexes in `PDN_MACRO_CONNECTIONS` not being
  properly marked as an `[ERROR]`.
* Fixed crash when steps that generate OpenROAD alerts that are suppressed by
  the flow experience a non-zero exit.

# 2.0.0

## Docs

* Updated messaging to be a bit more consistent wrt OpenLane 1 vs OpenLane 2.

# 2.0.0rc3

## CLI

* Resolved bug causing nonexistent mounted volumes to be created as root when
  using a non-rootless container engine with `--dockerized`.
* Fixed issue where PIP versions of OpenLane would not be able to copy examples
  properly.
* Environment detection scripts no longer use `nix-info`, saving time.

## Steps

* `OpenROAD.STAPrePnR`

  * Now performs multicorner STA pre-PnR according to `STA_CORNERS`; although if
    two corners have identical file lists the latter corner is skipped
  * Internally rearranged class structure so STA pre and post PnR share as much
    code as possible

* `Yosys.*`

  * Fixes a bug where synthesis checks were not passed properly when
    `SYNTH_ELABORATE_ONLY` is true.
  * **Internal**:
    * Created new namespace, `yosys_ol`, to encapsulate a number of reusable
      functions for modularity and readability
    * Created two new functions `ol_proc` and `ol_synth`; to encapsulate our
      modified `synth` and `proc` instead of them being strewn across
      `synthesize.tcl`
    * ABC script construction moved to standalone file

## Misc

* `openlane.steps`
  * `Step`
    * `.start()` no longer prints logs at the beginning as it may not
      necessarily exist

# 2.0.0rc2

## CLI

* `openlane.steps`
  * `eject` *now overrides `psutils.Popen()` instead of `run_subprocess`,
    allowing it to run at a lower level
  * `PATH`, `PYTHONPATH` now excluded from `run.sh`

## Steps

* `Checker.PowerGridViolations`

  * Fixed mistakenly added whitespace in `FP_PDN_CHECK_NODES`

* `Magic.WriteLEF`

  * Added new variable `MAGIC_WRITE_LEF_PINONLY`, which writes the LEF with with
    the `-pinonly` option; declaring nets connected to pins on the same metal
    layer as obstructions and not part of the pin

* `OpenROAD.*`, `Odb.*`

  * Outputs now processed first by new class `OpenROADOutputProcessor`, which
    captures warnings and errors from OpenROAD into a data structure and emits
    them using OpenLane's logger

* `OpenROAD.CTS`

  * Made `CTS_MAX_CAP` a non-PDK value, and also optional as the values in the
    PDK configuration are bad and OpenROAD does a better job without it
  * CTS no longer passes `MAX_TRANSITION_CONSTRAINT`, instead using a new
    variable `CTS_MAX_SLEW` if it exists
  * Fixed issue where no arguments were passed to
    `configure_cts_characterization`
  * Fixed bug where an incorrect value was passed to the `-max_slew` option

* `Odb.ApplyDEFTemplate`

  * Added new variable, `FP_TEMPLATE_COPY_POWER_PINS`, that *always* copies
    power pins from the DEF template
  * Power pins are now filtered and exempt from placement otherwise, allowing
    the step to be runnable after PDN generation

* `Odb.CustomIOPlacement`

  * Power pins are now filtered and exempt from placement, allowing the step to
    be runnable after PDN generation
  * `FP_IO_VLENGTH`, `FP_IO_HLENGTH` are now both optional PDK variables
  * The values are now used properly instead of a taking the maximum of both for
    both kinds of pins
  * For PDKs that do not specify them, the script calculates default values
    based on the layers' rules
  * `QUIT_ON_UNMATCHED_IO` now migrates to new variable
    `ERRORS_ON_UNMATCHED_IO`, an enumeration of four variables that controls
    whether errors are emitted in:
    * no situation
    * situations where pins in the design are missing from the config file
      (default, matching openlane 1)
    * situations where pins in the config file are missing from the design (new)
    * either situation
  * Better error message for too many pins on the same side

* `OpenROAD.GlobalPlacement`

  * Added `PL_MIN_PHI_COEFFICIENT`, `PL_MAX_PHI_COEFFICIENT` for when global
    placement diverges

* `OpenROAD.GlobalPlacementSkipIO`

  * `PL_TIMING_DRIVEN` and `PL_ROUTABILITY_DRIVEN` no longer passed (useless
    with `-skip_io`)

* `OpenROAD.IOPlacement`

  * `FP_IO_VLENGTH`, `FP_IO_HLENGTH`, `FP_IO_MIN_DISTANCE` are now all optional
    PDK variables
    * For PDKs that do not specify them, OpenROAD calculates default values
      based on the layers' rules

* `OpenROAD.ManualMacroPlacement`

  * **API Break**: Verilog names of macros are now considered instead of DEF
    names in the event of a mismatch (e.g. for instances with `[]` or `/` in the
    name.)

* `OpenROAD.STAPrePnR`, `OpenROAD.STAPostPnR`

  * Added new configuration variable `EXTRA_SPEFS` ONLY for backwards
    compatibility with OpenLane 1 that should not otherwise be used

* `OpenROAD.STAPrePNR`

  * Unset clock propagation for this step (misleading as the clock should be
    ideal before CTS)

* `Verilator.Lint`

  * Now works with the preprocessor macro `VERILOG_POWER_DEFINE` being defined -
    justification is that most macros come with a powered netlist than a regular
    netlist
  * `CELL_BB_VERILOG_MODELS` is no longer used, with the blackbox models always
    getting generated (so power pins can be included)
  * `__openlane__`, `__pnr__`, `PDK_{pdk_name}` and `SCL_{scl_name}` are all
    always defined as preprocessor macros
  * Fixed issue where the order of files may not be preserved for macros,
    causing linting to fail
  * Internally adjusted how linter flags are set; a `.vlt` file is used to turn
    off certain linting rules for the black-box models instead of copying and
    wrapping the black-box comments in comments

* `Yosys.*`

  * `__openlane__`, `__pnr__`, `PDK_{pdk_name}` and `SCL_{scl_name}` are all
    always defined as preprocessor macros

* `Yosys.JsonHeader`

  * Now reads generated black-boxed models of the standard cells with power pins
    instead of lib files, allowing power pins to be explicitly specified for
    hand-instantiated cells as well without issue

## Flows

* `Classic`
  * Added `Odb.AddRoutingObstructions` before global routing
  * Added `Odb.RemoveRoutingObstructions` after detailed routing
  * Moved PDN generation steps before Global Placement

## Tool Updates

* `magic` -> `8.3.466`/`bfd938b`
  * Addresses a bug with reading DEF files using generated vias
* Updated KLayout to `0.28.17-1`
  * Relaxes PIP version range to accept newer patches (not newer minor versions)

## Testing

* Added an OpenLane 1-compatible configuration for `aes_user_project_wrapper` to
  test back-compat
* Ensured `open_proj_timer` config matches OpenLane 1's as closely as possible
* Updated unit tests because newer versions of flake8 hate `pytest.fixture()`
  for some reason
* Updated step unit tests that look for OpenROAD alerts to use captured alerts
  instead of checking the log.

## Misc. Enhancements/Bugfixes

* `openlane.common`
  * `Toolbox`
    * New method, `get_timing_files_categorized`, returns the three design
      formats in, get this, three separate lists
* `openlane.config`
  * `Config`
    * No longer attempts to migrate `EXTRA_SPEFS` to `MACROS` because of
      side-effects (e.g. the dummy paths)
  * PDK backwards-compatibility script now skips migrating `LIB_*` if `LIB`
    already exists
    * "Default" constraints made exclusive to `sky130` and `gf180mcu`
* `openlane.steps.Step`
  * `run_subprocess`: New concept of "output processors"- classes that may do
    processing on the output of a step to parse it
    * Default output parsing behavior implemented as `DefaultOutputProcessor`
    * `run_subprocess` no longer returns just metrics, rather, metrics are
      returned under the key `generated_metrics` when the
      `DefaultOutputProcessor` is used along with the results of other output
      processors
* Slightly adjusted widths of printed tables across the codebase for
  readability.

## API Breaks

* `OpenROAD.ManualMacroPlacement`

  * Verilog names of macros are now considered instead of DEF names in the event
    of a mismatch (e.g. for instances with `[]` or `/` in the name.)

* `openlane.steps.Step`

  * `run_subprocess` no longer returns just metrics, rather, metrics are
    returned under the key `generated_metrics` when the `DefaultOutputProcessor`
    is used along with the results of other output processors

## Documentation

* Adapted timing closure guide by [@shalan](https://github.com/shalan) to
  OpenLane 2
  * Converted to MyST Markdown
  * All images made dark-mode friendly
  * References to variables all now resolve properly
* Fixed a number of inconsistencies and broken links.

# 2.0.0rc1

## CLI

* Fixed `--ef-save-views-to` not saving `.mag`, `.gds` views

## Steps

* `Checker.*`
  * Created new `ERROR_ON` variables with the removed `QUIT_ON` variables from
    the `Classic` flow being added as deprecated names for these variables.
  * Disabling `ERROR_ON*` (previously `QUIT_ON*`) no longer bypasses a step
    entirely. A warning will be generated and the flow will not quit.
* `Checker.TimingViolations`
  * `TIMING_VIOLATIONS_CORNERS` renamed to `TIMING_VIOLATION_CORNERS`
  * Now creates a new variable `<violation_type>_VIOLATION_CORNERS` for its
    subclasses. This allows for fine-grained control of the IPVT corners checked
    by each subclass.
  * Now generates errors for violations occuring at `TIMING_VIOLATION_CORNERS`
    (unless the subclass variable override is defined) and generates warnings
    for violations in the rest of the IPVT corners.
* `Checker.HoldViolations`
  * Added `HOLD_VIOLATION_CORNERS` which takes precedence over
    `TIMING_VIOLATION_CORNERS`
* `Checker.SetupViolations`
  * Added `SETUP_VIOLATION_CORNERS` acting similar to `HOLD_VIOLATION_CORNERS`.
* Created `Checker.MaxCapViolations`
  * Reports maximum capacitance violations.
  * Added `MAX_CAP_VIOLATION_CORNERS`. It defaults to `[""]` which is the value
    for matching no corners (i.e. all violations are reported as warnings).
* Created `Checker.MaxSlewViolations`
  * Reports maximum slew violations.
  * Added `MAX_SLEW_VIOLATION_CORNERS`. It defaults to `[""]` which is the value
    for matching no corners (i.e. all violations are reported as warnings).
* `OpenROAD.GlobalPlacementSkipIO`
  * Fixed a bug where `PL_TARGET_DENSITY_PCT` is calculated base on
    `FP_CORE_UTIL` in designs with `FP_SIZING` set to `absolute`. The behavior
    now matches `OpenROAD.GlobalPlacement`.
* `Yosys.*`
  * Verilog files are now read with `-noautowire`. This changes the default
    `default_nettype` to `none`, no longer tolerating implicitly declared wires
    unless `default_nettype` is explicitly set to something else in a particular
    source file.

## Flows

* `Classic`, `VHDLClassic`
  * **API Break**: Removed all `QUIT_ON*` variables from the flow itself
  * Added `Checker.MaxSlewViolations`
  * Added `Checker.MaxCapViolations`

## Tool Updates

* Updated `black` to `23` + matching formatting changes to the code
* Makefile no longer creates venvs for most targets
* Default Nix shell no longer includes development-specific tools (jdupes,
  alejandra, pytest…), new devShell `dev` includes these tools and more

## Testing

* Created two coverage commands in the `Makefile`, one for infrastructure unit
  tests and the other for step unit tests

## Misc. Enhancements/Bugfixes

* `openlane.flows.Flow`:
  * All warnings captured are now printed at the end of the flow à la OpenLane
    1\.
* `openlane.flows.SequentialFlow`:
  * Deferred errors are now handled in the same way normal errors are.
* Various internal environment variables changed from `_lower_snake_case` to
  `_UPPER_SNAKE_CASE` for (relative) consistency
* `openlane.common.TclUtils`
  * Empty strings now escaped as `""`
* `openlane.steps.Step`
  * Printing of last 10 lines of a file now uses a ring buffer instead of
    concatenating then splitting then joining
* `openlane.steps.TclStep`
  * Various handcrafted joins in subclasses now use `TclStep.value_to_tcl` or
    `TclUtils.join`
  * **API Break**: `value_to_tcl` no longer converts dataclasses to JSON,
    rather, they're converted to Tcl dicts
  * **API Break**: `run_subprocess` now intercepts and passes most environment
    variables are now passed indirectly, i.e., a file is made and placed under
    the variable `_TCL_ENV_IN`, which is then to be sourced by scripts. This
    helps avoid the 1 MiB args + env limit in macOS / 2 MiB args + env limit in
    Linux.

## API Breaks

* **API Break**: Removed all `QUIT_ON*` variables from the the `Classic`,
  `VHDLClassic` per se, however they are not translated variables.

## Documentation

* Fixed bug with newcomer's guide (thanks @calvbore)

# 2.0.0b17

## CLI

* Multiple configuration files now supported, incl. mixes of JSON and Tcl files
* Added new flag, `--show-progress-bar/--hide-progress-bar`, also
  self-explanatory
* Added new flag, `--run-example`, which instantiates and runs one of the
  example designs
* Added new flag, `--condensed`, which sets `logging.options.condensed_mode` and
  changes the default for showing the progress bar to `False`
* Added new entry script, `openlane.config`, which allows configuration files to
  be interactively generated
* Fixed bug where 0 config files causes a crash

## Steps

* All steps:
  * Change skipped-step `warn`s to `info` if the skip should not necessarily be
    a cause for alarm
  * Suppressed warnings about dead processes when tracking subprocess resource
    usage
  * Fixed crash when subprocesses emit non-UTF-8 output: Now a proper
    `StepException` is raised
* Created `KLayout.DRC`
  * Only compatible with sky130 (skipped for other PDKs)
* Created `Checker.PowerGridViolations`
  * Raises deferred step error if `design__power_grid_violation__count` is
    nonzero
* Created `Checker.SetupViolations `, `Checker.HoldViolations` to check
  setup/hold timing violations
  * Add config variable `TIMING_VIOLATIONS_CORNERS`, which is a list of
    wildcards to match corners those steps will flag an error on.
* `KLayout.OpenGUI`
  * Added a new boolean config var, `KLAYOUT_EDITOR_MODE` to that enables editor
    mode in KLayout
  * Added new variable `KLAYOUT_PRIORITIZE_GDS`, which as the name implies,
    prioritizes GDS over DEF if there's a GDS in the input state.
  * `cwd` for subprocess set to step directory for convenience
  * Fixed bug where viewer mode was not working
* `Odb.*`, `KLayout.*`
  * Subprocesses now inherit `sys.path` in `PYTHONPATH` which allows `nix run`
    to work properly
* `Odb.ApplyDEFTemplate`
  * Added `FP_TEMPLATE_MATCH_MODE`, with values `strict` (default) or
    `permissive` with `strict` raising an error if any pins are missing from
    either the template or the design.
  * Warn when the template DEF die area is different from the design die area.
  * No longer copies the die area from the DEF template file-- floorplanning
    needs to be executed correctly first. `DIE_AREA`
* `Odb.CustomIOPlacement`
  * Completely re-implemented pin placement file parser in Antlr4 for more
    thorough syntax and semantic checking at
    https://github.com/efabless/ioplace_parser
  * Formalized concept of annotations; documented three annotations:
    `@min_distance`, `@bit_major`, and `@bus_major`.
  * Rewrote `openlane/scripts/odbpy/io_place.py` to rely on the new parser +
    general cleanup
* `Odb.ManualMacroPlacement`
  * Instances missing placement information are no longer treated as errors and
    are simply skipped so it can be passed on to other steps (or if is
    information about a nested macro)
* Created new step `Odb.WriteVerilogHeader`
  * Writes a `.vh` file using info from the layout post-PDN generation and the
    Verilog header
* `OpenROAD.*`
  * Updated to handle `EXTRA_EXCLUDED_CELLS`
  * No longer trimming liberty files, relying on `set_dont_use` instead
* `OpenROAD.CheckAntennas`
  * Added new `antenna_summary.rpt` file with a summary table for antennas
    matching that of OpenLane 1
* `OpenROAD.Floorplan`
  * `PL_TARGET_DENSITY_PCT` default calculation now prioritizes using metric
    `design__instance__utilization` if available.
  * Fixed a crash where obstructions were passed as floats instead of database
    unit integers and caused a crash.
* `OpenROAD.GeneratePDN`
  * Renamed `DESIGN_IS_CORE` to `FP_PDN_MULTILAYER`, which is more accurate to
    its functionality
  * Removed comments about assumptions as to the PDN stack config with regards
    to top-level integrations vs macros: macros can have two PDN layers and a
    core ring
  * Fixed issue where a PDN core ring would still be created on two layers even
    if `FP_PDN_MULTILAYER` is set to false- an error is thrown now
  * Fixed issue where `FP_PDN_VSPACING` is not passed to `add_pdn_stripe` when
    `FP_PDN_MULTILAYER` is set to false (thanks @mole99)
  * **API Break**: `FP_PDN_CHECK_NODES` is no longer a config variable for this
    step. The relevant checks are always run now, however, they do not cause the
    flow to exit immediately, rather, they generate
    `design__power_grid_violation__count ` metrics.
* `OpenROAD.GlobalPlacementSkipIO`
  * Updated to do nothing when `FP_DEF_TEMPLATE` is defined
* `OpenROAD.IOPlacement`
  * Updated to do nothing when `FP_DEF_TEMPLATE` is defined.
* `OpenROAD.IRDropReport`
  * Added `VSRC_LOC_FILES` for IR Drop, printing a warning if not given a value
  * Rewrote internal IR drop script
* `OpenROAD.Resizer*`, `OpenROAD.RepairDesign`
  * `RSZ_DONT_USE_CELLS` removed, added as a deprecated name for
    `EXTRA_EXCLUDED_CELLS`
* `OpenROAD.STAPostPNR`
  * Added hold/setup reg-to-reg worst violation to STA summary table.
  * Added hold/setup tns to STA summary table.
  * Slack values of zero are now highlighted green instead of red.
  * Changed summary table column header from `reg-to-reg` to `Reg to Reg Paths`
    for readability
  * Fixed slacks for `Reg to Reg Paths` only showing negative values.
* `Yosys.*`
  * Updated to handle `EXTRA_EXCLUDED_CELLS`
  * Internally replaced various `" ".join`s to `TclUtils.join`
  * Implementation detail: "internal" variables to be lowercase and prefixed
    with an underscore as a pseudo-convention
  * Turned `read_deps` into one sourced script that is generated by Python
    instead of a Tcl function (as was the case for `.EQY`)
  * For maximum compatibility, priority of views used of macros changed, now, in
    that order it's
    * Verilog Header
    * Netlist/Powered Netlist
    * Lib File
  * Fixed bug where Lighter would not be executed properly
* `Yosys.Synthesis`
  * Updated error for bad area/delay format to make a bit more sense
  * Updated internal `stat` calls to Yosys to pass the liberty arguments so the
    area can be consistently calculated
  * Fixed bug where custom technology maps were not properly applied
  * Removed `SYNTH_STRATEGY` value `AREA 4` -- never existed or worked

## Flows

* All flows
  * Added a `flow.log`, logging at a `VERBOSE` log level
  * Properly implemented filtering for `error.log` and `warning.log`
  * Constructors updated to support multiple configuration files
* Universal Flow Configuration Variables
  * Created `TRISTATE_CELLS`, accepting `TRISTATE_CELL_PREFIX` from OpenLane 1
    with translation behavior
  * Created new PDK variable `MAX_CAPACITANCE_CONSTRAINT`
    * Also added to `base.sdc`
  * Created new variable `EXTRA_EXCLUDED_CELLS`, which allows the user to
    exclude more cells throughout the entire flow
  * Renamed `PRIMARY_SIGNOFF_TOOL` to `PRIMARY_GDSII_STREAMOUT_TOOL` with
    translation behavior
  * Renamed `GPIO_PADS_PREFIX` to `GPIO_PAD_CELLS` with translation behavior
  * Renamed `FP_WELLTAP_CELL` to `WELLTAP_CELL` with translation behavior
  * Renamed `FP_ENDCAP_CELL` to `ENDCAP_CELL` with translation behavior
  * Renamed `SYNTH_EXCLUSION_CELL_LIST` to `SYNTH_EXCLUDED_CELL_FILE` with
    translation behavior
  * Renamed `PNR_EXCLUSION_CELL_LIST` to `PNR_EXCLUDED_CELL_FILE` with
    translation behavior
* `SynthesisExploration`
  * Added new flow, `SynthesisExploration`, that tries all synthesis strategies
    in parallel, performs STA and reports key area and delay metrics
* `Classic`
  * `ApplyDEFTemplate` now takes precedence over `CustomIOPlacement`, matching
    OpenLane 1
  * Added `Checker.PowerGridViolations` to the flow, gated by
    `QUIT_ON_PDN_VIOLATIONS` (which has a deprecated name of
    `FP_PDN_CHECK_NODES`) for back-compat with OpenLane 1 configurations
  * Added `Checker.SetupViolations`, `Checker.HoldViolations` to the end of the
    flow
    * Both gated by `QUIT_ON_TIMING_VIOLATIONS`
    * Each gated by `QUIT_ON_SETUP_VIOLATIONS`, `QUIT_ON_HOLD_VIOLATIONS`
      respectively

## Tool Updates

* Repository turned into a [Flake](https://nixos.wiki/wiki/Flakes) with
  `openlane` as the default output package and the previous shell environment as
  the default output devShell
  * `flake-compat` used so `nix-shell` continues to work as you'd expect for
    classic nix
* All package `.nix` files
  * Now follow the `nixpkgs` convention of explicitly listing the dependencies
    instead of taking `pkgs` as an argument
  * Have a `meta` field
* Reformatted all Nix code using
  [alejandra](https://github.com/kamadorueda/alejandra)
* Updated Open PDKs to `bdc9412`
* Updated OpenROAD to `75f2f32`
  * Added some conveniences for manual compilation to the Nix derivation
* Updated Volare to `0.16.0`/`4732594`
  * New class in API, the `Family` class, helps provide more meaningful error
    reporting if the user provides an invalid PDK variant (and resolves to a
    variant if just a PDK name is provided)
* Updated Yosys to `0.38`/`543faed`
  * Added Yosys F4PGA SDC plugin (currently unused)
* Added KLayout's python module to the explicit list of requirements

## Testing

* Added various [IPM](https://github.com/efabless/ipm) designs to the CI
* Added a full caravel user project example (wrapper + example) to the CI
* Greatly expanded unit tests for individual steps

## Misc. Enhancements/Bugfixes

* Created new folder in module, `examples` which contains example designs (of
  which `spm` is used as a smoke test)
* `__main__`
  * Two new commandline flags added
  * `--save-views-to`: Saves all views to a directory in a structure after
    successful flow completion using `State.save_snapshot`
  * `--ef-save-views-to`: Saves all views to a directory in the Efabless
    format/convention, such as the one used by Caravel User Project.
* `openlane.logging`
  * `LogLevels` is now an IntEnum instead of a class with global variables
  * Create a custom formatter for logging output instead of passing the
    formatting options as text to the logger
  * Created new log level, `SUBPROCESS`, between `DEBUG` and `VERBOSE`, and made
    it the new default
  * Create a separate handler for logs with level `SUBPROCESS` that doesn't
    print timestamps, level, etc
  * New global singleton `options` created, which allows to configure both:
    * `condensed_mode`: boolean to make the logs terser and suppress messages
      with `SUBPROCESS` level unconditionally
    * `show_progress_bar`: boolean, self-explanatory
  * **API Break**: Removed `LogLevelsDict`, LogLevels[] now works just fine
  * Changed all instances of `WARN` to `WARNING` for consistency
  * Fixed bug where `VERBOSE` logging in internal plain output mode simply used
    `print`
* `openlane.state`
  * Added new `DesignFormat`: `VERILOG_HEADER`
* `openlane.common`
  * `Toolbox`
    * Objects no longer create a folder immediately upon construction
    * `remove_cells_from_lib` now accepts wildcard patterns to match against
      cells (to match the behavior of OpenROAD steps)
    * `get_macro_views` can now take more than one `DesignFormat` for
      `unless_exist`
  * New `click` type, `IntEnumChoice`, which turns integer enums into a set of
    choices accepting either the enum name or value
  * New function `process_list_file` to process `.gitignore`-style files (list
    element/comment/empty line)
* `openlane.config`
  * Updated to support an arbitrary number of a combination of Tcl files, JSON
    files and python dictionaries (or any object conforming to `Mapping`) to
    create configuration files, each with their own `Meta` values
  * `design_dir` can now be set explicitly, but if unset will take `dirname` of
    last config file passed (if applicable)
  * Internally unified how Tcl-based configurations and others are parsed
  * `Instance` fields `location`, `orientation` now optional
  * `Macro` has two new views now, `vh` and `pnl`
  * New `DesignFormat` added: * `openlane.config.DesignFormat`
* `openlane.steps`
  * `__main__`
    * Use default `--pdk-root` for `run` command
  * `Step`
    * `load()`'s pdk_root flag can now be passed as `None` where it will default
      to `cwd`
    * New method `load_finished()` to load concluded steps (which loads the
      output state and step directory)
    * `factory`
      * New method `from_step_config()` which attempts to load a step from an
        input configuration file
        * Reworked step-loading function to use `from_step_config()` where
          appropriate
    * `create_reproducible()`
      * Added `flatten` to public API, which flattens the file structure with
        the exception of the PDK, which is saved to `pdk/$PDK`
      * Modified behavior of flatten to allow including the PDK (which isn't
        flattened)
      * Generated `run_ol.sh` now passes ARGV to the final command (backwards
        compatible with old behavior)
        * Primary use for this: `run` command now accepts `--pdk-root` flag
    * Added runtime to `*.process_stats.json`
  * `openlane.flows`
    * Added new instance variable, `config_resolved_path`, which contains the
      path to the `resolved.json` of a run
    * Flows resuming existing runs now load previously concluded steps into
      `self.step_objects` so they may be inspected
* Fixed an issue where Docker images did not properly have dependencies of
  dependencies set in `PYTHONPATH`.
* Fixed a corner case where some OpenLane 1 JSON configs that use Tcl-style
  dicts that include paths would fail conversion to a Python dict
* Fixed a bug with ejected reproducible scripts keeping some nix store paths.
* Fixed Docker images not having `TMPDIR` set by default
* Updated Nix overlays to detect Darwin properly, added another fix for `jshon`
* Updated Nix derivation to ignore `__pycache__` files
* Suppressed tracebacks in more situations (too shouty)
* Removed `PYTHONPATH` from `default.nix` - OpenLane now passes its
  `site-packages` to subprocesses (less jank) (but still a bit jank)

## API Breaks

* Universal Flow Configuration Variables
  * `CTS_ROOT_BUFFER`, `CTS_CLK_BUFFERS` and `CTS_MAX_CAP` all moved to
    `OpenROAD.CTS`
  * `IGNORE_DISCONNECTED_MODULES` moved to `Odb.ReportDisconnectedPins`
  * `GPL_CELL_PADDING` moved to `OpenROAD.GlobalPlacement`
  * `DPL_CELL_PADDING` moved to steps that have the rest of the `dpl` variables
  * `GRT_LAYER_ADJUSTMENTS` moved to steps that have the rest of the routing
    layer variables
  * Moved `GRT_OBS` to `Odb.AddRoutingObstructions` as a deprecated name for
    `ROUTING_OBSTRUCTIONS`
  * Removed `FP_CONTEXT_DEF`, `FP_CONTEXT_LEF`, and `FP_PADFRAME_CFG`: To be
    implemented
  * Removed `LVS_INSERT_POWER_PINS`, `RUN_CVC`, `LEC_ENABLE`,
    `CHECK_ASSIGN_STATEMENTS`
* Moved `DesignFormat`, `DesignFormatObject` from `openlane.common` to
  `openlane.state`
* `openlane.common.Toolbox.remove_cells_from_lib` no longer accepts
  `as_cell_lists` as an argument, requiring the use of `process_list_file`
  instead
* Removed `LogLevelsDict`, `LogLevels[]` now works just fine

## Documentation

* Added Glossary
* Added FAQ
* Added note on restarting Nix after configuring the Cachix substituter
* Added a first stab at (conservative) minimum requirements for running
  OpenLane- you can definitely get away with less at your own risk
* Added extensions to make the documentation better to write and use:
  * `sphinx-tippy` for tooltips
  * `sphinx-copybutton` for copying terminal commands
  * `sphinxcontrib-spelling` so we don't write "Verliog"
* Custom extension so Flows, Steps and Variables can be referenced using custom
  MyST roles
* Added a new target to the `Makefile`, `watch-docs`, which watches for changes
  to rebuild the docs (requires `nodemon`)
* Separated the "Getting Started" guide into a tutorial for newcomers and a
  migration guide for OpenLane veterans
* Changed *all* `.png` files to `.webp` (saves considerable space, around 66%
  per image)
* Updated all Microsoft Windows screenshots to a cool 150% UI scale
* Updated generated documentation for steps, flows and universal configuration
  variable
* Updated Readme to reflect `aarch64` support
* Updated docstrings across the board for spelling and terminology mistakes

# 2.0.0b16

## Steps

* All:
  * Changed type of `DIE_AREA` and and `CORE_AREA` to
    `Optional[Tuple[Decimal, Decimal, Decimal, Decimal]]`
* `KLayout.*`:
  * Propagated `venv` sitepackages to `PYTHONPATH`
  * Rewrote scripts to use either the Python API or use arguments passed via
    `KLAYOUT_ARGV` instead of the weird `-rd` pseudo-serialization
* `KLayout.XOR`:
  * Fixed threads not working properly
  * `KLAYOUT_XOR_THREADS` is now optional, with the thread count being equal to
    your thread count by default
  * Added new variable, `KLAYOUT_XOR_TILE_SIZE`, which is the size of the side
    of a tile in microns (the tile size must be sufficiently smaller than the
    design for KLayout to bother threading)
  * Added `info` prints for thread count
* `Magic.*`:
  * Base `MagicStep` no longer overrides `run`, but does override
    `run_subprocess`
  * `openlane/scripts/magic/common/read.tcl` is now a list of read-related Tcl
    functions used across all Magic scripts
  * Added new variable `MAGIC_CAPTURE_ERRORS` to best-effort capture and throw
    errors generated by Magic.
* `Magic.StreamOut`:
  * Internally set `MAGTYPE` to `mag`
  * Change sequence as follows
    * Old sequence:
      1. Read tech LEF
      1. Read macro LEF views (if applicable)
      1. Read design DEF
      1. Read macro GDS views (if applicable)
      1. Write final GDS
    * New sequence:
      1. Read tech LEF
      1. Read PDK SCL/GDS
      1. Depending on the value of `MAGIC_MACRO_STD_CELL_SOURCE`, if applicable:
         * Read macro GDS views as a black-box
         * Read macro GDS views, de-referencing standard cells (i.e. using PDK
           definitions)
      1. Write final GDS
    * Rationale: The old flow triggers a bug where references for cells inside a
      macro's GDS view were broken broken. A workaround was suggested by Tim
      Edwards and the new flow was adapted from his workaround.
      * Additionally, the new flow is just plain more explicit and
        straightforward.
  * Updated to throw errors when `MAGIC_MACRO_STD_CELL_SOURCE` is set to `macro`
    and:
    * Multiple GDS files are defined per macro
    * A macro's GDS file does not have a PR boundary
* `Odb.*`
  * Added `openlane/scripts/odbpy` to `PYTHONPATH`
  * Propagated `venv` sitepackages to `PYTHONPATH`
  * `openlane/scripts/odbpy/defutil.py`:
    * Added validation for obstruction commands
    * Added exit codes for validation errors in obstruction commands
    * Added a command to remove obstructions
    * Enhanced obstructions regex matching to account for >5 items in an
      obstruction definition.
* Created obstruction-related steps
  * `Odb.AddRoutingObstructions`: Step for adding metal-layer obstructions to a
    design
  * `Odb.RemoveRoutingObstructions`: Step for removing metal-layer obstructions
    from a design.
    * The preceding two steps, and their derivatives, should be used in tandem,
      i.e., obstructions should be added then removed later in the flow.
  * `Odb.AddPDNObstructions`: A subclass of `Odb.AddRoutingObstructions` that
    adds routing (metal-layer) obstructions that apply only to the PDN, using
    the variable `PDN_OBSTRUCTIONS`. Runs before PDN generation.
  * `Odb.RemovePDNObstructions`: A subclass `Odb.RemoveRoutingObstructions` that
    removes obstructions added by `Odb.AddPDNObstructions`.
* `Odb.DiodesOnPorts`, `Odb.HeuristicDiodeInsertion`:
  * Now automatically runs DPL and GRT to legalize after insertion
  * Old behavior kept using new steps: `Odb.PortDiodePlacement` and
    `Odb.FuzzyDiodeInsertion`.
  * Updated underlying script to have some more debugging options/be more
    resilient
  * Fixed a bug where attempting to insert another diode of the same name would
    cause a crash
* `OpenROAD.*`:
  * Added three new entries to set of DesignFormats:
    * `POWERED_NETLIST_SDF_FRIENDLY`
    * `POWERED_NETLIST_NO_PHYSICAL_CELLS`
    * `OPENROAD_LEF`
  * Added `openlane/scripts/odbpy` to `PYTHONPATH`
  * Propagated `venv` sitepackages to `PYTHONPATH`
* `OpenROAD.WriteViews`
  * Writes the aforementioned new design formats
* `OpenROAD.CTS`, `CVCRV.ERC` (unused):
  * Replaced legacy calls to `Step.run` causing crashes in some situations
* Created `OpenROAD.CutRows`
* `OpenROAD.CutRows`, `OpenROAD.TapDecapInsertion`:
  * Renamed `FP_TAP_VERTICAL_HALO` to `FP_MACRO_VERTICAL_HALO`,
    `FP_TAP_HORIZONTAL_HALO` to `FP_MACRO_HORIZONTAL_HALO`
    * Rationale: Halo doesn't only affect tap insertion, it also affects cut
      rows generated in the floorplan. This affects cell insertion and power
      rails and anything related to floorplan and std cell placement.
* `OpenROAD.DetailedRouting`:
  * Added `info` prints for thread count
* `OpenROAD.Floorplan`:
  * Added new variable `FP_OBSTRUCTIONS` to specify obstructions during
    floorplanning
  * Added a new PDK variable, `EXTRA_SITES`, which specifies additional sites to
    use for floorplanning (as overlapping rows) even when:
    * Cells without double-heights are not used
    * Double-height cells with missing or mislabeled LEF `SITE`(s) are used
* Part of `OpenROAD.GlobalRouting` spun off as `OpenROAD.RepairAntennas`
  * Added `OpenROAD.RepairAntennas` to `Classic` flow after
    `Odb.HeuristicDiodeInsertion`; gated by `RUN_ANTENNA_REPAIR` (with a
    deprecated name of `GRT_REPAIR_ANTENNAS` for backwards compat)
* `OpenROAD.IOPlacement`, `OpenROAD.GlobalPlacementSkipIO`
  * Added new value for `FP_IO_MODE` which places I/O pins by annealing
* `OpenROAD.ResizerTiming*`:
  * Added `PL_RESIZER_GATE_CLONING` and `GRT_RESIZER_GATE_CLONING` respectively,
    which control OpenROAD's ability to perform gate cloning while running
    `repair_timing` (default: `true`)
* `OpenROAD.STAPostPNR`
  * Added `timing__unannotated_nets__count` to record number of annotated nets
    reports during post-PnR STA
  * Added `timing__unannotated_nets_filtered__count` which filters the former's
    count based on whether a net has a wire. A wire indicates if a net has
    physical implementation. If a net doesn't have a wire then it can be waived
    and filtered out.
* `Verilator.Lint`:
  * Fixed bug where inferred latch warnings were not properly processed
* `Yosys.*Synthesis`:
  * Per comments from Yosys Team
    [(1)](https://github.com/YosysHQ/yosys/issues/4039#issuecomment-1817937447)
    [(2)](https://github.com/The-OpenROAD-Project/OpenLane/pull/2051#issuecomment-1818876410)
    * Replaced instances of ABC command `rewrite` with `drw -l` with new
      variable `SYNTH_ABC_LEGACY_REWRITE` being set to `true` restoring the
      older functionality (`false` by default)
    * Replaced instances of ABC command `refactor` with `drf -l` with new
      variable `SYNTH_ABC_LEGACY_REFACTOR` being set to `true` restoring the
      older functionality (`false` by default)
  * New variable, `USE_SYNLIG`, enables the use of the Synlig frontend in place
    of the Yosys Verilog frontend for files enumerated in `VERILOG_FILES`
    (disabled **by default**)
  * New variable, `SYNLIG_DEFER`, enables the experimental `-defer` feature (see
    [this part of Synlig's readme](https://github.com/chipsalliance/synlig#example-for-parsing-multiple-files))
    (disabled by default)
  * Underlying scripts reworked to unify how Verilog files, preprocessor
    definitions and top level parameters are handled
  * Exempt SystemVerilog `"$assert"s` from "unmapped cells"
  * Metric `design__latch__count` renamed to `design__inferred_latch__count`
  * Fixed `SYNTH_NO_FLAT` not working.

## Flows

* `Classic` flow
  * `Odb.DiodesOnPorts` and `Odb.HeuristicDiodeInsertion` now run after
    `OpenROAD.RepairDesignPostGRT` (as the latter may create some long wires)
    but still before `Odb.ResizerTimingPostGRT` (as timing repairs take
    priority)
  * `OpenROAD.CheckAntennas` added after `OpenROAD.DetailedRouting`
  * `OpenROAD.CutRows` added before `OpenROAD.TapDecapInsertion`
  * `OpenROAD.AddPDNObstructions` and `OpenROAD.RemovePDNObstructions` now
    sandwich `OpenROAD.GeneratePDN`
* Internally updated implementation of `VHDLClassic` flow to dynamically create
  `.Steps` from `Classic`

## Documentation

* `docs/source/index`:
  * Changed markup language from RST to Markdown
  * Better disambiguation between OpenLane 1 and OpenLane 2
  * Removed reference to unused utilities
  * Hid top-level `toctree` polluting the landing page
  * Fixed links to incorrect repository
* Corners and STA: Now indexed; details some violations
* Updated documentation of `openlane.config.Variable.pdk` to make it a bit
  clearer

## Tool Updates

* Nix:
  * Upgraded Nix Package Pin to `3526897`
  * Added support for `aarch64-linux` and `aarch64-darwin`
  * Created new overlays:
    * `cbc`: Use c++14 instead of the default c++17 (`register` declarations)
    * `lemon-graph`: `sed` patch `register` declaration
    * `spdlog-internal-fmt`: `spdlog` but with its internal `fmt` as the
      external `fmt` causes some problems
    * `clp` to support `aarch64-linux`
    * `cairo`: to enable X11 support on macOS
    * `or-tools`: to use a new SDK on `x86-64-darwin` (see
      [this](https://github.com/NixOS/nixpkgs/issues/272156#issuecomment-1839904283)
    * `clp` to support `aarch64-linux`
  * Reworked Nix derivations for the OpenLane shell, OpenLane, and the Docker
    image
    * Made OpenLane 2's `src` derivation allowlist-based rather than
      gitignore-based (smaller `source` derivations)
    * Added a new argument to `default.nix`, `system`, as
      `builtins.currentSystem` is not available when using nix flakes (where in
      documentation it is described as "non-hermetic and impure": see
      https://nixos.wiki/wiki/Flakes). This change allows passing the system as
      argument and thus restores compatibility with nix flakes.
* Completely revamp Notebook
  * Rewrite Nix setup section to be more tolerant of non-Colab setups
  * Rewrite OpenLane dependencies to use a better method of installing
    OpenLane's dependencies/hack in `tkinter` if it's missing (as it will be on
    local environments)
  * Added descriptions for *all steps used*
  * Added RCX, STAPostPNR, LVS and DRC
* Added [Surelog](https://github.com/chipsalliance/surelog) to the included
  utilities
* Extended CI to handle Linux aarch64 builds
* Excluded yosys-ghdl plugin from ARM-based builds and from macOS - never worked
* Upgraded KLayout to `0.28.13`
  * Made KLayout derivation more orthodox- distinct configure, build and install
    steps
  * Made KLayout Python modules available to all Python scripts
  * macOS: All KLayout Mach-O binaries patched to find the correct dylibs
    without `DYLD_LIBRARY_PATH`
* Upgraded Magic to `83ed73a`
  * Enabled `cairo` support on macOS, which allows Mac users to use the Magic
    GUI
  * Removed `mesa_glu` on macOS
* Fixed Yosys plugins propagating Yosys, causing conflicts
* Updated unit tests to work with some env changes in Python 3.11
* Removed `StringEnum`
* Updated OpenPDKs to `e0f692f`
* Updated OpenROAD to `6f9b2bb`
  * OpenSTA is now built **standalone** just like `openroad-abc` for modularity
    purposes
  * Fixes issue where post-GRT resizing run-time and memory consumption got out
    of hand: see
    https://github.com/The-OpenROAD-Project/OpenROAD/issues/4121#issuecomment-1758154668
    for one example
* Updated Verilator to `v5.018` to fix a couple crashes, including a persistent
  one with `spm` on Apple Silicon
* Updated Volare to `0.15.1`
  * OpenLane now doesn't attempt to `enable` when using `volare`- it points the
    `Config` object to the specific version directory for said PDK
* Updated Yosys to `0.34`/`daad9ed`
  * Added the
    [Synlig Yosys SystemVerilog Plugin](https://github.com/chipsalliance/synlig)

## API Breaks

* `openlane.steps.step.Step.load`: Argument `state_in_path` renamed `state_in`,
  also takes `State` objects
* `openlane.config.Config`:
  * For JSON configurations using `meta.version = 2`, `DIE_AREA` and `CORE_AREA`
    can no longer be provided as strings, and must be provided as an array of
    four numeric elements.
  * Removed global state when `Config.interactive` is used, `state_in` now
    explicitly required
    * Rationale: the little convenience offered is far outdone by the annoyance
      of most steps being non re-entrant, so trying to run the same cell twice
      is almost always a crash.
* `OpenROAD.CTS`:
  * Removed `CTS_TOLERANCE`: no longer supported by OpenROAD
* `OpenROAD.Floorplan`:
  * Removed `PLACE_SITE_HEIGHT` and `PLACE_SITE_WIDTH`: redundant
* `OpenROAD.GlobalRouting`:
  * Removed `GRT_REPAIR_ANTENNAS`. See details above.
* `Odb.DiodesOnPorts`, `Odb.HeuristicDiodeInsertion`:
  * Updated `HEURISTIC_ANTENNA_THRESHOLD` to be a non-optional PDK variable with
    default variables added in `openlane/config/pdk_compat.py`
* `Magic.StreamOut`:
  * Removed `MAGIC_GDS_ALLOW_ABSTRACT`: Bad practice
* Removed `openlane.common.StringEnum`: Use `Literal['string1', 'string2', …]`

## Misc. Enhancements/Bugfixes

* Added exit code propagation when a `StepError` is caused by
  `CalledProcessError`
* Added default Toolbox when Toolbox is not defined for a step
* Created a `.process_stats.json` file for every subprocess that has general
  statistics about a process's total elapsed time and resource consumption
* Created method `openlane.common.Path.startswith`
* Expanded `openlane.common.copy_recursive` to support dataclasses
* `openlane.state.State._repr_html_` to better handle recursive outputs.
* `openlane.config.Config`
  * Fixed bug in private methods where `pdkpath` was not being set in some
    scenarios
  * Fixed `_repr_markdown_` to use correct syntax identifier for YAML in
    Markdown
* Fixes and tweaks for step reproducibles:
  * `openlane.steps create-reproducible` has new flag, `--no-include-pdk`, which
    excludes PDK files from reproducibles and make any reference to them utilize
    `pdk_dir::`
  * Slight internal rework for `openlane.steps.Step.create_reproducible` to
    support flattened file structures suitable for testing
  * Reproducibles now no longer include views of the design not explicitly
    declared in step `.inputs`
* Fixed tuple loading for config variables
* Fixed unit test for tuple loading for config variables
* Fixed missing orientations for MACRO variables

## Testing

* Created step unit testing infrastructure, relying on specially-laid out
  folders that provide input data with the ability to add a per-step input data
  preprocessor and output
  * Requires `--step-rx` flag to be passed to `pytest`
  * Created submodule to host step tests
  * Added step to Nix build that utilizes the step unit testing infrastructure
  * Some space/data duplication avoidance measures: Allow missing `state.json`
    for empty state and creation of `.ref` files
* Created a new internal subcommand, `openlane.steps create-test`, which creates
  a flat reproducible that can be more easily added as a step unit
* Ported `aes_user_project_wrapper` from OpenLane 1
* Added `user_proj_timer` from
  https://github.com/efabless/openframe_timer_example/tree/main/openlane/user_proj_timer
* Changed `manual_macro_placement_test` design to have a macro with orientation
  `FN` as a test for the aforemention
* Enable post-GRT resizer for `aes_core`, `spm` and `aes`
* Disabled latch linting for `salsa20`

# 2.0.0b15

* Added IcarusVerilog as a dependency to OpenLane, and GTKWave as a Nix shell
  dependency
* Added power metric reporting to OpenSTA-based steps
* Updated OpenROAD to `bdc8e94`
* Updated Yosys to 0.33 / `2584903`
  * Changed Yosys build process to use an external ABC as ABC takes 8 billion
    years to build (estimate)
  * Patched Yosys and dependent utilities to use BSD libedit
  * Reimplemented how Yosys plugins work in Nix, so they're all loaded with
    Yosys
    * Added derivations for:
      * [SymbiYosys](https://github.com/YosysHQ/sby)
      * [eqy](https://github.com/YosysHQ/eqy)
      * [Lighter](https://github.com/YosysHQ/eqy)
      * [GHDL Yosys Plugin](https://github.com/ghdl/ghdl-yosys-plugin)
  * Created `Yosys.EQY`, a step based on EQY that runs at the very end of the
    flow comparing the RTL inputs and outputs (disabled by default)
  * Modified `Yosys.Synthesis` to support Lighter, which greatly reduces power
    consumption by clock-gating D-flipflops (disabled by default, set
    `USE_LIGHTER` to true to activate)
  * Created new step, `VHDLSynthesis`
    * Created new experimental flow, `VHDLClassic`, incorporating said step and
      removing Verilog-specific steps
* Latches without `always_latch` are now reported as a lint error if the
  variable `LINTER_ERROR_ON_LATCH` is set to `True` (which it is by default)
  * Added latch design to fastest test set for both supported PDKs
* Fixed a race condition with `openlane/steps/step.py::Step::run_subprocess`
* Fixed a bug where `glob` introduced nondeterminism, as glob returns files in
  an arbitrary order on some filesystems:
  https://docs.python.org/3.8/library/glob.html?highlight=sorted
  * All `glob` results were simply sorted.
* Fixed a bug where `openlane/common/toolbox.py::Toolbox::create_blackbox_model`
  constructs and uses an invalid Path.
* Fixed `Checker.YosysSynthChecks` ID to match class name
* Fixed `Odb.SetPowerConnections` missing from step factory
* Fixed `OpenROAD.GlobalRouting` missing `GRT_ANTENNA_MARGIN` from OpenLane 1
* Fixed `Verilator.Lint` incorrectly calling Verilator by appending the list of
  defines to the list of files
* Renamed `SYNTH_DEFINES` to `VERILOG_DEFINES` with translation behavior
* Renamed `SYNTH_POWER_DEFINE` to `VERILOG_POWER_DEFINE` with translation
  behavior
* Removed `SYNTH_READ_BLACKBOX_LIB`, now always loaded

# 2.0.0b14

* Added `PNR_SDC_FILE` to all OpenROAD steps
* Added `SIGNOFF_SDC_FILE` to `OpenROAD.STAPostPNR`
* Added `report_design_area_metrics` to OpenROAD scripts that potentially modify
  the layout
* Added comprehensive documentation on PDKs
* Added documentation for migrating the Macro object
* Added validation for unknown keys for the Macro object
* Added testing for `openlane.common.toolbox::Toolbox::create_blackbox_model`,
  `openlane.common.toolbox::Toolbox::get_lib_voltage`,
  `openlane.flows.sequential::SequentialFlow::__init_subclass__`=
* Updated OpenROAD to `0a6d0fd`: **There is an API break in OpenDB APIs**:
  * `odb.read_def` now takes a `dbTech` and a Path string instead of a
    `dbDatabase` and a Path string.
  * The `dbTech` object can be obtained via the `getTech` method on `dbDatabase`
    objects: `db.getTech()`, for example.
  * Liberty files without default operating conditions break in PSM-
    `libparse-python` added as a workaround until the PDKs are fixed
* `BASE_SDC_FILE` renamed to `FALLBACK_SDC_FILE` with translation
  * Move `FALLBACK_SDC_FILE` to universal flow variables
* OpenROAD scripts internally now always read `SDC_IN` instead of `CURRENT_SDC`
  * SDC_IN set to either `PNR_SDC_FILE` or `SIGNOFF_SDC_FILE` by the appropriate
    steps
* Reimplemented I/O placement in the Classic flow based on the one in ORFS,
  i.e.:
  > "We start the loop in ORFS by ignoring io placement while doing global
  > placement, then do io placement, then re-run global placement considering
  > IOs. Its not perfect but that's the use." - @maliberty
* `open_pdks` -> `dd7771c`
* Volare -> `0.12.8`
* Changed gf180mcu tests to use `gf180mcuD`, the new recommended variant of
  gf180mcu
* Fixed bug with gating config variables with wildcards only affecting the first
  matching step
* Fixed detecting if `PL_TARGET_DENSITY_PCT` is not defined
* Fixed antenna repair: now re-legalizes after repair which was missing
  * Fixed failing designs in Extended Test Set

# 2.0.0b13

* Add Linting
  * Added Nix derivation for:
    [Verilator](https://github.com/verilator/verilator)
  * Added the following steps:
    * `Verilator.Lint`
    * `Checker.LintTimingConstructs`
    * `Checker.LintWarnings`
  * Emplaced the three new steps at the beginning of the flow
  * Added `Classic` flow variable:
    * `RUN_LINTER` w/ deprecated name (`RUN_VERILATOR`)
  * Added step variables:
    * `QUIT_ON_LINTER_ERRORS` -w/ deprecated name (`QUIT_ON_VERILATOR_ERRORS`)
    * `QUIT_ON_LINTER_WARNINGS` w/ deprecated name
      (`QUIT_ON_VERILATOR_WARNINGS`)
    * `QUIT_ON_LINTER_TIMING_CONSTRUCTS`
    * `LINTER_RELATIVE_INCLUDES` w/ deprecated (`VERILATOR_REALTIVE_INCLUDES`)
    * `LINTER_DEFINES`
  * Added metrics:
    * `design__lint_errors__count`
* Added support for `Flow`-specific configuration variables
  * Added a `config_vars` property to `Flow`
  * Added a `gating_config_vars` property to `SequentialFlow`, essentially
    replacing `flow_control_variable` (breaking change) with deprecation
    warnings for the latter
  * Added more consistent runtime handling of "abstract class properties"
  * Folded *all* OpenLane 1-style `RUN_` variables into Classic Flow
* Added an undocumented CVC step- upstream no longer supporting CVC in flows
* open_pdks -> `1341f54`
* yosys -> `14d50a1` to match OL1
* Restored ancient `{DATA,CLOCK}_WIRE_RC_LAYER` variables, with translation
  behavior from `WIRE_RC_LAYER` to `DATA_WIRE_RC_LAYER`
* Created new PDK variable `CELL_SPICE_MODELS` to handle .spice models of the
  SCLs instead of globbing in-step
* Changed default value of `MAGIC_DRC_USE_GDS`
* Fixed an issue where CI would fail when `vars.CACHIX_CACHE` is not defined
  (affected pull requests)
* Fixed an issue with Nix in environment surveys
* Fixed an issue where `openlane/scripts/openroad/pdn.tcl` used a deprecated
  name for a variable
* Fixed a bug where KLayout category names were lacking enclosing single quotes
* Fixed a number of broken links and entries in the documentation

# 2.0.0b12

* Added diode padding to `dpl_cell_pad.tcl`
* Added `FULL_LIBS` to `YosysStep` without any redactions
* Moved all PDN variables to the the `OpenROAD.GeneratePDN` step as
  step-specific PDK variables
* Updated PDN documentation to make sense and added an illustrated diagram of
  values
* Slightly reordered Classic Flow so detailed placement happens right after
  `Odb.HeuristicDiodeInsertion`
* Fixed translation of `FP_PDN_MACRO_HOOKS` when a string is provided (only
  splitting if a `,` is found)
* Removed extraneous `check_placement -verbose` after `common/dpl.tcl` sources
  in OpenROAD scripts

# 2.0.0b11

* Added new `mag` format to design formats, populated by `Magic.StreamOut`
* Added support for `stdin` in reproducibles (mainly for Magic): ejected
  reproducibles now save the input and use it
* Added three new PDK variables to all Magic-based steps: `MAGIC_PDK_SETUP`,
  `CELL_MAGS`, and `CELL_MAGLEFS`, which explicitly list some files Magic
  constructed from `PDK_ROOT`, as well as codifying a convention that variables
  must explicitly list files being used.
* Added new variable to `Magic.SpiceExtraction`, `MAGIC_EXT_ABSTRACT`, which
  allows for cell/submodule-level LVS rather than transistor-level LVS.
* Changed SPEF file saving to only strip asterisks instead of underscores as
  well, matching the folders
* Fixed an issue where OpenLane's type-checking only accepted a single value for
  Literals in violation of
  ["Shortening unions of literals," PEP-586](https://peps.python.org/pep-0586/#shortening-unions-of-literals)
* Fixed an issue where command-line overrides were still treated as strict
  variables
* Fixed an issue where `rule()` would print a line even when log levels would
  not allow it
* Fixed an issue where `PDK_ROOT` was of type `str`
* Updated documentation to provide information on conventions for declaring
  variables
  * Deprecated `StringEnums`, now favoring `Literal['str1', 'str2', …]`

# 2.0.0b10

* Add new commandline options: `--docker-tty/--docker-no-tty`, controlling the
  `-t` flag of Docker and compatible container engines which allocates a virtual
  tty
* Convert CI to use `--dockerized` instead of a plain `docker run`

# 2.0.0b9

* `Flow.start()` now registers two handlers, one for errors and one for
  warnings, and forwards them to `step_dir/{errors,warnings}.log` respectively
* Created `CELL_SPICE_MODELS` as a PDK variable to handle .spice models of the
  SCLs instead of globbing in-step
* Added a "dummy path" for macro translation purposes that always validates and
  is ignored by `self.toolbox.get_macro_views`
* Reduced reliance on absolute paths
  * Special exception carved out for `STEP_DIR`, `SCRIPTS_DIR`
  * Made KLayout scripts more resilient to relative pathing
* Created new "eject" feature, which would make reproducibles for steps relying
  on subprocesses independent of OpenLane
  * `scripts` directory copied in entirety into ejected reproducibles
* Updated Open PDKs to `e3b630d`
* Updated Yosys to `14d50a1`
* Updated CI to handle missing `vars.CACHIX_CACHE`
* Updated Volare to `0.12.3` to use new authentication and user agent
* Downgraded Magic to `0afe4d8` to match OL1
* Restored ancient `{DATA,CLOCK}_WIRE_RC_LAYER` variables, with translation
  behavior from `WIRE_RC_LAYER` to `DATA_WIRE_RC_LAYER`
* Fixed issue with `Step.load()` re-validating values, which affected
  reproducibles
* Timing signoff no longer prints if log level is higher than `VERBOSE`
* Use `parse_float=Decimal` consistently when loading JSON strings to avoid fun
  floating point errors
* Removed dependency on State module from `odb` scripts
* Removed custom PYTHONPATH setting from `OdbStep` (which was mostly to mitigate
  problems fixed in #86)

# 2.0.0b8

* Rename incorrectly-named metric rename `clock__max_slew_violation__count` to
  `design__max_slew_violation__count`
* Fix clock skew metric aggregation by using `-inf` instead of `inf`

# 2.0.0b7

* Internally reworked `Config` module
  * `Variable` objects now have a Boolean property, `.pdk`, which is set to
    `True` if the variable is expected to be provided by the PDK
  * List of common flow variables now incorporate both option config variables
    *and* PDK config variables, with the aforementioned flag used to tell them
    apart.
  * Individual `Step`s may now freely declare PDK variable, with the implication
    that if a `Flow` or one of its constituent `Step`s has one or more variables
    not declared by the current PDK, the `Step` (and `Flow`) are incompatible
    with the PDK.
  * Mutable data structures are used during the construction of `Config` to
    avoid constant copying of immutable dictionaries
    * Multiple private instance methods converted to private `classmethod`s to
      deal with mutable data structures instead of constantly making `Config`
      copies
  * Getting raw values from the PDK memoized to avoid having to call the Tcl
    interpreter repeatedly
  * All `Step` objects, not just those used with an interactive configuration,
    can now be given overrides upon construction using keyword arguments.
* A number of previously-universal PDK variables are now declared by the `Step`s
  and made non-optional, i.e., the `Step` can expect them to be declared by the
  PDK if the configuration is successfully validated.
* `PDK`, `PDK_ROOT` are no longer considered "PDK" variables as PDK variables
  depend on them
* `PRIMARY_SIGNOFF_TOOL` now a PDK variable and a string so OpenLane is not
  limited to two signoff tools
* `Toolbox.render_png()` now relies on a new `Step` called `KLayout.Render`
* `Config.interactive()` fixed, new Nix-based Colab notebook to be uploaded
  Soon™
* Assorted documentation updates and bugfixes

# 2.0.0b6

* Added `Odb.ApplyDEFTemplate` to `Classic` Flow
* Added `RUN_TAP_DECAP_INSERTION` as a deprecated name for
  `RUN_TAP_ENDCAP_INSERTION`

# 2.0.0b5

* Added `refg::` to documentation
* Fixed issue where "worst clock skew" metrics were aggregated incorrectly
* Fixed issue with referencing files outside the design directory

# 2.0.0b4

* Updated documentation for `run_subprocess`
* Updated Volare to `0.11.2`
* Fixed a bug with `Toolbox` method memoization
* Unknown key errors only emit a warning now if the key is used as a Variable's
  name *anywhere* linked to OpenLane. This allows using the same config file
  with multiple flows without errors.

# 2.0.0b3

* Added ability to create reproducible for any step using instance method
  `Step.create_reproducible()`
* Added ability to load and run Step from Config and State JSON files, working
  for both existing step folders and new reproducibles
* Added new CLI- under either the script `openlane.steps` or
  `python3 -m openlane.steps`, exposing the two functionalities above.
* Added internal ability to load a Config without attempting to load the PDK
  configuration data- i.e., only rely on the user's input
* Extended `Meta` objects to support Step ID and OpenLane version.
* Moved tests from source tree to `test/` folder, refactoring as necessary
* Internal `utils` module folded into `common` module, with elements publicly
  documented
* Removed `tcl_reproducible`

# 2.0.0b2

* Updated Magic to `952b20d`
* Added new variable, `MAGIC_EXT_SHORT_RESISTOR` to `Magic.SpiceExtraction`,
  disabled by default

# 2.0.0b1

* Added unit testing and coverage reporting for core infrastructure features
  (80%+)
* Added running unit tests in the CI for different Python versions
* Moved CI designs out-of-tree
* Various documentation improvements
* Common Module
  * Created new TclUtils to handle common Tcl interactions, i.e., evaluating the
    environment and testing
  * Made Tcl environment evaluation no longer rely on the filesystem
  * Made Tcl environment evaluation restore the environment after the fact
  * Moved `Path` from State module to common
  * Moved parsing metric modifiers and such from Toolbox
* Config Module
  * Updated PDK migration script to be a bit more resilient
  * Fixed bug where `meta` did not get copied properly with `Config` copies
  * Rewrote configuration dictionary preprocessor again
* Flow Module
  * Sequential flows now handle duplicate Step IDs by adding a suffix
* Logging Module
  * Logging rewritten to use Python logger with rich handler, the latter of
    which suppressed during unit testing
* State Module
  * `State.save_snapshot()` now also saves a JSON representation of metrics
  * Fixed metric cloning
* Step Module
  * Report start/end locii also end up in the log file
  * Utils
  * DRC module now uses `.` to separate category layer and rule in name

# 2.0.0a55

* Updated OpenROAD to `02ea75b`
* Updated Volare to `0.9.2`
* Added guide on updating utilities with Nix

# 2.0.0a54

* Updated Magic to `0afe4d8`:

```
Corrected an error introduced by the code added recently for support

of command logging, which caused the "select cell <instance>" command
option to become invalid;  this command option is used by the
parameterized cell generator and makes it impossible to edit the
parameterized cells.
```

# 2.0.0a53

* Reworked Tcl unsafe string escaping to use home-cooked functions instead of
  "shlex"

# 2.0.0a52

* Added three designs to the gf180mcu test set
* Magic GDS writes now check log for `Calma output error` before proceeding
  further
* Moved constraint variables to PDK
  * `SYNTH_CAP_LOAD` renamed to `OUTPUT_CAP_LOAD`
* Deprecated names for variables now take priority: allows overriding PDK
  variables properly
* Updated Magic to `8b3bb1a`
* Updated PDK to `78b7bc3`
* Updated Volare to `0.8.0` to support zstd-compressed PDKs
* Temporarily removed `manual_macro_placement_test` from the sky130 test set
  pending a weird bug

# 2.0.0a51

* Updated Netgen to `87d8759`

# 2.0.0a50

* JSON configuration files with `meta.version: 2` and dictionary configurations
  now both subject to stricter validation
  * Strings no longer automatically converted to lists, dicts, numbers,
    Booleans, et cetera
  * Numbers no longer automatically converted to Booleans
  * Unrecognized keys throw an error instead of a warning
* Steps now only keep a copy of configuration variables that are either common
  or explicitly declared
  * Explicitly declare global routing variables for resizer steps
  * Explicitly declare MagicStep variables for DRC step
* `CLOCK_PORT` type changed from `Optional[List[str]]` to
  `Union[str, List[str], None]`
* JSON globs behavior adjusted, now always returns `List` - conversion handled
  after preprocessing
* Rewrote `resolve.py` as a proper preprocessor
  * Proper recursion into Mappings and Sequences (so refs:: may be resolved in
    arbitrarily deep objects)
  * Defer most validation and conversion to `Config` object
* Fixed internal issue where `some_of` of a Union with more than two variables
  of which one is `None` just returns the same Union
* Fixed issue where `expr::` turns results into strings
* `µ`niformity, now all use `U+00B5 MICRO SIGN`
* Removed default values that `ref::`/`expr::` other variables
* Removed unused variable

# 2.0.0a49

* Made designs synthesized by Yosys keep their name after `chparam`

# 2.0.0a48

* Created `openlane.flows.cloup_flow_opts`, which assigns a number of `cloup`
  commandline options to an external function for convenience.
* Moved handling of `last_run` inside `Flow.start`
* Moved handling of volare, setting log level and threadpool count to
  `cloup_flow_opts`

# 2.0.0a47

* Update Magic, Netgen, and Yosys
* Made `SYNTH_ELABORATE_ONLY` functional
* Minor internal rearchitecture of `common` and commandline options

# 2.0.0a46

* Start on API cleanup in preparation for beta
* Common and Logging isolated into own modules
* Improved documentation on various parts of the codebase.
* Delineated `public`, `private` and `protected` class members:
  * If undocumented or starts with `__`, private
  * If decorated with `@openlane.common.protected`, protected
  * Else public
* Class members renamed to reflect the above
* Adjusted documentation generation to use RST and proper titles
* Flow progress bar hooks encapsulated in new `FlowProgressBar` object
  * Old methods still exist, issue a `DeprecationWarning`

## API Breaks

* Top level `import openlane` now only has the version. To get access to `Flow`
  or `Step`, try `from openlane.flows import Flow`
* `Flow.get`/`Step.get` no longer exist: use
  `Flow.factory.get`/`Step.factory.get` instead
* `openlane.common.internal` decorator replaced with `openlane.common.protected`
* `Step` objects no longer hold a reference to parent flow
  * `Step.start` now takes `self.step_dir` as a required argument when running
    non-interactive flows
  * A faster migration method inside a Flow is `step.start()` ->
    `self.start_step(step)`

# 2.0.0a45

* Made Magic DRC report parser more robust, handling multiple rules, etc
* Updated documentation for various related variables
* Fixed bug causing PNR-excluded cells being used during resizer-based OpenROAD
  steps

# 2.0.0a44

* Added support for multiple corners during CTS using the `CTS_CORNERS` variable
* Added support for multiple corners during resizer steps using the
  `RSZ_CORNERS` variable
* Internally reworked OpenROAD resizer and CTS steps to share a common base
  class

# 2.0.0a43

* Added `io_placer` and `manual_macro_placemnt_test` to CI
* Fixed `MAGTYPE` for `Magic.WriteLEF`
* Fixed bug with reading `EXTRA_LEFS` in Magic steps

# 2.0.0a42

* Added support for instances to `RSZ_DONT_TOUCH_RX`
* Added support for `RSZ_DONT_TOUCH_LIST` to resizer steps
* `inverter` design used to configure the above two
* Added ignore for `//` key in JSON config files
* Added two new variables for `Yosys.Synthesis`; `SYNTH_DIRECT_WIRE_BUFFERING`
  and `SYNTH_SPLITNETS`
* Fixed bug with Yosys report parsing
* Fixed issue in `usb_cdc_core` masked by aforementioned bug

# 2.0.0a41

* Updated Magic to `9b131fa`
* Updated Magic LEF writing script
* Ensured consistency of Tcl script logging prefixes

# 2.0.0a40

* Fixed a bug with extracting variables from Tcl config files when the variable
  is already set in the environment
* Fixed a bug with saving lib and SDF files
* Fixed `check_antennas.tcl` being mis-named

# 2.0.0a39

* Added mechanism for subprocesses to write metrics via stdout,
  `%OL_METRIC{,_I,_F}`, used for OpenSTA
* Added violation summary table to post-PNR STA
* Reworked multi-corner STA: now run across N processes with the step being
  responsible for aggregation
* Made handling `Infinity` metrics more robust
* Fixed names of various metrics to abide with conventions:
  * `magic__drc_errors` -> `magic__drc_error__count`
  * `magic__illegal__overlaps` -> `magic__illegal_overlap__count`
* Removed splash messages from OpenROAD, OpenSTA

# 2.0.0a38

* Added full test-suite added to CI
  * Like OpenLane 1, a "fastest test set" runs with every PR and an "extended
    test set" runs daily
* Added Nix building, intra-CI caching and installation as composite actions
  * Nix derivation now cached intra-CI even if running without access to secrets
  * Fixed issue where channel was mis-named
  * Smoke test on all platforms using `nix-shell`
* Docker image re-implemented: One layer with proper settings for PATH and
  PYTHONPATH
  * Docker image smoke-tested independently of Nix
* Fixed bug with Tcl configurations
* Fixed issue with `Yosys.Synthesis` producing false-positive checks
* Updated various design configs

# 2.0.0a37

* Added `MAX_TRANSITION_CONSTRAINT` to `base.sdc` (if set)
* Added `MAX_TRANSITION_CONSTRAINT` -> `SYNTH_MAX_TRAN` translation behavior in
  `base.sdc`
* Removed attempt(s) to calculate a default value for
  `MAX_TRANSITION_CONSTRAINT` in `all.tcl`, `openroad/cts.tcl` and
  `yosys/synth.tcl`

# 2.0.0a36

* Added a commandline option `-j/--jobs` to add a maximum cap on subprocesses.
* Added a global ThreadPoolExecutor object for all subprocesses to `common`.
  * Accessible for external scripts and plugins via `openlane.get_tpe` and
    `openlane.set_tpe`
* Folded `--list-plugins` into `--version`
* Renamed `ROUTING_CORES` to `DRT_THREADS`
* Removed `RCX_CORES`, step now uses global ThreadPoolExecutor

# 2.0.0a35

* Revert magic to
  [`a33d7b7`](https://github.com/RTimothyEdwards/magic/commit/a33d7b78b54d8456769d08236f91f9be31784267),
  last known-good version before a LEF writing bug

# 2.0.0a34

* Added ability to disable reproducibles on a per-class level
* Updated SDF to support N-corners
* Fixed bug with writing LIB/SDF views

# 2.0.0a33

* Bump supported PDK to `af34855`
* Rename 3 PDK variables to match OpenLane 1
  * `FP_PDN_RAILS_LAYER` -> `FP_PDN_RAIL_LAYER`
  * `FP_PDN_UPPER_LAYER` -> `FP_PDN_HORIZONTAL_LAYER`
  * `FP_PDN_LOWER_LAYER` -> `FP_PDN_VERTICAL_LAYER`

# 2.0.0a32

* Better adherence to class structure and mutability principles
  * Create `GenericDict`, `GenericImmutableDict` to better handle immutable
    objects, i.e. `State`, `Config`
  * `State`, `Config` made immutable post-construction
    * Various rewrites to accommodate that
  * `Step`:
    * `.run`:
      * No longer has any default implementation
      * Is expected to return a tuple of **views updates** and **metrics
        updates** which are then applied to copies by `.start` to meet
        mutability requirements
    * `.start`:
      * Handles input checking
      * Handles creating new `State` object based on deltas
  * `Flow`
    * Stateful variables for `.start`, `.run`, and other internal methods made
      private
    * `.start` now only returns the final state object
    * Intermediate steps stored in `self.step_dir`
    * `self.step_dir` and other "mutations" to Flow object have no effect on
      future `.start()` invocations, which are (more or less) idempotent
  * Remove `ConfigBuilder` and fold methods into `Config`
* Added `make host-docs` to Makefile

# 2.0.0a31

* Replace OpenSTA binary name check with an environment variable, `OPENSTA`

# 2.0.0a30

* Added ability to use `--dockerized` without further arguments to drop into a
  shell
* Reimplemented `--dockerized` - needs to be the first argument provided
* Reimplemented `--smoke-test` to not use a subprocess
  * `--smoke-test` doesn't attempt to handle `--dockerized` on its own anymore
* Fixed permissions bug when running a smoke test from a read-only filesystem
* Fixed race condition for temporary directories on macOS (and presumably
  Windows)

# 2.0.0a29

* Added run-time type checkers for `SequentialFlow` `Substitute` dictionary
* Folded `init_with_config` into constructor and deprecate it
* Fixed `SequentialFlow` step substitution bug by moving variable compilation to
  instance instead of class

# 2.0.0a28

* Added missing macro orientations
* Added missing `PDN_CFG` configuration variable
* Fixed crash when defining `SYNTH_READ_BLACKBOX_LIB`
* Streamlined all `read` messages in OpenROAD scripts and macro-related `read`
  messages in Yosys scripts.
* Cleaned up `YosysStep` hierarchy
* Cleaned up `synthesize.tcl`

> Thanks [@smunaut](https://github.com/smunaut) for the bug reports!

# 2.0.0a27

* Added `cloup` library for better argument grouping/prettier `--help` with
  click
* Added ability to substitute steps with a certain `id` in a `SequentialFlow`
  with other Step classes
* Added `--only`, `--skip` to commandline interface for `SequentialFlow`s
* Changed processing of how `--from` and `--to` are done in `SequentialFlow`s
* Better delineation of class vs. instance variables in documentation
* Type checker now also checks functions without typed headers
* Fixed minor bugs with `Decimal` serialization and deserialization
* Class/step registry now case-insensitive
* Moved documentation dependencies to separate requirements file
* Removed `jupyter` from `requirements_dev.txt`- too many dependencies and can
  just be installed with `pip install jupyter`
* Various documentation improvements and fixes

# 2.0.0a26

* Yosys steps now read macro netlists as a black-box if applicable
* Renamed STA steps to avoid ambiguity

# 2.0.0a25

* Made optional/default handling more straightforward to fix issue where the
  default value of an Optional is not None.
* Fixed config var inheritance issue for `OpenROAD.ParasiticsSTA`

# 2.0.0a24

* Add support for gf180mcuC to PDK monkey-patch procedure
* Update some PDK variables to be optional: `GPIO_PADS_LEF`,
  `IGNORE_DISCONNECTED_MODULES`
* Remove unused PDK variable: `CELL_CLK_PORT`

# 2.0.0a23

* Added warning on multiple clocks in `base.sdc`
* Added usage of translation hook for SDC scripts
  * Folded `sdc_reader.tcl` into `io.tcl`
* Fixed calculation issue with I/O delays in `base.sdc`
* Fixed SPEF read invocation to include instance path
* Renamed multiple functions in `io.tcl` for clarity and to avoid aliasing Tcl
  built-in functions
* Tcl reproducibles now add entire environment delta vs. just "extracted"
  variables
  * Better handling of objects inside the design directory

# 2.0.0a22

* Fixed a bug with initializing configurations using dictionaries.
* Added exception message for `InvalidConfig`.

# 2.0.0a21

* Created a (very) rudimentary plugin system
  * Add ability to list detected plugins with flag `--list-plugins`
* Fixed a problem with reading SPEF files for macros
* Various documentation updates

# 2.0.0a20

* Created a `Macro` definition object to replace a litany of variables.
  * `libs`, `spefs` and `sdf` files now use wildcards as keys, which will be
    matched against timing corners for loading, i.e., a SPEF with key `nom_*`
    will match timing corner `nom_tt_025C_1v80`.
    * This has been applied to PDK lib files, RCX rulesets and technology LEF
      files as well.
    * `Toolbox` object now has methods for matching the proper LIB/SPEF files.
* PDKs now list a `DEFAULT_CORNER` for picking LIB files as well as a list of
  `STA_TIMING` corners.
* Expanded the range of valid types for `Variable`: these new classes are
  supported, all with theoretically infinite nesting:
  * `Dict`
  * `Union`
  * `Literal`
* `State` rewritten to support nested dictionaries and type annotations.
  * (Subclass of `Mapping`- Python 3.8 does not support subscripting `UserDict`.
    Yep.)
* Created a `config.json` for the caravel_upw example for testing purposes.
* Updated Magic, add new patch for Clang
* `self.state_in` is now always a future for consistency, but `run()` now takes
  a `state_in` which is guaranteed to be resolved.
* `EXTRA_LEFS`, `EXTRA_LIBS`, etc kept as a fallback for consistency.
* Remove `STA_PRE_CTS`- STA now always propagates clocks

# 2.0.0a19

* Created new metric `synthesis__check_error__count` with a corresponding
  Checker, with said Checker being the new executor of the
  `QUIT_ON_SYNTH_CHECKS` variable
  * Check report parser imported from OpenLane 1
* Created `SYNTH_CHECKS_ALLOW_TRISTATE` to exclude unmapped tribufs from
  previous metric.
* Created new metric `design__xor_difference__count` with a corresponding
  Checker to flag a deferred error on XOR differences.
* Fixed a few typos.

# 2.0.0a18

* Updated the smoke test to support PDK downloads to a different directory.
* Updated config builder to resolve the PDK root much earlier to avoid an issue
  where a crash would affect the issue reproducible.
* Updated `SYNTH_READ_BLACKBOX_LIB` to read the full `LIB` variable instead of
  `LIB_SYNTH`, which also fixes a crash when reading JSON headers.
* Updated post-GRT resizer timing script to re-run GRT before the repair: see
  https://github.com/The-OpenROAD-Project/OpenROAD/issues/3155
* Added a "yosys proc" to the JSON header generator (thanks @smnaut)
* Fixed a bug where random equidistant mode did not work for OpenROAD IO placer.

# 2.0.0a17

* Fixed a crash when the SCL is specified via command-line.
* Fixed a changelog merge nightmare.

# 2.0.0a16

* Reimplement DRC database using `lxml`
* Makefile `venv` creation updated
* Misc. aesthetic bugfixes for sequential flows

# 2.0.0a14

* Add steps to extract, preserve and check power connections:
  * `Checker.DisconnectedPins`: Checker for `ReportDisconnectedPins`.
  * `Odb.ReportDisconnectedPins`: Report disconnected instance pins in a design.
  * `Yosys.JsonHeader`: RTL to a JSON Header.
  * `Odb.SetPowerConnections`: Uses JSON generated in `Yosys/JsonHeader` and
    module information in Odb to add global connections for macros in a design.
* Add `IGNORE_DISCONNECTED_MODULES` as a PDK variable, as some cells need to be
  ignored.
* Rename `SYNTH_USE_PG_PINS_DEFINES` to `SYNTH_POWER_DEFINE`.
* Rename `CHECK_UNMAPPED_CELLS` to `QUIT_ON_UNMAPPED_CELLS`.
* Rename various metrics.
* Change various configuration variables for included `caravel_upw` design.
* Fix `DIODE_INSERTION_STRATEGY` translations
* Allow overriding from CLI when using Tcl configuration files.

# 2.0.0a13

## Documentation

* Built-in flows now have full generated documentation akin to steps.
* Built-in steps now document their inputs, outputs and each built-in step has a
  human-readable text description.
* Rewrite the RTL-to-GDS guides.
* Add an architectural overview of OpenLane 2+.
* Document pin config file format.
* Add guides on writing custom flows AND custom steps.
* Add a migration guide from OpenLane 1.
* Port contributor's guide from OpenLane 1.
* Removed default values from Jupyter Notebook.

## Functional

* `Config` is now immutable, `.copy()` can now take kwargs to override one or
  more values.
* `TapDecapInsertion` -> `TapEndcapInsertion` (more accurate)
* Dropped requirement for description to match between two variables to be
  "equal:" It is sometimes favorable to have a slightly different description in
  another step.
* `OpenInKLayout`/`OpenInOpenROAD` turned into sequential flows with one step
  instead of hacks.
* Fixed a bug where `OpenInKLayout` would exit instantly.
* Updated and fixed `Optimizing` demo flow, as well as delisting it.
* Port https://github.com/The-OpenROAD-Project/OpenLane/pull/1723 to OpenLane 2.
* Remove `Odb.ApplyDEFTemplate` from default flow.

# 2.0.0a12

* Fixes a bug where if OpenLane is invoked from the same directory as the
  design, KLayout stream-outs would break.

# 2.0.0a11

* Update OpenROAD, Add ABC patch to use system zlib
* Adds SDC files as an input to `OpenROADStep`, `NetlistSTA` and `LayoutSTA`
  steps
* Add `sdc_reader.tcl`: a hook script for reading in SDC files while handling
  deprecated variables
* Replace deprecated variables in base.sdc
  * Properly use TIME_DERATING_CONSTRAINT in base.sdc
  * Properly use SYNTH_DRIVING_CELL in base.sdc
  * Properly use SYNTH_CLK_DRIVING_CELL in base.sdc

# 2.0.0a10

* Add `wrapper.tcl` to capture errors in Magic scripts.
* Fix instances of a deprecated variable was used in Magic scripts.

# 2.0.0a9

* Add port diode insertion script.
* Fix formula for calculating `FP_TARGET_DENSITY_PCT`.

# 2.0.0a8

* Update `volare` dependency.
* Update `magic` version + make `magic` nix derivation more resilient.

# 2.0.0a7

* Add the custom diode insertion script as a `Step` (disabled by default).
* `Flow` objects are now passed explicitly to child `Step` objects, removing
  earlier stack inspection code.
* `flow_config_vars` now only affect steps running inside a Flow.

# 2.0.0a6

* Add validation on step exit.

# 2.0.0a5

* Fix a small path resolution issue.

# 2.0.0a4

* Add basic CI that builds for Linux, macOS and Docker
* Various improvements to Dockerization so that `openlane --dockerized` can run
  on Windows

# 2.0.0a3

* Fixed an issue where KLayout scripts exited silently.

# 2.0.0a2

* Handle `PDK_ROOT`, `PDK` and `STD_CELL_LIBRARY` environment variables.
* Unify environment inspection by using `os.environ`- eliminated getenv
* KLayout scripts no longer accept environment variables.
* Updated Docker images for consistency.
* Added ReadTheDocs configuration.

# 2.0.0a1

* Update smoke test
* Fix bug with default variables

# 2.0.0dev15

* `log` -> `info`
* Add mitigation for KLayout None variables.
* `logging` isolated from `common` into its own module
* CLI now accepts either a value or a string for log levels.
* CLI now prints help if no arguments are provided.
* Fix issue where `rich` eats the cursor if it exits by interrupt.

# 2.0.0dev14

* Multiple logging levels specified via CLI. Can also be set via `set_log_level`
  in the API.
* Updated all `run_subprocess` invocations to create a log, named after the
  `Step`'s `id` by default.
* Fixed issue with `ROUTING_CORES` not using the computer's total core count by
  default.
* Fixed an issue with Tcl config files where `DESIGN_DIR` was resolved
  relatively, which greatly confused KLayout.

# 2.0.0dev13

* Add ApplyDEFTemplate step.
* Update most `odbpy` CLIs to accept multiple LEF files.

# 2.0.0dev12

* Cleaned up build system.
* Add support for OpenROAD with `or-tools` on macOS.

# 2.0.0dev11

* Added `QUIT_ON_SYNTH_CHECKS`
* Added `QUIT_ON_UNMAPPED_CELLS`
* Added metric `design__instance_unmapped__count`
* Allowed `MetricChecker` to raise `StepError`

# 2.0.0dev10

* Updated OpenROAD to `6de104d` and KLayout to `0.28.5`.
* OpenROAD builds now use system boost to cut on build times.
* Added new dedicated interactive mode to replace "Step-by-step" API: activated
  by calling `ConfigBuilder.interactive`, which replaced `per_step`.
  * State, Config and Toolbox for `Step`s all become implicit and rely on global
    variables.
  * On the other hand, `config=` must now be passed explicitly to
    non-interactive flows.
* Added Markdown-based IPython previews for `Step` and `Config` objects.
  * Added an API to render `DEF` or `GDS` files to PNG files to help with that.
* Changed API for KLayout Python scripts to be a bit more consistent.
* Renamed a number of variables for consistency.
* Tweaked documentation slightly for consistency.

# 2.0.0dev9

* Moved `State` to its own submodule.
* Fixed bug with loading default SCL.

# 2.0.0dev8

* Added a step-by-step API for OpenLane.
  * Involves new `ConfigBuilder` method, `per_step`, which creates configuration
    files that can be incremented per-step.
  * This mode is far more imperative and calls may have side effects.
* Added an example IPython notebook to use the aforementioned API.
  * Add a number of APIs to display `State` as a part of a notebook.
* Added various default values for `Step` so it can be used without too many
  parameters. (`config` is still required, but `state_in` will become an empty
  state if not provided.)
* Moved various documentation functions to the `Variable` object so they can
  also be used by IPython.
* Updated documentation for `Variable` object.
* Various documentation updates and fixes.

# 2.0.0dev7

* More build fixes.

# 2.0.0dev6

* Added magic builds to macOS
* Fixed KLayout builds on macOS
* Tweaks to Nix build scripts
* Removed hack to make KLayout work on macOS
* Removed NoMagic flow

# 2.0.0dev5

* Fixed commandline `--flow` override.
* Removed call-stack based inference of `state_in` argument for steps: a step
  initialized without a `state_in` will have an empty in-state.
* Changed signature of `Flow.run`, `Flow.start` to return `(State, List[Step])`,
  returning only the last state as the per-step states can be accessed via
  `step[i].state_out`.
* Removed distinction between the `Step.id` and it factory-registered string:
  the ID is now used for the factory, in the format `Category.Step` for the
  built-in steps.
* Fixed `--from` and `--to`, also add validation and case-insensitivity.
* Various bugfixes to Tcl script packager.

# 2.0.0dev4

* Fix `Optimizing` flow.

# 2.0.0dev3

* Remove Mako as requirement, migrate relevant code.

# 2.0.0dev2

* Updated installation instructions.
* Separated variables step-by-step.
* Various fixes to environment variables, especially when using OpenROAD Odb
  Python scripts.
* Add specialized steps to check and/or quit on specific metrics and/or
  variables.

# 2.0.0dev1

* Rewrite OpenLane in Python using a new, Flow-based architecture.
* Add packaging using the Nix Package Manager to replace the Docker
  architecture.
* Added transparent Dockerization using `--dockerized` commandline argument,
  with images also built using Nix.
