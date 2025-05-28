# Glossary

```{glossary}
:sorted:

IPVT

    Short for Interconnect, Process, Voltage, and Temperature, the four
    components of a {term}`timing corner` in LibreLane.

timing corner

    A set of simulated physical conditions under which timing analysis is
    performed.

[Nix](https://nixos.org)

    A declarative build utility that can be used to create development
    environments in a pure and reproducible manner for both Linux and macOS.

    LibreLane environments including tools are built with Nix.

[Cachix](https://docs.cachix.org/)

    Cachix is a service that caches {term}`Nix` build results from the LibreLane
    CI and allows users to download those results instead of building LibreLane
    and all included utilities themselves.


[sky130](https://github.com/google/skywater-pdk)

    The SkyWater Open Source {term}`PDK` is a collaboration between Google, Efabless and
    SkyWater Technology Foundry to provide a fully {term}`open-source` PDK and
    related resources, which can be used to create manufacturable designs at
    SkyWater’s facilities. sky130 is a mature 180nm-130nm hybrid technology
    originally developed internally by Cypress Semiconductor before being spun
    out into SkyWater Technology and made accessible to general industry.

    sky130 is the default PDK for use with LibreLane as it was the first entirely
    open-source PDK.

PDK

    Short for Process Design Kit.

    A set of files used within the
    semiconductor industry to model a fabrication process for the design
    tools used to design an integrated circuit.

RTL

    Short for Register-Transfer Level.

    An abstraction used in hardware description languages
    (HDLs) like Verilog and VHDL to create high-level representations of a
    circuit, from which lower-level representations and ultimately actual wiring
    can be derived. Design at the RTL level is typical practice in modern digital
    design.

Netlist

    A representation of the circuit modeling pre-hardened elements (standard
    cells and macros) and the connections between them.

    In LibreLane, Netlists can be in Verilog, where they model cells in ideal conditions
    and are only interested in verifying the logical correctness of the circuit,
    or they can be {term}`SPICE netlist`(s), which model more physical conditions.

GDSII

    Short for Graphic Design System II.

    A binary stream format which is the *de facto* industry standard for data
    exchange of integrated circuit or IC layout artwork. It was developed by
    Calma Company in 1978. A GDSII file contains planar
    geometric shapes, text labels, and other information about the layout in
    hierarchical form. The data can be used to reconstruct all or part of the
    artwork to be used in sharing layouts, transferring artwork between different
    tools, or creating photomasks. It captures all the layout details needed by
    the manufacturer.

[KLayout](https://www.klayout.de/)

    A free and {term}`open-source` layout ({term}`DEF`/{term}`GDSII`) viewer and
    editor.

PnR

    Short for placement and routing.

    A phase of digital circuit implementation where:

    1. the positions of standard cells and macros within a layout are
        determined and checked for legality (placement)
    2. the shapes of the physical connections between those cells are determined
        and also checked for legality (routing)

[OpenROAD](https://openroad.readthedocs.io/en/latest/)

    An {term}`open-source` tool chain for digital SoC layout generation,
    focusing on the RTL-to-GDSII phase of system-on-chip design. It is used for
    floorplanning, {term}`PnR` and design optimizations inside LibreLane.

[OpenLane](https://github.com/The-OpenROAD-Project/OpenLane)

    The progenitor of LibreLane, OpenLane is an ASIC flow developed by Efabless
    Corporation in 2020 for use with the Google {term}`OpenMPW` project.

[Magic](http://opencircuitdesign.com/netgen)

    A free software layout ({term}`DEF`/{term}`GDSII`) viewer and editor.

[Yosys](https://github.com/YosysHQ/yosys)

    A framework for RTL synthesis tools with extensive Verilog-2005 support.

SDC

    Stands for Synopsys® Design Constraints.

    A Tcl-based format used to describe design requirements including timing,
    power, and area to EDA tools. Supports of a subset of the Tcl commands
    provided by timing tools.

Tcl

    A shell language popular for embedded interpreter inside {term}`EDA`
    tools, initially designed by John Osterhout for use with the {term}`Magic`
    VLSI tool.

    {term}`Yosys`, {term}`OpenROAD` and {term}`Magic` are all Tcl-programmable,
    in addition to most proprietary electronic design automation tool. LibreLane
    accepts design configuration files in the Tcl format as previous versions of
    LibreLane were written in Tcl.

metrics

    Quantitative measures representing physical characteristics of a design.

    Typically, these include values like the area of the design, worst clock
    slack, average voltage drop, et cetera, but in LibreLane the conventional definition
    is expanded to include any and all information about the circuit generated
    during runtime, encompassing things such as lint violations in the
    {term}`RTL` description of the circuit, the number of pins, et cetera.

[METRICS2.1](https://github.com/ieee-ceda-datc/datc-rdf-Metrics4ML#metrics21-naming-convention)

    A naming convention for {term}`metrics` of a design used by {term}`OpenROAD`
    and LibreLane 2+. LibreLane is responsible for extracting and naming metrics
    in a 2.1-compliant format from tools other than OpenROAD.

LEF

    Short for "Layout Exchange Format".

    An abstract view of pre-hardened macros and standard cells, containing
    information about the cell's dimensions, pin positions and elements on
    metal layers.

    The LEF language is defined in the {term}`LEFDEFREF`.

DEF

    Short for "Design Exchange Format".

    An abstract view of the current working design, listing instantiated cells
    and macros as well as any elements on metal layers, including pins.

    When a design is hardened, {term}`LEF` and {term}`GDSII` views are
    generated from the DEF view.

    The DEF language is defined in the {term}`LEFDEFREF`.

LEFDEFREF

    Refers to the LEF/DEF Language Reference by Cadence
    Inc.

    The LEFDEFREF is obtainable for free from Silicon Integration Initiative,
    Inc.'s
    [Complimentary OpenAccess Tools, Libraries, and Utilities](https://si2.org/oa-tools-utils-libs/).

    As of the time of writing, a slightly out of date but still valid version is
    also available from the
    [ISPD's 2018 detailed routing contest downloads](https://www.ispd.cc/contests/18/lefdefref.pdf).

CSV

    Short for "Comma-separated Values".

    A text file that represents tabular data.

JSON

    Short for JavaScript Object Notation.

    A data interchange format derived from JavaScript supporting numeric, Boolean
    and string values as well as lists and hashmaps composed of the above.

    LibreLane uses JSON as the primary form for loading and storing configuration
    data.

Verilog

    A hardware description language (HDL) used to model electronic
    systems. It is most commonly used in the design and verification of digital
    circuits at the register-transfer level (RTL) of abstraction.

[Netgen](http://opencircuitdesign.com/netgen)

    A {term}`open-source` tool for running {term}`LVS`.

SPICE

    Short for Simulation Program with Integrated Circuit Emphasis.

    A public-domain utility for simulating analog circuits. Unlike (most)
    Verilog simulators, SPICE enables the simulation of a variety of physical
    conditions of a circuit, including but not limited to, temperature,
    extracted parasitic resistances and capacitances, transistor switching
    speed, and so on.

    SPICE itself is not part of any included LibreLane flows, but
    {term}`SPICE netlist`s are.


SPICE netlist

    A netlist readable by {term}`SPICE` and compatible utilities. Unlike Verilog
    netlists, SPICE netlists are capable of capturing an analog view of the
    circuit.

    By comparing the digital Verilog netlist and analog SPICE netlist, LibreLane
    performs {term}`LVS`.

ASIC

    Short for Application-Specific Integrated Circuit.

    As the name implies, it is silicon that is manufactured to execute a specific
    function (even though these functions may be themselves generic, i.e., a
    CPU is an ASIC that performs general-purpose computing).

    Broadly, digital design targets one of two technologies: ASIC manufacturing
    (higher upfront cost but lower-cost scaling) or {term}`FPGA` (lower-cost
    upfront cost but *very* costly scaling.)

    LibreLane flows primarily target ASIC technologies for manufacturing.

FPGA

    Short for Field-Programmable Gate Array.

    An integrated circuit that can be reprogrammed to perform various digital
    functions much, much faster than a general-purpose computer, but at a
    recurring cost, area and performance penalty compared to a dedicated ASIC.

    Popular for prototyping ASICs or for niche applications where the upfront
    cost of an ASIC is not financially justifiable.

EDA

    Short for Electronic Design Automation.

    A field concerned with the development software, hardware, and services to
    enable the automation of chip design tasks. LibreLane and all of its
    constituent utilities could be considered EDA tools.

foundry

    A semiconductor manufacturer, such as GlobalFoundries, SkyWater Technologies,
    or TSMC.

process node

    A semiconductor manufacturing process executed by a certain chip foundry,
    typically identified by the foundry name and a number, i.e., the Skywater
    130 nm process ({term}`sky130`).

    Historically, the process node number used to refer to a physical characteristic
    of the circuit such as the minimum feature length, but since the mid-1990s,
    the number has become more or less arbitrary.

    To create a design to be manufactured on a particular process node, a
    {term}`process design kit <PDK>` for that node is required.

DRC

    Short for Design Rule Checks.

    Rules set by a chip foundry for a certain chip manufacturing process that
    broadly have to be satisfied by a design for a design to be actually
    manufacturable.

    A design that does not have any DRC violations is referred to as DRC-clean.

LVS

    Short for Layout vs. Schematic.

    A comparison between the engineering schematic for a certain design (abstract)
    and its (concrete) physical layout. This catches misconfigured power connections
    or bugs with {term}`PnR` tools.

    A design that does not have any LVS errors is referred to as LVS-clean.

DRC deck

    An implementation of a set of {term}`DRC`s for a certain utility.

On-chip variation

    Variations in physical and electrical characteristics of chips. They can
    occur due to factors such as manufacturing processes, material properties,
    or environmental conditions.

    Sometimes abbreviated as OCV.

STA

    Short for Static Timing Analysis.

    A method for determining the validity of a chip's timing parameters without
    performing a full functional simulation thereof.

    A chip for which STA reveals no timing constraint violations is said to
    have achieved {term}`timing closure`.

timing closure

    A term given for designs for which STA has revealed that there exist no
    violations of timing constraints at a certain clock period and at all
    {term}`timing corners <timing corner>`.

    Designs that have not achieved timing closure are usually not suitable
    for tape-out.

IEEE

    Short for the Institute of Electrical and Electronics Engineers.

    A professional association for electronics and electrical engineers. IEEE
    sets the standard for a number of formats in the EDA space, including 
    the Verilog Hardware Description Language.

SPEF

    Short for Standard Parasitic Exchange Format.

    An {term}`IEEE` standard for representing parasitic resistances and
    capacitances of wires in a circuit.

SDF

    Short for Standard Delay Format.

    An {term}`IEEE` standard for representing and interpreting timing data for
    use at any stage of an electronic design process.

open-source

    A model for releasing products where upon the source files are also made
    available for free (as in free spreech, not necessarily but usually
    also free of cost) modification and redistribution.
    
    The term is more accurately defined by the Open Source Initiative (OSI) at
    this link: https://opensource.org/osd
    
Caravel

    A test harness by Efabless Corporation for use with the {term}`OpenMPW`
    and {term}`chipIgnite` programs, that enforces a common pinout for all
    user projects as well as providing a number of base functions, including
    a management SoC, I/O configuration, power, clocking, and more.
    
    See https://caravel-harness.readthedocs.io/en/latest/ for more info.

OpenMPW

    A program by Google sponsoring a free Multi-Project Wafer for
    {term}`open-source` hardware projects. LibreLane's progenitor,
    {term}`OpenLane`, was initially developed for use with the OpenMPW project.
    
    See https://developers.google.com/silicon for more info.
    
chipIgnite

    A program by Efabless Corporation for manufacturing chips based on the
    {term}`sky130` PDK; using the same harness and tools as the {term}`OpenMPW`
    program but allowing for (optional) proprietary designs.
    
    See https://efabless.com/chipignite for more info.

MPW
    
    Short for Multi-Project Wafer.
    
    A wafer produced aggregating a number of different chips, allowing the cost
    of a wafer to be spread across multiple projects.
    
    {term}`OpenMPW` and {term}`chipIgnite` are examples of MPW projects.
    
dotlib

    Also `.lib`.

    A library format for macros including standard cells, modeling at an
    abstract level the interface to and timing properties of a cell.
    
    Typically used for Synthesis and {term}`STA`.
    
Gzip

    A free and open-source compression format. A great many number of tools
    support Gzipped inputs transparently, i.e., any file beginning with the
    bytes `1f 8b` is automatically decompressed without any special input
    from the user.
    
    Gzipping is popular for text-heavy formats such as {term}`dotlib` or
    {term}`SPEF` formats.
```
