# Power Distribution Networks

A Power Distribution Network (PDN) is a series of connection throughout the chip
that aim to ensure all the cells receive power at a relatively consistent
voltage, i.e. without power drops.

A power distribution network is composed of a combination of **straps** and
**rings**.

```{tip}
This guide assumes you're using the default flow or the included PDN step,
**`OpenROAD.GeneratePDN`**.

You can find a full list of power distribution network configuration variables
in the {step}`PDN step documentation <OpenROAD.GeneratePDN>`.
```

## Straps

Straps are polygons on upper metal layers that are connected to top-level pins
on the design.

In a typical power distribution networks, straps are laid out into a group of
straps. The groups of straps are **offset** from the core boundary by an initial
distance, repeat according to a certain **pitch** distance, and the straps
within them have a fixed **spacing**.

The count of straps in each group corresponds to the unique power/ground pins in
the design. For example, in [Caravel](https://caravel-harness.readthedocs.io/),
there are two sets of power pins at the top level:

* `vccd1` (Digital Power)
* `vssd1` (Digital Ground)
* `vdda1` (Analog Power)
* `vssa1` (Analog Ground)

…and thus, Caravel has **four** straps in each group, one for each pin.

A visualization of straps for a hypothetical design with two top-level power
pins and one ground pin could be found below:

```{include} ./pdn.svg
:start-line: 2
```

There are two layers of straps, laid out in a plaid pattern, where one has
**vertical** straps and the other has **horizontal** straps. The straps are
connected with vias at the intersections between groups of straps. Which layer
is the higher or lower layer is PDK-dependent, however, the two layers must be
consecutive and must have straps in opposite directions.

## Rings

Rings are four steps of straps across two layers surrounding a macro, used for
one specific method of power integration which will be detailed in a later
section.

## Macro Integration

Any macros instantiated within a design need to be connected to the top-level
power distribution network. There are, in essence, two methods to accomplish
this:

* Hierarchical method: Saves space, but less routing layers are available for
  the macros (i.e. for a Macro nested *i*-deep, *N - i* metal layers are
  available for routing.) This is the default behavior and should be used in
  most cases.

* Ring method: Uses more space, allows any arbitrarily-nested macro to use the
  full routing layer stack. Useful if routing very complex macros.

Regardless of the power routing method being used, you need to ensure that your
design is configured as follows:

```{tip}
This section assumes you're integrating for Caravel and using the default
Flow. Power pin names may vary.
```

* The Verilog headers for the sub-macros have the power with a preprocessor
  guard. For example:

  ```verilog
    `ifdef USE_POWER_PINS
    inout vccd1,
    inout vssd1,
    `endif
  ```

* The configuration includes hooks to show LibreLane how to connect the signals,
  as well as the name of the preprocessor guard for the power pins.
  Additionally, we ignore OpenROAD's PSM network checker as it lacks the ability
  to check hierarchical designs correctly.

  ```json
  "FP_PDN_MACRO_HOOKS": "mprj vccd1 vssd1 vccd1 vssd1",
  "SYNTH_POWER_DEFINE": "USE_POWER_PINS",
  "FP_PDN_CHECK_NODES": false
  ```

The hierarchical method works as follows: the top level integration has access
to all metal layers; and the deeper you go in the macro hierarchy, you lose the
top-most metal layer as being available for routing.

So for example, a macro routed for top-level integration must not have any
signals or power routed on met5. A macro routed *within* that must not have any
signals or power routed on met4. And so on.

The power straps on the top-most metal layer of a sub-macro are then connected to
the layer above using vias. (There is no continuity between power straps within
each metal layer across the macro boundary.)

```{figure} pdn_hierarchical.webp

A top view of an example PDN, showing the power rails. Note
how within each macro, straps may have different properties such as
width, pitch or spacing.

The topmost metal layer, met5, is the lightest gray, while met4 and
met3 are darker. Vias between metal layers are represented in green.
```

As you may be able to tell from the previous figure; sub-macros must be large
enough for the straps in the layer above them to intersect with the straps in
its topmost layer, otherwise the macro would not be connected to power.

Additionally, particularly in option 1, there are metal "stubs" generated as
part of the power distribution network, which aren't connected to any macros.
These are generally harmless but do cause higher routing congestion at the top
level. If the configuration variable `FP_PDN_SKIPTRIM` is set to `false`, the
PDN will attempt to remove those stubs.

The hierarchical mode is the default used by LibreLane and no configuration other
than that which was shown above is required.

## Ring Method

The ring method works as follows: each macro is hardened with a "power ring"
around the **core area** of the macro, which unlike the hierarchical method,
does interrupt the straps on the top level.

This allows the use of the full layers stack for routing, however, it takes more
area, making it less space-efficient.

```{figure} pdn_ring.webp
A top view showing the integration of a macro that uses
power rings.
```

Akin to the hierarchical method; sub-macros must be large enough for the straps
in the layer above them to connect to the rings, otherwise the macro would not
be connected to power.

The core ring method does not actually require any special configuration for the
top-level integration, but all macros need to be hardened with the following
options:

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING` Must be set to true

* {var}`OpenROAD.GeneratePDN::FP_PDN_HORIZONTAL_LAYER` While the vertical layer may remain unchanged, the
  horizontal layer should be different from the integrator (i.e.) met5.

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING_HWIDTH` The width of the horizontal straps forming the core ring.

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING_VWIDTH` The width of the vertical straps forming the core ring.

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING_HOFFSET` The distance between the horizontal boundaries of the die
  area and the beginning of the horizontal core ring straps.

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING_VWIDTH` The distance between the vertical boundaries of the die
  area and the beginning of the vertical core ring straps.

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING_HSPACING` The intra-strap distance within the two sets of
  horizontal straps forming the core ring.

* {var}`OpenROAD.GeneratePDN::FP_PDN_CORE_RING_VSPACING` The intra-strap distance within the two sets of vertical
  straps forming the core ring.
