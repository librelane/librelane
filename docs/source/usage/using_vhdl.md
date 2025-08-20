# Using VHDL

LibreLane supports VHDL by using the GHDL plugin for Yosys.

Instead of Librelane's “Classic” flow with Verilog support, we need to activate the “VHDLClassic” flow with VHDL support. This can be done by passing `--flow VHDLClassic` in the CLI, or it can permanently set in the configuration file.

As an example, take this `config.yaml` file:

```yaml
meta:
  flow: VHDLClassic

DESIGN_NAME: counter
VHDL_FILES: dir::counter.vhd
CLOCK_PORT: clk_i
CLOCK_PERIOD: 20 # 20ns = 50MHz
```

The only difference between the variables of the “Classic” flow  is that we use `VHDL_FILES` instead of `VERILOG_FILES`.

The `counter.vhd` in the same directory may look like this:

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

Now the flow can be run as usual:

```
librelane config.yaml
```