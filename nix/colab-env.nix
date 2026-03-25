# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  system,
  python3,
  symlinkJoin,
}:
symlinkJoin {
  name = "librelane-colab-env";
  paths = python3.pkgs.librelane.includedTools;
}
