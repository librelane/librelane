# Implementing a Macro for Caravel

> Originally written by [Kareem Farid](https://github.com/kareefardi) and
> [Mohamed Hosni](https://github.com/mo-hosni)

```{admonition} Note
:class: seealso
If you do not have prior experience with LibreLane, please make sure to go
through the
[Getting Started: Newcomers](../../getting_started/newcomers/index.md) tutorial
first.
```

Initially released in 2020 by Efabless Corporation, the Caravel harness chip
is comprised of base functions supporting IO, power, and configuration as well
as drop-in modules for a management SoC core, and a ≈ 3mm x 3.6mm open project
area for the placement of user IP blocks.

Both OpenLane and LibreLane were initially developed for use with Caravel, which
in turn was created for the {term}`OpenMPW` project.

AES stands for Advanced Encryption Standard which is a symmetric encryption
algorithm widely used across the globe to secure data. It operates on blocks of
data using keys of 128, 192, or 256 bits to encrypt and decrypt information,
providing a high level of security and efficiency for electronic data
protection. In this tutorial, we are going to harden an `AES` core and have it
as a
[Caravel User Project](https://github.com/chipfoundry/caravel_user_project)
macro to serve as an accelerator for the chip
[Caravel](https://github.com/chipfoundry/caravel).

## Creating your own project repository

```{note}
For the purposes of this tutorial, we will be using a maintained fork of the
Caravel User Project by UmbraLogic Technologies LLC that uses LibreLane instead
of OpenLane.
```

1. Start by creating a new repository from the Caravel user project LibreLane
   [template](https://github.com/chipfoundry/caravel_user_project/generate).
   Let's call it `caravel_aes_accelerator`.

1. Open a terminal and clone your repository as follows:

   ```console
   $ git clone git@github.com:<github_user_name>/caravel_aes_accelerator.git ~/caravel_aes_accelerator
   ```

______________________________________________________________________

## RTL integration

We begin by using the open-source RTLs for AES by
[Joachim Strömbergson](https://github.com/secworks) and adding a Wishbone bus
wrapper for Caravel. Since the RTL from secworks provides a generic memory
interface, we only need to add the `ack`, `write_enable`, and `read_enable`
logic to the Wishbone wrapper.

1. Clone the `secworks/aes` Git repository

   ```console
   $ git clone git@github.com:secworks/aes.git ~/secworks_aes
   ```

1. Create the Verilog file
   `~/caravel_aes_accelerator/verilog/rtl/aes_wb_wrapper.v` and add the Wishbone
   wrapper to the RTL:

   ````{dropdown} aes_wb_wrapper.v

   ```{literalinclude} ./aes_wb_wrapper.v

   ```

   ````

1. Instantiate the `aes_wb_wrapper` in the `user_project_wrapper` Verilog file
   under `~/caravel_aes_accelerator/verilog/rtl`

   ````{dropdown} user_project_wrapper.v

   ```{literalinclude} ./user_project_wrapper.v

   ```

   ````

(configuration-user-project-wrapper)=

______________________________________________________________________

## Hardening strategies

There are 3 options for implementing a Caravel User Project design using
LibreLane:

1. `Macro-First Hardening`: Harden the user macro(s) initially and incorporate
   them into the user project wrapper without top-level standard cells. Ideal
   for smaller designs, as this approach significantly reduces {term}`Placement
   and Routing (PnR) <PnR>` and signoff time.
1. `Full-Wrapper Flattening`: Merge the user macro(s) with the
   user_project_wrapper, covering the entire wrapper area. While this method
   demands more time and iterations for PnR and signoff, it ultimately enhances
   performance, making it suitable for designs requiring the full wrapper area.
1. `Top-Level Integration`: A hybrid approach where the user macro(s) are
   hardened then instantiated in the wrapper alongside standard cells at the top
   level. This is useful to allow user macros to be harderned separately, but
   the top-level may still insert its own buffers or similar to handle boundary
   violations.

```{seealso}
See the
[Caravel Integration & Power Routing document](./ef_caravel_integration_power_routing.pdf)
(archived from
[original](https://docs.google.com/document/d/1pf-wbpgjeNEM-1TcvX2OJTkHjqH_C9p-LURCASS0Zo8))
for more information about these options.
```

For this tutorial, we will be following all three in order.

```{toctree}
:maxdepth: 1

./macro_first_hardening/index
./flattened_wrapper/index
./top_level_integration/index
```
