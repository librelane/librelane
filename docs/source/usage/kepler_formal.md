# Sequential Equivalence Checking with Kepler Formal

`KeplerFormal.SEC` checks that a gate-level netlist produced by the flow is
sequentially equivalent to the design's RTL, using
[Kepler Formal](https://github.com/keplertech/kepler-formal). Kepler Formal is
part of the LibreLane Nix environment, so no further installation is needed.

## Enabling the Step

The step is not part of the Classic flow. Insert it after any step that
produces a netlist, for example right after fill insertion so that the final
netlist is checked:

```yaml
meta:
  version: 2
  flow: Classic
  substituting_steps:
    "+OpenROAD.FillInsertion": KeplerFormal.SEC
```

Three variables control the proof:

| Variable | Default | Meaning |
| --- | --- | --- |
| `KEPLER_FORMAL_ENGINE` | `pdr` | Proof engine: `pdr`, `k_induction` or `imc`. |
| `KEPLER_FORMAL_ENCODING` | `dual_rail_steady` | How unknown state is modelled, see below. |
| `KEPLER_FORMAL_MAX_K` | `32` | Bound for the proof or counterexample search. |

## What Is Compared

The RTL in `VERILOG_FILES` is read by Kepler Formal's own SystemVerilog
frontend with the view synthesis had of it: the `PDK_*`, `SCL_*`, `PAD_*`,
`__librelane__`, `__pnr__` and `SYNTHESIS` defines, `VERILOG_DEFINES`,
`VERILOG_INCLUDE_DIRS`, `SYNTH_PARAMETERS` and `SLANG_ARGUMENTS`. The gate
side is the current `NETLIST`, with cells taken from the `CELL_LIBS` and
`PAD_LIBS` Liberty files of `DEFAULT_CORNER` and from `EXTRA_LIBS`. Macros
contribute their netlist when they have one and their Liberty file otherwise;
a macro with neither cannot be part of the proof and stops the step.
`EXTRA_VERILOG_MODELS` are read on both sides. No input is rewritten.

Fill, decap, tap and endcap cells (`FILL_CELLS`, `DECAP_CELLS`,
`WELLTAP_CELL`, `ENDCAP_CELL`) carry no logic, and some PDKs ship them as LEF
only. When the netlist instantiates such a cell that none of the Liberty files
defines, the step writes an empty Verilog module for it to
`physical_cells.v` and reads that file with the netlist.

## Results

The flow stops in two cases: Kepler Formal finds a counterexample, i.e. an
input sequence on which the two designs produce different outputs, or Kepler
Formal cannot run on the design, for example because the netlist uses a cell
that none of the Liberty files define or the RTL uses an unsupported
construct. The error names the cause; the step's log has the details.

Everything short of a complete proof lets the flow continue with a warning:
outputs the tool could not check, a proof that ran out of bound on some
outputs, an inconclusive result, and proofs that treat internal terms as
boundaries instead of checking through them. The reasons are in the step
directory: `kepler_formal.log` is the tool's log, `boundary_terms.txt` lists
the boundary terms and `skipped_*_pos.txt` the outputs that were skipped and
why. `rtl.f` and `kepler_formal.yml` are the inputs the step generated for the
tool and can be used to rerun it by hand.

The step adds these metrics:

| Metric | Meaning |
| --- | --- |
| `design__equivalence__proven` | `1` when every output was proven equivalent, `0` otherwise. |
| `design__equivalence__checked_outputs` | Outputs proven equivalent. |
| `design__equivalence__unchecked_outputs` | Outputs skipped or left inconclusive. |
| `design__equivalence__proof_bound` | The bound at which the proof (or partial proof) completed. |

## Encodings

Kepler Formal does not assume that registers in the RTL and in the netlist
correspond by name, so an output whose value depends on a register that no
reset ever defines cannot be compared bit for bit.

In the default `dual_rail_steady` encoding such outputs stay in the proof: the
tool tracks whether each value is known and proves that the two designs never
produce opposite *defined* values. It does not prove that an output ever
becomes defined.

The `binary` encoding is an exact 0/1 comparison. It gives a stronger result
for the outputs it checks, but skips outputs that depend on reset-unanchored
state, which then shows up as unchecked outputs. Kepler Formal can keep those
outputs in a binary proof when told which ports reset the design; the step
does not expose this yet.
