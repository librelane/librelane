# Option 2 — Full-Wrapper Flattening strategy

In this strategy, we will harden the `user_project_wrapper` with the aes as one
large flattened macro.

## Configuration

Since we will only harden the `user_project_wrapper`. Only the
`librelane/user_project_wrapper/config.json` will be edited. The following edits
are needed for the `user_project_wrapper`

1. Add the AES Verilog files

```json
    "VERILOG_FILES": [
        "dir::../../../secworks_aes/src/rtl/*.v",
        "dir::../../verilog/rtl/aes_wb_wrapper.v",
        "dir::../../verilog/rtl/defines.v",
        "dir::../../verilog/rtl/user_project_wrapper.v"
    ],
```

1. Remove the `Macros configurations` section as there will not be any macros
1. Update the hardening strategy part to the flattened version

```json
    "//": "Hardening strategy variables (this is for 2-Full-Wrapper Flattening). Visit https://docs.google.com/document/d/1pf-wbpgjeNEM-1TcvX2OJTkHjqH_C9p-LURCASS0Zo8 for more info",
    "SYNTH_ELABORATE_ONLY": false,
    "RUN_POST_GPL_DESIGN_REPAIR": true,
    "RUN_POST_CTS_RESIZER_TIMING": true,
    "DESIGN_REPAIR_BUFFER_INPUT_PORTS": true,
    "PDN_ENABLE_RAILS": true,
    "RUN_ANTENNA_REPAIR": true,
    "RUN_FILL_INSERTION": true,
    "RUN_TAP_ENDCAP_INSERTION": true,
    "RUN_CTS": true,
    "RUN_IRDROP_REPORT": true,
    "VSRC_LOC_FILES": {
        "vccd1": "dir::vsrc/upw_vccd1_vsrc.loc",
        "vssd1": "dir::vsrc/upw_vssd1_vsrc.loc"
    },
```

Now the full configuration file will be:

````{dropdown} config.json
```json
{
    "//": "Design files",
    "VERILOG_FILES": [
        "dir::../../../secworks_aes/src/rtl/*.v",
        "dir::../../verilog/rtl/aes_wb_wrapper.v",
        "dir::../../verilog/rtl/defines.v",
        "dir::../../verilog/rtl/user_project_wrapper.v"
    ],
    "PNR_SDC_FILE": "dir::signoff.sdc",
    
    "//": "Hardening strategy variables (this is for 2-Full-Wrapper Flattening). Visit https://docs.google.com/document/d/1pf-wbpgjeNEM-1TcvX2OJTkHjqH_C9p-LURCASS0Zo8 for more info",
    "SYNTH_ELABORATE_ONLY": false,
    "RUN_POST_GPL_DESIGN_REPAIR": true,
    "RUN_POST_CTS_RESIZER_TIMING": true,
    "DESIGN_REPAIR_BUFFER_INPUT_PORTS": true,
    "PDN_ENABLE_RAILS": true,
    "RUN_ANTENNA_REPAIR": true,
    "RUN_FILL_INSERTION": true,
    "RUN_TAP_ENDCAP_INSERTION": true,
    "RUN_CTS": true,
    "RUN_IRDROP_REPORT": true,

    "//": "PDN configurations",
    "PDN_VOFFSET": 5,
    "PDN_HOFFSET": 5,
    "PDN_VWIDTH": 3.1,
    "PDN_HWIDTH": 3.1,
    "PDN_VSPACING": 15.5,
    "PDN_HSPACING": 15.5,
    "PDN_VPITCH": 180,
    "PDN_HPITCH": 180,
    "QUIT_ON_PDN_VIOLATIONS": false,

    "//": "Magic variables",
    "MAGIC_DRC_USE_GDS": true,
    "MAX_TRANSITION_CONSTRAINT": 1.5,

    "//": "Fixed configurations for Caravel. You should NOT edit this section",
    "DESIGN_NAME": "user_project_wrapper",
    "FP_SIZING": "absolute",
    "DIE_AREA": [0, 0, 2920, 3520],
    "FP_DEF_TEMPLATE": "dir::fixed_dont_change/user_project_wrapper.def",
    "VDD_NETS": [
        "vccd1",
        "vccd2",
        "vdda1",
        "vdda2"
    ],
    "GND_NETS": [
        "vssd1",
        "vssd2",
        "vssa1",
        "vssa2"
    ],
    "PDN_CORE_RING": 1,
    "PDN_CORE_RING_VWIDTH": 3.1,
    "PDN_CORE_RING_HWIDTH": 3.1,
    "PDN_CORE_RING_VOFFSET": 12.45,
    "PDN_CORE_RING_HOFFSET": 12.45,
    "PDN_CORE_RING_VSPACING": 1.7,
    "PDN_CORE_RING_HSPACING": 1.7,
    "CLOCK_PORT": "wb_clk_i",
    "SIGNOFF_SDC_FILE": "dir::signoff.sdc",
    "MAGIC_DEF_LABELS": 0,
    "CLOCK_PERIOD": 25,
    "MAGIC_ZEROIZE_ORIGIN": 0
}
```
````

