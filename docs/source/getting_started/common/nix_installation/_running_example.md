1. In your terminal, clone LibreLane as follows

   ```bash
   git clone https://github.com/librelane/librelane
   ```

1. Start a shell with LibreLane and its underlying utilities installed

   ```bash
   nix-shell librelane/shell.nix
   ```

1. Copy and run the `spm` example under a folder named `my_designs`

   ```bash
   mkdir my_designs
   cd my_designs/
   librelane --run-example spm
   ```
