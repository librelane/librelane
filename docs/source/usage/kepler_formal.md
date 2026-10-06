# Sequential Equivalence with Kepler Formal

`KeplerFormal.SEC` compares the original Verilog/SystemVerilog RTL with the
current gate-level netlist. It passes both inputs directly to Kepler Formal
without rewriting them. It can run after filler insertion in the Classic flow.
A complete equivalence proof lets the flow continue; a counterexample,
inconclusive result, frontend failure, unsupported model, or incomplete output
coverage stops it.

## Run the `spm` Example

After [setting up Nix](../installation/index.md), clone this fork and enter its
tool environment:

```bash
git clone --branch main --recurse-submodules https://github.com/nanocoh/librelane.git
cd librelane
nix-shell
```

Add the following top-level entries to `librelane/examples/spm/config.yaml`,
keeping its existing design settings:

```yaml
meta:
  version: 2
  flow: Classic
  substituting_steps:
    "+OpenROAD.FillInsertion": KeplerFormal.SEC

KEPLER_FORMAL_ENGINE: pdr
KEPLER_FORMAL_ENCODING: dual_rail_steady
KEPLER_FORMAL_MAX_K: 32
```

The `+` inserts the check immediately after `OpenROAD.FillInsertion`. It keeps
filler insertion and the remaining Classic steps in place. Run the configuration
from the repository root:

```bash
python3 -m librelane librelane/examples/spm/config.yaml
```

The pinned Kepler frontend currently rejects the unmodified `spm` RTL with an
unsupported `InstanceArray` error. This stops the run at `KeplerFormal.SEC`;
the step does not transform the RTL to bypass the frontend limitation.

`KEPLER_FORMAL_ENGINE` defaults to `pdr`; `k_induction` and `imc` are also
available. `KEPLER_FORMAL_ENCODING` defaults to `dual_rail_steady`; `binary`
is also available. `KEPLER_FORMAL_MAX_K` defaults to `32` and must be non-negative.
Reaching this bound without a proof stops the flow. After updating the checkout
or its Nix dependencies, exit and re-enter `nix-shell` to refresh the environment.

## Inputs and Results

The RTL frontend uses `DESIGN_NAME`, `VERILOG_FILES`, `VERILOG_INCLUDE_DIRS`,
`VERILOG_DEFINES`, `SYNTH_PARAMETERS`, and `SLANG_ARGUMENTS`. It includes the
standard synthesis defines used by LibreLane. These options are passed to
Kepler's native frontend alongside the original RTL files. The gate input is
the unchanged current `NETLIST` state. The step does not generate an elaborated
RTL netlist or strip cells from the gate netlist.
Its tool configuration selects `format: sv2v`, with RTL as design 1 and the
gate-level netlist as design 2.

Cell and optional pad Liberty files are selected for `DEFAULT_CORNER` from
`LIB` and `PAD_LIBS`. `EXTRA_LIBS`, functional macro netlists or Liberty models,
and `EXTRA_VERILOG_MODELS` supply additional models. Every instantiated cell
needs a suitable definition, including physical cells retained in the netlist.
Black-box headers do not establish equivalence.

The `KeplerFormal.SEC` step directory contains the generated `rtl.f` frontend
options, `kepler_formal.yml` tool configuration, captured
`keplerformal-sec.log`, and `boundary_terms.txt`. Kepler may also write
`skipped_*_pos.txt` reports. Use the captured `keplerformal-sec.log` to inspect
the verdict or counterexample; the tool's separate `kepler_formal.proof.log`
may omit the final verdict.

Successful checks add these metrics to `state_out.json`:

| Metric | Meaning |
| --- | --- |
| `design__equivalence__proven` | `1` when a complete proof was accepted. |
| `design__equivalence__checked_outputs` | Number of checked output bits. |
| `design__equivalence__proof_bound` | Bound reported by the successful proof. |

The step checks the reported verdict, output coverage, and boundary reports.
The pinned Kepler version returns exit status zero for both a proof and a
counterexample, so exit status alone does not indicate equivalence.
