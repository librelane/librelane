# Resolving LVS Mismatches in LibreLane

This guide aims to document a number of common {term}`LVS` mismatches, their
possible causes, and how to resolve them.

This is a living document. We'll add more sections as we encounter more LVS

## About LVS Mismatches

LVS mismatches (alternately referred to simply as LVS errors) constitute a
situation where the physical **layout** of the chip does not match the declared
**schematic** thereof. Here is a non-exhaustive list of some common issues that
are captured by LVS:

1. An open circuit exists in the layout where it should be connected in the
   schematic, i.e., a connection was not properly made.
1. A bridge exists between two wires in the layout that are not connected in
   the schematic, creating a short-circuit.
1. A component (standard cell or macro) declared in the schematic is missing
   or different in the layout.

The first two are the most common class of LVS error. In LibreLane, the affected
nets are more often than not power nets.

These mismatches can occur either by user misconfiguration 

## Identifying LVS mismatches

When running the {flow}`Classic` flow, you may see this message at the end of
the flow:

```log
ERROR   The following error was encountered while running the flow:
        One or more deferred errors were encountered:
        1 LVS errors found.
```

This indicates that both:
* The {step}`Netgen.LVS` was run, comparing the final Verilog netlist with the
  final {term}`SPICE` netlist, found one mismatch.
* Another step, {step}`Checker.LVS`, reported it to the flow as an Error.

We can find the specific LVS mismatches in the reports directory of
{step}`Netgen.LVS`, which would be named something along the lines
`runs/<run_tag>/<step number>-netgen-lvs/reports`. Inside, there is a report
named `lvs.netgen.rpt`.

You can find specific mismatches by searching `MISMATCH` in the report.

## Pin postfixed with `_uqX`

In some instance, the layout may contain a pin postfixed with `_uq` and then
an integer.

This typically indicates that there's a break in the net. During SPICE netlist
extraction with Magic, Magic ensures every net has a unique name, meaning that
if two nets exist with the same name (i.e. the same net has a break in it,)
one will be renamed to `_uq`. This may be any number of things, including:



 