______________________________________________________________________

## Running the flow

To harden macros with LibreLane, we use the default flow, {flow}`Classic`.

```console
[nix-shell:~/librelane]$ librelane ~/caravel_aes_accelerator/openlane/user_project_wrapper/config.json
```

The flow will finish successfully in ~2 hours and we will see:

```console
Flow complete.
```

______________________________________________________________________

## Viewing the layout

To open the final {term}`GDSII` layout run this command:

```console
[nix-shell:~/librelane]$ librelane --last-run --flow openinklayout ~/caravel_aes_accelerator/openlane/user_project_wrapper/config.json
```

Now, we can see that there are STD cells all over the `user_project_wrapper`
without any macros. Also, we can see that the logic is clustered in the bottom
left corner close to the Wishbone bus.

```{figure} ./mprj-flattened-1.webp
:align: center

Final layout of the user_project_wrapper after flattening
```

## Checking the reports

### `OpenROAD.CheckAntennas`

There are around 260 antenna violations with ratios up to 7.

```
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Partial/Required ┃ Required ┃ Partial ┃ Net                                       ┃ Pin          ┃ Layer ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━┩
│ 7.55             │ 400.00   │ 3018.79 │ _14743_                                   │ _28341_/B    │ met3  │
│ 6.82             │ 400.00   │ 2727.89 │ net1493                                   │ _24384_/B    │ met1  │
│ 4.68             │ 400.00   │ 1870.11 │ mprj.aes.core.enc_block.block_w0_reg[18\] │ _20471_/A    │ met1  │
│ 3.86             │ 400.00   │ 1544.22 │ _11561_                                   │ _22409_/A0   │ met1  │
│ 3.80             │ 400.00   │ 1519.33 │ _11868_                                   │ _22752_/A0   │ met1  │
│ 3.71             │ 400.00   │ 1485.23 │ _14658_                                   │ fanout1328/A │ met1  │
│ 3.61             │ 400.00   │ 1443.72 │ net19                                     │ hold86/A     │ met2  │
│ 3.45             │ 400.00   │ 1380.11 │ mprj.aes.core.enc_block.block_w1_reg[6\]  │ _22727_/A1   │ met1  │
⋮
```

