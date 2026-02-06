# Using ECO Steps

{term}`Engineering Change Orders (ECOs) <ECO>` are a powerful tool you can use to
resolve issues with the circuit that:

- Are discovered late into PnR, where an RTL change would put you behind
  schedule
- Were not successfully resolved using automatic PnR tools

Classically, ECOs were done by the user manually opening the design database and
then re-running a part of the flow. LibreLane of course lets you do that if you
want:

```console
$ librelane --run-tag my_run ./config.yaml
[…]
[ERROR] Hold violations found.
$ openroad -gui ./runs/my_run/*-openroad-resizertimingpostgrt/*.odb
$ librelane --run-tag my_run_eco --with-initial-state ./runs/my_run/*-openroad-resizertimingpostgrt/state_out.json --from openroad.steamidpnr-3 ./config.yaml
[…]
[INFO] Flow successful.
```

```{tip}
To know the order of the steps in the default flow, invoke
`librelane.help Classic`. Steps are case-insensitive.
```

Though for issues that occur regularly on a particular pin or instance,
LibreLane actually provides a set of steps that let you:

* Insert a buffer on a specific driver or sink pin to help with hold violation
* Insert a diode on a specific sink pin to help with antenna violations

The two steps are {step}`Odb.InsertECOBuffers` and {step}`Odb.InsertECODiodes`.
They are not part of the default flow, so you will need to inject those steps
manually.

This tutorial will show `Odb.InsertECOBuffers`, but diodes work broadly
similarly (except the diode step only supports sinks and not drivers.)

## Example

Consider this quaint demonstrative design:

```verilog
module hold_violation(
  input clk,
  input d,
  output q
);
  wire intermediate;
  wire clk_delayed;

  sky130_fd_sc_hd__clkbuf_4 dly (
    .A(clk),
    .X(clk_delayed)
  );

  sky130_fd_sc_hd__dfrtp_4 u_ff1 (
    .CLK(clk),
    .D(d),
    .RESET_B(1'b1),
    .Q(intermediate)
  );

  sky130_fd_sc_hd__dfrtp_1 u_ff2 (
    .CLK(clk_delayed),
    .D(intermediate),
    .RESET_B(1'b1),
    .Q(q)
  );
endmodule
```

Here, the clock for `u_ff2` is delayed, forcing a hold violation into existence.
In a more realistic scenario, the resizer will invariably fix something so
simple, but for the sake of demonstration, let's just turn it off.

So running this config:

```yaml
DESIGN_NAME: hold_violation
CLOCK_PORT: clk
CLOCK_PERIOD: 5
VERILOG_FILES: dir::hold_violation.v
RUN_POST_CTS_RESIZER_TIMING: false
RUN_POST_GRT_RESIZER_TIMING: false
FP_SIZING: absolute
DIE_AREA: [0, 0, 100, 100]
```

…will invariably end up with hold violations at the typical corner:

```
Hold violations found in the following corners:
* max_ff_n40C_1v95
* min_ff_n40C_1v95
* nom_ff_n40C_1v95
```

Now, some designs are huge and it's something of a hassle to re-run routing
just to fix this issue. So what can we do in this case?

That's where LibreLane's ECO steps come in.

## Adding it to your flow

You can use the `meta.flow` and `meta.substituting_steps` keys to modify the
flow conveniently from your configuration file as follows:

<table>
<tr>
  <th>JSON</th>
  <th>YAML</th>
</tr>
<tr>
  <td>

  ```json
  {
    "meta": {
      "flow": "Classic",
      "substituting_steps": {
        "+OpenROAD.DetailedRouting": "Odb.InsertECOBuffers",
        "+Odb.InsertECOBuffers": "OpenROAD.DetailedRouting"
      }
    }
  }
  ```

  </td>
  <td>

```yaml
meta:
  flow: Classic
  substituting_steps:
    "+OpenROAD.DetailedRouting": "Odb.InsertECOBuffers"
    "+Odb.InsertECOBuffers": "OpenROAD.DetailedRouting"
```

  </td>
</tr>
</table>

> See {ref}`config-substituting-steps` for more info.

## Configuring buffers

But adding the step alone is not enough: you also need to tell it where you
need an ECO buffer inserted.

<table>
<tr>
  <th>JSON</th>
  <th>YAML</th>
</tr>
<tr>
  <td>

  ```json
  {
    "INSERT_ECO_BUFFERS": [
      {
        "target": "u_ff1/Q",
        "buffer": "sky130_fd_sc_hd__buf_1"
      }
    ]
  }
  ```

  </td>
  <td>

```yaml
INSERT_ECO_BUFFERS:
  - target: u_ff1/Q
    buffer: sky130_fd_sc_hd__buf_1
```

  </td>
</tr>
</table>

Then find the `state_out.json` for detailed routing:

`runs/RUN_2025-09-16_00-11-02/42-openroad-detailedrouting/state_out.json`

…and run this command:

```console
$ librelane ./config.yaml --with-initial-state runs/RUN_2025-09-16_00-11-02/42-openroad-detailedrouting/state_out.json --from odb.insertecobuffers
```

You'll now find that the hold violations at the typical corner have been solved,
but at the fast corner, there's still a violation as the buffer is too fast.
So what's the solution?

Well, just add another buffer.

<table>
<tr>
  <th>JSON</th>
  <th>YAML</th>
</tr>
<tr>
  <td>

  ```json
  {
    "INSERT_ECO_BUFFERS": [
      {
        "target": "u_ff1/Q",
        "buffer": "sky130_fd_sc_hd__buf_1"
      },
      {
        "target": "u_ff1/Q",
        "buffer": "sky130_fd_sc_hd__buf_1"
      }
    ]
  }
  ```

  </td>
  <td>

```yaml
INSERT_ECO_BUFFERS:
  - target: u_ff1/Q
    buffer: sky130_fd_sc_hd__buf_1
  - target: u_ff1/Q
    buffer: sky130_fd_sc_hd__buf_1
```

  </td>
</tr>
</table>

You will notice that the new {step}`OpenROAD.DetailedRouting` step added has a
much faster runtime; and that's because it only has to route nets that have been
modified as part of the ECO.
