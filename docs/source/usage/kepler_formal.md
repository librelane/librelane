# Sequential Equivalence Checking with Kepler Formal

`KeplerFormal.SEC` checks that a gate-level netlist produced by the flow is
sequentially equivalent to the design's RTL, using
[Kepler Formal](https://github.com/keplertech/kepler-formal). Kepler Formal is
shipped with LibreLane, so no further installation is needed.

## Enabling the Step

The step is not part of the Classic flow. Insert it after any step that
produces a netlist, for example right after fill insertion so that the final
netlist is checked, and follow it with `Checker.KeplerFormalSEC` to fail the
flow when the proof is not complete:

```yaml
meta:
  version: 2
  flow: Classic
  substituting_steps:
    "+OpenROAD.FillInsertion": KeplerFormal.SEC
    "+KeplerFormal.SEC": Checker.KeplerFormalSEC
```

The checker raises a deferred error, like the other signoff checkers, so the
flow finishes before it fails. Set `ERROR_ON_UNPROVEN_EQUIVALENCE` to `false`
to keep the warning only.

Three variables control the proof:

| Variable | Default | Meaning |
| --- | --- | --- |
| `KEPLER_FORMAL_ENGINE` | `pdr` | Proof engine: `pdr`, `k_induction` or `imc`, see below. |
| `KEPLER_FORMAL_ENCODING` | `dual_rail_steady` | How unknown state is modelled, see below. |
| `KEPLER_FORMAL_MAX_K` | `32` | Bound for the proof or counterexample search. |

Every other Kepler Formal setting is available as an optional variable. An
unset variable is not written to the tool's configuration, so Kepler Formal's
own default applies; the default run uses none of them.

| Variable | Kepler Formal setting |
| --- | --- |
| `KEPLER_FORMAL_SOLVER` | `solver`: `kissat` (default), `glucose` or `cadical`. |
| `KEPLER_FORMAL_LEARN_INTERNAL_RELATIONS` | `learn_internal_relations` |
| `KEPLER_FORMAL_ALLOW_X_EQUALITY_IN_INTERNAL_RELATIONS` | `allow_x_equality_in_internal_relations` |
| `KEPLER_FORMAL_BINARY_RELATION_ROUND` | `binary_relation_round` |
| `KEPLER_FORMAL_LATCH_ABSTRACTION` | `latch_abstraction` |
| `KEPLER_FORMAL_DATA_LATCH_MODEL` | `data_latch_model` |
| `KEPLER_FORMAL_RESET_CYCLES`, `KEPLER_FORMAL_RESET_PORTS` | `sec_reset`: hold the listed ports, e.g. `{"rst_n": false}`, at their active value for the first cycles; see [Encodings](#encodings). |
| `KEPLER_FORMAL_SET_AS_BOUNDARY` | `set_as_boundary`: pairs of RTL and netlist instance paths treated as proof boundaries. |
| `KEPLER_FORMAL_PY_TECH_FILES` | `py_tech_files` |
| `KEPLER_FORMAL_SV_SINGLE_UNIT` | `sv_single_unit` |
| `KEPLER_FORMAL_VERILOG_PREPROCESSING` | `verilog_preprocessing` |
| `KEPLER_FORMAL_NETLIST_TOP` | `verilog_design2_top` |
| `KEPLER_FORMAL_COMPACT_MODE` | `compact_mode` |
| `KEPLER_FORMAL_LOG_LEVEL` | `log_level`: `info` (default) or `debug`. |
| `KEPLER_FORMAL_EXPORT_BTOR2`, `KEPLER_FORMAL_EXPORT_CNF`, `KEPLER_FORMAL_EXPORT_PO_CNF` | `btor2_export`, `cnf_export`, `po_cnf_export`; the files land in the step directory. |

The meaning of each setting is documented in Kepler Formal's
[flag reference](https://github.com/keplertech/kepler-formal/blob/main/docs/sec-flags-spec.md).

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

Everything short of a complete proof lets the flow continue with a warning
(or with a deferred error when `Checker.KeplerFormalSEC` follows the step):
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

## Engines

The three engines prove the same property on the same model and differ in how
they look for the proof, which decides whether one is found within
`KEPLER_FORMAL_MAX_K`.

`pdr` (Property Directed Reachability, the default) builds the invariant it
needs on its own. It is the engine for comparing a netlist with RTL, where
synthesis has re-encoded the registers: on the `gcd` CI design it proves all
18 outputs at k = 12 in a few minutes with the default settings, while
`k_induction` runs out of bound with 1 of 18 outputs proved and `imc` stays
inconclusive. With the defaults, `pdr` reaches a complete proof on the
`sky130A/sky130_fd_sc_hd` CI designs `BM64`, `EF_GPIO`, `EF_TCC32`, `gcd`,
`hold_violations_1`, `hold_violations_2`, `inverter`, `partial_hierarchy`,
`s44` and `user_proj_timer`.

`k_induction` is the classic bounded check: it proves an output by plain
induction when the registers in its cone correspond one to one between the RTL
and the netlist, and reports the other outputs as inconclusive once
`KEPLER_FORMAL_MAX_K` is reached. Raising the bound rarely turns its partial
proof into a complete one, because what is missing is an invariant, not depth.

`imc` (Interpolation-Based Model Checking) is a second unbounded engine to try
when `pdr` does not finish in the time you can give it. In Kepler Formal's own
regressions it has not reached a proof on a design where `pdr` did not.

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
state, which then shows up as unchecked outputs. Kepler Formal keeps those
outputs in a binary proof when told which ports reset the design and for how
long: set `KEPLER_FORMAL_RESET_PORTS` and `KEPLER_FORMAL_RESET_CYCLES`.
