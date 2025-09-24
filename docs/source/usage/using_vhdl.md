# Using VHDL

LibreLane supports VHDL **only on x86-64 platforms** by using the GHDL plugin
for Yosys.

Instead of Librelane's "Classic" flow which only has Verilog support, you will
need to use the "VHDLClassic" flow with VHDL support. This can be done by
either:

* Passing `--flow VHDLClassic` in the CLI
* Permanently setting the default flow for your design in the configuration file
  as follows:

  <table>
    <tr><th>JSON</th><th>YAML</tr></tr>
    <tr><td>

    ```json
    {
        "meta": {
            "flow": "VHDLClassic"
        }
    }
    ```

    </td><td>

    ```yaml
    meta:
      flow: VHDLClassic
    ```

    </td></tr>
  </table>

When using the `VHDLClassic` flow, you need to specify the variable
`VHDL_FILES` instead of `VERILOG_FILES`. 

As an example, consider this VHDL design, `counter.vhd`:

```vhdl
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity counter is
    port (
        clk_i   : in  std_logic;
        rst_ni  : in  std_logic;
        count_o : out std_logic_vector(7 downto 0)
    );
end entity counter;

architecture rtl of counter is

    signal count_reg : unsigned(7 downto 0);

begin

    count_o <= std_logic_vector(count_reg);

    process (clk_i)
    begin
        if rising_edge(clk_i) then
            if rst_ni = '1' then
                count_reg <= (others => '0');
            else
                count_reg <= count_reg + 1;
            end if;
        end if;
    end process;

end architecture;
```

To configure this design for LibreLane, you create a YAML file as follows:

```yaml
meta:
  flow: VHDLClassic

DESIGN_NAME: counter
VHDL_FILES: dir::counter.vhd
CLOCK_PORT: clk_i
CLOCK_PERIOD: 20 # 20ns = 50MHz
```

You may then run the flow as usual:

```console
$ librelane config.yaml
```

## Limitations

Unlike with Verilog, the LibreLane flow does not support:

* VHDL headers for macros

  If you use a macro, even if it is written in VHDL, the header exposing it to
  Yosys must be in Verilog for now. Of course, you don't need a header if you
  have a `.lib` file. See {doc}`/usage/using_macros` for more info.

* Automatic power connections for macros

  You will need to use the variable {var}`OpenROAD.GeneratePDN::PDN_MACRO_CONNECTIONS`:
  
  ```yaml
  PDN_MACRO_CONNECTIONS:
    - "<instance_name_regex> <vdd_net> <gnd_net> <vdd_pin> <gnd_pin>"
  ```