In the event they appear, w can fix those the same way we did in the AES
[here](#caravel-openroad-checkantennas-with-fixes).

______________________________________________________________________

### `OpenROAD.STAPostPnR`

Looking at `xx-openroad-stapostpnr/summary.rpt`, there are multiple max Slew/Cap
violations and 1 hold violation which is not Reg to Reg.

```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃              ┃ Hold Worst   ┃ Reg to Reg   ┃          ┃ Hold         ┃ of which Reg ┃ Setup Worst   ┃ Reg to Reg   ┃           ┃ Setup         ┃ of which Reg ┃ Max Cap       ┃ Max Slew     ┃
┃ Corner/Group ┃ Slack        ┃ Paths        ┃ Hold TNS ┃ Violations   ┃ to Reg       ┃ Slack         ┃ Paths        ┃ Setup TNS ┃ Violations    ┃ to Reg       ┃ Violations    ┃ Violations   ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Overall      │ -0.0108      │ 0.1068       │ -0.0108  │ 1            │ 0            │ 5.1907        │ 5.1907       │ 0.0000    │ 0             │ 0            │ 44            │ 275          │
│ nom_tt_025C… │ 0.1236       │ 0.3212       │ 0.0000   │ 0            │ 0            │ 11.2213       │ 15.3832      │ 0.0000    │ 0             │ 0            │ 1             │ 4            │
│ nom_ss_100C… │ 0.4500       │ 0.8885       │ 0.0000   │ 0            │ 0            │ 5.7475        │ 5.7475       │ 0.0000    │ 0             │ 0            │ 38            │ 235          │
│ nom_ff_n40C… │ 0.0365       │ 0.1079       │ 0.0000   │ 0            │ 0            │ 11.1783       │ 18.8282      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ min_tt_025C… │ 0.1726       │ 0.3196       │ 0.0000   │ 0            │ 0            │ 11.2516       │ 15.6835      │ 0.0000    │ 0             │ 0            │ 1             │ 1            │
│ min_ss_100C… │ 0.5527       │ 0.8798       │ 0.0000   │ 0            │ 0            │ 6.2822        │ 6.2822       │ 0.0000    │ 0             │ 0            │ 29            │ 168          │
│ min_ff_n40C… │ 0.0791       │ 0.1068       │ 0.0000   │ 0            │ 0            │ 11.2090       │ 19.0602      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ max_tt_025C… │ 0.0536       │ 0.3234       │ 0.0000   │ 0            │ 0            │ 11.1886       │ 15.0609      │ 0.0000    │ 0             │ 0            │ 5             │ 25           │
│ max_ss_100C… │ 0.3233       │ 0.8972       │ 0.0000   │ 0            │ 0            │ 5.1907        │ 5.1907       │ 0.0000    │ 0             │ 0            │ 44            │ 275          │
│ max_ff_n40C… │ -0.0108      │ 0.1095       │ -0.0108  │ 1            │ 0            │ 11.1440       │ 18.5834      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
└──────────────┴──────────────┴──────────────┴──────────┴──────────────┴──────────────┴───────────────┴──────────────┴───────────┴───────────────┴──────────────┴───────────────┴──────────────┘
```

The max Slew/Cap violations can be fixed the same way as in
[this section](#caravel-openroad-stapostpnr-with-fixes). For the hold violation,
it is in the `max_ff_n40C_1v95` corner. To investigate the timing path, open the
report `xx-openroad-stapostpnr/max_ff_n40C_1v95/min.rpt` and the violation will
be in the first timing path.

```{note}
There might be more hold violations or no violations at all depending on the
version of LibreLane being used as this is a violation with a very small negative
slack and the results can slightly change with LibreLane or OpenROAD updates.
```

To fix hold violations, one or more of the following solutions can be applied:

1. Enable post-global routing timing optimizations using
   {var}`Classic::RUN_POST_GRT_RESIZER_TIMING`:

```json
    "RUN_POST_GRT_RESIZER_TIMING": true,
```

2. Increase the hold repair margins using
   {var}`OpenROAD.ResizerTimingPostCTS::PL_RESIZER_HOLD_SLACK_MARGIN` and
   {var}`OpenROAD.ResizerTimingPostGRT::GRT_RESIZER_HOLD_SLACK_MARGIN`. The
   default values are `0.1ns` and `0.05ns`. We can increase those as follows:

```json
    "PL_RESIZER_HOLD_SLACK_MARGIN": 0.2,
    "GRT_RESIZER_HOLD_SLACK_MARGIN": 0.2,
```

3. Change the default timing corner using {var}`::DEFAULT_CORNER`:

```json
    "DEFAULT_CORNER": "max_tt_025C_1v80",
```

4. Most importantly, it is recommended to use a specific constraint file for
   your design using {var}`OpenROAD.CheckSDCFiles::PNR_SDC_FILE` and
   {var}`OpenROAD.CheckSDCFiles::SIGNOFF_SDC_FILE`

```json
    "PNR_SDC_FILE": "dir::cons.sdc",
    "SIGNOFF_SDC_FILE": "dir::cons.sdc",
```

______________________________________________________________________

### `Magic.DRC`

Under the directory `xx-magic-drc`, you will find a file named `reports/drc.rpt`
that summarizes the DRC violations reported by magic. The design is DRC clean so
the report will look like this:

```text
aes_wb_wrapper
----------------------------------------
[INFO] COUNT: 0
[INFO] Should be divided by 3 or 4


```

______________________________________________________________________

### `KLayout.DRC`

Under the directory `xx-klayout-drc`, you will find a file named
`violations.json` that summarizes the DRC violations reported by KLayout. The
design is DRC clean so the report will look like this with `"total": 0` at the
end:

```text
{
  ⋮
  "total": 0
}

```

______________________________________________________________________

### `Netgen.LVS`

Under the directory `xx-netgen-lvs`, you will find a file named `lvs.rpt` that
summarizes the LVS violations reported by Netgen. The design is LVS clean so the
last part of the report will look like this:

```text
Cell pin lists are equivalent.
Device classes user_project_wrapper and user_project_wrapper are equivalent.

Final result: Circuits match uniquely.

```

______________________________________________________________________

## Re-running the flow with a modified configuration

To fix the previous issues in the implementation, the following was added to the
`user_project_wrapper` config file:

```json
    "//": "New variables",
    "GRT_ANTENNA_ITERS": 10,
    "RUN_HEURISTIC_DIODE_INSERTION": true,
    "HEURISTIC_ANTENNA_THRESHOLD": 200,
    "DESIGN_REPAIR_MAX_WIRE_LENGTH": 800,
    "PL_WIRE_LENGTH_COEF": 0.05,
    "DEFAULT_CORNER": "max_tt_025C_1v80",
    "RUN_POST_GRT_DESIGN_REPAIR": true,
    "RUN_POST_GRT_RESIZER_TIMING": true,
```

and the following constraints file `pnr.sdc` was created at
`~/caravel_aes_accelerator/openlane/user_project_wrapper/`. This file is
originally copied from
`~/caravel_aes_accelerator/openlane/user_project_wrapper/signoff.sdc` and edited
to fix the transition and hold violations:

````{dropdown} pnr.sdc
```tcl
# Copied from signoff.sdc then edited

## Note:
# - input clock transition and latency are set for wb_clk_i port.
#   If your design is using the user_clock2, update the clock constraints to reflect that and use usr_* variables.
# - IO ports are assumed to be asynchronous. If they're synchronous to the clock, update the variable IO_SYNC to 1.
#   As well, update in_ext_delay and out_ext_delay with the required I/O external delays.

#------------------------------------------#
# Pre-defined Constraints
#------------------------------------------#

set ::env(IO_SYNC) 0
# Clock network
if {[info exists ::env(CLOCK_PORT)] && $::env(CLOCK_PORT) != ""} {
    set clk_input $::env(CLOCK_PORT)
    create_clock [get_ports $clk_input] -name clk -period $::env(CLOCK_PERIOD)
    puts "\[INFO\]: Creating clock {clk} for port $clk_input with period: $::env(CLOCK_PERIOD)"
} else {
    set clk_input __VIRTUAL_CLK__
    create_clock -name clk -period $::env(CLOCK_PERIOD)
    puts "\[INFO\]: Creating virtual clock with period: $::env(CLOCK_PERIOD)"
}
if { ![info exists ::env(SYNTH_CLK_DRIVING_CELL)] } {
    set ::env(SYNTH_CLK_DRIVING_CELL) $::env(SYNTH_DRIVING_CELL)
}
if { ![info exists ::env(SYNTH_CLK_DRIVING_CELL_PIN)] } {
    set ::env(SYNTH_CLK_DRIVING_CELL_PIN) $::env(SYNTH_DRIVING_CELL_PIN)
}

# Clock non-idealities
set_propagated_clock [all_clocks]
set_clock_uncertainty 0.15 [get_clocks {clk}]
puts "\[INFO\]: Setting clock uncertainty to: 0.15"
set_clock_transition $::env(SYNTH_CLOCK_TRANSITION) [get_clocks {clk}]
puts "\[INFO\]: Setting clock transition to: $::env(SYNTH_CLOCK_TRANSITION)"

# Maximum transition time for the design nets
set_max_transition 0.75 [current_design]
puts "\[INFO\]: Setting maximum transition to: 0.75"

# Maximum fanout
set_max_fanout 16 [current_design]
puts "\[INFO\]: Setting maximum fanout to: 16"

# Timing paths delays derate
set_timing_derate -early [expr {1-0.07}]
set_timing_derate -late [expr {1+0.07}]
puts "\[INFO\]: Setting timing derate to: [expr {0.07 * 100}] %"

# Reset input delay
set_input_delay [expr $::env(CLOCK_PERIOD) * 0.5] -clock [get_clocks {clk}] [get_ports {wb_rst_i}]

# Multicycle paths
set_multicycle_path -setup 2 -through [get_ports {wbs_ack_o}]
set_multicycle_path -hold 1  -through [get_ports {wbs_ack_o}]
set_multicycle_path -setup 2 -through [get_ports {wbs_cyc_i}]
set_multicycle_path -hold 1  -through [get_ports {wbs_cyc_i}]
set_multicycle_path -setup 2 -through [get_ports {wbs_stb_i}]
set_multicycle_path -hold 1  -through [get_ports {wbs_stb_i}]

#------------------------------------------#
# Retrieved Constraints
#------------------------------------------#

# Clock source latency
set usr_clk_max_latency 4.57
set usr_clk_min_latency 4.11
set clk_max_latency 5.57
set clk_min_latency 4.65
set_clock_latency -source -max $clk_max_latency [get_clocks {clk}]
set_clock_latency -source -min $clk_min_latency [get_clocks {clk}]
puts "\[INFO\]: Setting clock latency range: $clk_min_latency : $clk_max_latency"

# Clock input Transition
set usr_clk_tran 0.13
set clk_tran 0.61
set_input_transition $clk_tran [get_ports $clk_input]
puts "\[INFO\]: Setting clock transition: $clk_tran"

# Input delays
set_input_delay -max 1.87 -clock [get_clocks {clk}] [get_ports {la_data_in[*]}]
set_input_delay -max 1.89 -clock [get_clocks {clk}] [get_ports {la_oenb[*]}]
set_input_delay -max 3.17 -clock [get_clocks {clk}] [get_ports {wbs_sel_i[*]}]
set_input_delay -max 3.74 -clock [get_clocks {clk}] [get_ports {wbs_we_i}]
set_input_delay -max 3.89 -clock [get_clocks {clk}] [get_ports {wbs_adr_i[*]}]
set_input_delay -max 4.13 -clock [get_clocks {clk}] [get_ports {wbs_stb_i}]
set_input_delay -max 4.61 -clock [get_clocks {clk}] [get_ports {wbs_dat_i[*]}]
set_input_delay -max 4.74 -clock [get_clocks {clk}] [get_ports {wbs_cyc_i}]
set_input_delay -min 0.18 -clock [get_clocks {clk}] [get_ports {la_data_in[*]}]
set_input_delay -min 0.3  -clock [get_clocks {clk}] [get_ports {la_oenb[*]}]
set_input_delay -min 0.79 -clock [get_clocks {clk}] [get_ports {wbs_adr_i[*]}]
# wbs_dat_i minimum input delay was decreased here to fix hold violations
set_input_delay -min 0.80 -clock [get_clocks {clk}] [get_ports {wbs_dat_i[*]}]
set_input_delay -min 1.19 -clock [get_clocks {clk}] [get_ports {wbs_sel_i[*]}]
set_input_delay -min 1.65 -clock [get_clocks {clk}] [get_ports {wbs_we_i}]
set_input_delay -min 1.69 -clock [get_clocks {clk}] [get_ports {wbs_cyc_i}]
set_input_delay -min 1.86 -clock [get_clocks {clk}] [get_ports {wbs_stb_i}]
if { $::env(IO_SYNC) } {
    set in_ext_delay 4
    puts "\[INFO\]: Setting input ports external delay to: $in_ext_delay"
    set_input_delay -max [expr $in_ext_delay + 4.55] -clock [get_clocks {clk}] [get_ports {io_in[*]}]
    set_input_delay -min [expr $in_ext_delay + 1.26] -clock [get_clocks {clk}] [get_ports {io_in[*]}]
}

# Input Transition
set_input_transition -max 0.14  [get_ports {wbs_we_i}]
set_input_transition -max 0.15  [get_ports {wbs_stb_i}]
set_input_transition -max 0.17  [get_ports {wbs_cyc_i}]
set_input_transition -max 0.18  [get_ports {wbs_sel_i[*]}]
set_input_transition -max 0.38  [get_ports {io_in[*]}]
set_input_transition -max 0.84  [get_ports {wbs_dat_i[*]}]
set_input_transition -max 0.86  [get_ports {la_data_in[*]}]
set_input_transition -max 0.92  [get_ports {wbs_adr_i[*]}]
set_input_transition -max 0.97  [get_ports {la_oenb[*]}]
set_input_transition -min 0.05  [get_ports {io_in[*]}]
set_input_transition -min 0.06  [get_ports {la_oenb[*]}]
set_input_transition -min 0.07  [get_ports {la_data_in[*]}]
set_input_transition -min 0.07  [get_ports {wbs_adr_i[*]}]
set_input_transition -min 0.07  [get_ports {wbs_dat_i[*]}]
set_input_transition -min 0.09  [get_ports {wbs_cyc_i}]
set_input_transition -min 0.09  [get_ports {wbs_sel_i[*]}]
set_input_transition -min 0.09  [get_ports {wbs_we_i}]
set_input_transition -min 0.15  [get_ports {wbs_stb_i}]

# Output delays
set_output_delay -max 0.7  -clock [get_clocks {clk}] [get_ports {user_irq[*]}]
set_output_delay -max 1.0  -clock [get_clocks {clk}] [get_ports {la_data_out[*]}]
set_output_delay -max 3.62 -clock [get_clocks {clk}] [get_ports {wbs_dat_o[*]}]
set_output_delay -max 8.41 -clock [get_clocks {clk}] [get_ports {wbs_ack_o}]
set_output_delay -min 0    -clock [get_clocks {clk}] [get_ports {la_data_out[*]}]
set_output_delay -min 0    -clock [get_clocks {clk}] [get_ports {user_irq[*]}]
set_output_delay -min 1.13 -clock [get_clocks {clk}] [get_ports {wbs_dat_o[*]}]
set_output_delay -min 1.37 -clock [get_clocks {clk}] [get_ports {wbs_ack_o}]
if { $::env(IO_SYNC) } {
    set out_ext_delay 4
    puts "\[INFO\]: Setting output ports external delay to: $out_ext_delay"
    set_output_delay -max [expr $out_ext_delay + 9.12] -clock [get_clocks {clk}] [get_ports {io_out[*]}]
    set_output_delay -max [expr $out_ext_delay + 9.32] -clock [get_clocks {clk}] [get_ports {io_oeb[*]}]
    set_output_delay -min [expr $out_ext_delay + 2.34] -clock [get_clocks {clk}] [get_ports {io_oeb[*]}]
    set_output_delay -min [expr $out_ext_delay + 3.9]  -clock [get_clocks {clk}] [get_ports {io_out[*]}]
}

# Output loads
set_load 0.19 [all_outputs]
```
````

Then, the PnR SDC file path was edited in the JSON file.

```json
    "PNR_SDC_FILE": "dir::pnr.sdc",
```

Now the final
`~/caravel_aes_accelerator/openlane/user_project_wrapper/config.json` file will
be:

````{dropdown} config.json
```json
{
    "//": "Design files",
    "VERILOG_FILES": [
        "dir::../../../secworks_aes/src/rtl/*.v",
        "dir::../../verilog/rtl/aes_wb_wrapper.v",
        "dir::../../verilog/rtl/defines.v",
        "dir::../../verilog/rtl/user_project_wrapper.v"
    ],
    "PNR_SDC_FILE": "dir::pnr.sdc",
    
    "//": "Hardening strategy variables (this is for 2-Full-Wrapper Flattening). Visit https://docs.google.com/document/d/1pf-wbpgjeNEM-1TcvX2OJTkHjqH_C9p-LURCASS0Zo8 for more info",
    "SYNTH_ELABORATE_ONLY": false,
    "RUN_POST_GPL_DESIGN_REPAIR": true,
    "RUN_POST_CTS_RESIZER_TIMING": true,
    "DESIGN_REPAIR_BUFFER_INPUT_PORTS": true,
    "PDN_ENABLE_RAILS": true,
    "RUN_ANTENNA_REPAIR": true,
    "RUN_FILL_INSERTION": true,
    "RUN_TAP_ENDCAP_INSERTION": true,
    "RUN_CTS": true,
    "RUN_IRDROP_REPORT": true,
    "VSRC_LOC_FILES": {
        "vccd1": "dir::vsrc/upw_vccd1_vsrc.loc",
        "vssd1": "dir::vsrc/upw_vssd1_vsrc.loc"
    },

    "//": "PDN configurations",
    "PDN_VOFFSET": 5,
    "PDN_HOFFSET": 5,
    "PDN_VWIDTH": 3.1,
    "PDN_HWIDTH": 3.1,
    "PDN_VSPACING": 15.5,
    "PDN_HSPACING": 15.5,
    "PDN_VPITCH": 180,
    "PDN_HPITCH": 180,
    "QUIT_ON_PDN_VIOLATIONS": false,

    "//": "Magic variables",
    "MAGIC_DRC_USE_GDS": true,
    "MAX_TRANSITION_CONSTRAINT": 1.5,

    "//": "New variables",
    "GRT_ANTENNA_ITERS": 10,
    "RUN_HEURISTIC_DIODE_INSERTION": true,
    "HEURISTIC_ANTENNA_THRESHOLD": 200,
    "DESIGN_REPAIR_MAX_WIRE_LENGTH": 800,
    "PL_WIRE_LENGTH_COEF": 0.05,
    "DEFAULT_CORNER": "max_tt_025C_1v80",
    "RUN_POST_GRT_DESIGN_REPAIR": true,
    "RUN_POST_GRT_RESIZER_TIMING": true,

    "//": "Fixed configurations for Caravel. You should NOT edit this section",
    "DESIGN_NAME": "user_project_wrapper",
    "FP_SIZING": "absolute",
    "DIE_AREA": [0, 0, 2920, 3520],
    "FP_DEF_TEMPLATE": "dir::fixed_dont_change/user_project_wrapper.def",
    "VDD_NETS": [
        "vccd1",
        "vccd2",
        "vdda1",
        "vdda2"
    ],
    "GND_NETS": [
        "vssd1",
        "vssd2",
        "vssa1",
        "vssa2"
    ],
    "PDN_CORE_RING": 1,
    "PDN_CORE_RING_VWIDTH": 3.1,
    "PDN_CORE_RING_HWIDTH": 3.1,
    "PDN_CORE_RING_VOFFSET": 12.45,
    "PDN_CORE_RING_HOFFSET": 12.45,
    "PDN_CORE_RING_VSPACING": 1.7,
    "PDN_CORE_RING_HSPACING": 1.7,
    "CLOCK_PORT": "wb_clk_i",
    "SIGNOFF_SDC_FILE": "dir::signoff.sdc",
    "MAGIC_DEF_LABELS": 0,
    "CLOCK_PERIOD": 25,
    "MAGIC_ZEROIZE_ORIGIN": 0
}
```
````

Now let's try re-running the flow:

```console
[nix-shell:~/librelane]$ librelane ~/caravel_aes_accelerator/openlane/user_project_wrapper/config.json
```

The flow will finish successfully in ~2 hours and we will see:

```console
Flow complete.
```

______________________________________________________________________

## Re-checking the reports

Now, the antenna report under
`xx-openroad-checkantennas-1/reports/antenna_summary.rpt` has much less
violations:

```text
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┓
┃ Partial/Required ┃ Required ┃ Partial ┃ Net                                 ┃ Pin        ┃ Layer ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━┩
│ 2.03             │ 400.00   │ 810.79  │ _08755_                             │ _19772_/C  │ met3  │
│ 2.00             │ 400.00   │ 798.00  │ _14836_                             │ _28092_/A  │ met1  │
│ 1.75             │ 400.00   │ 701.33  │ _11832_                             │ _22711_/A0 │ met1  │
│ 1.70             │ 400.00   │ 678.78  │ _11884_                             │ _22770_/A0 │ met1  │
│ 1.62             │ 400.00   │ 647.67  │ net1481                             │ _25071_/B  │ met1  │
│ 1.61             │ 3130.28  │ 5050.41 │ _14758_                             │ _28362_/B  │ met4  │
│ 1.40             │ 3130.28  │ 4394.16 │ _14751_                             │ _28352_/B  │ met4  │
│ 1.39             │ 3130.28  │ 4350.98 │ _14707_                             │ _28292_/B  │ met4  │
⋮
```

Also, the STA report `xx-openroad-stapostpnr/summary.rpt` has no issues:

```text
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃              ┃ Hold Worst   ┃ Reg to Reg   ┃          ┃ Hold         ┃ of which Reg ┃ Setup Worst  ┃ Reg to Reg   ┃           ┃ Setup         ┃ of which Reg ┃ Max Cap       ┃ Max Slew     ┃
┃ Corner/Group ┃ Slack        ┃ Paths        ┃ Hold TNS ┃ Violations   ┃ to Reg       ┃ Slack        ┃ Paths        ┃ Setup TNS ┃ Violations    ┃ to Reg       ┃ Violations    ┃ Violations   ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Overall      │ 0.0486       │ 0.0486       │ 0.0000   │ 0            │ 0            │ 5.2837       │ 5.2837       │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ nom_tt_025C… │ 0.2274       │ 0.2274       │ 0.0000   │ 0            │ 0            │ 11.0726      │ 15.1596      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ nom_ss_100C… │ 0.2414       │ 0.7146       │ 0.0000   │ 0            │ 0            │ 5.8981       │ 5.8981       │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ nom_ff_n40C… │ 0.0497       │ 0.0497       │ 0.0000   │ 0            │ 0            │ 11.0978      │ 18.6822      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ min_tt_025C… │ 0.2253       │ 0.2253       │ 0.0000   │ 0            │ 0            │ 11.0640      │ 15.5219      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ min_ss_100C… │ 0.3307       │ 0.7108       │ 0.0000   │ 0            │ 0            │ 6.5295       │ 6.5295       │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ min_ff_n40C… │ 0.0486       │ 0.0486       │ 0.0000   │ 0            │ 0            │ 11.0946      │ 18.9314      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ max_tt_025C… │ 0.2292       │ 0.2292       │ 0.0000   │ 0            │ 0            │ 11.0804      │ 14.7813      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ max_ss_100C… │ 0.1453       │ 0.7174       │ 0.0000   │ 0            │ 0            │ 5.2837       │ 5.2837       │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
│ max_ff_n40C… │ 0.0509       │ 0.0509       │ 0.0000   │ 0            │ 0            │ 11.0951      │ 18.3978      │ 0.0000    │ 0             │ 0            │ 0             │ 0            │
└──────────────┴──────────────┴──────────────┴──────────┴──────────────┴──────────────┴──────────────┴──────────────┴───────────┴───────────────┴──────────────┴───────────────┴──────────────┘
```

______________________________________________________________________

## Saving the views

To save the views, run the following script with the following arguments in
order:

1. The directory of the project
1. The macro name
1. The successful run tag

```console
[nix-shell:~/librelane]$ bash ~/caravel_aes_accelerator/openlane/copy_views.sh ~/caravel_aes_accelerator user_project_wrapper RUN_TAG
```

This will copy the physical views of the macro in the specified run to your
project folder.

Congrats! Now you have another AES accelerator as a Caravel user project.
