#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2025 LibreLane Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import yaml
import click


@click.command()
@click.argument("filename")
@click.option("--pdk-family", help="The PDK family for which to get the hash.")
def get_pdk_hash(filename, pdk_family):
    """
    Prints the hash of the PDK family in filename.
    """

    with open(filename, "r") as file:
        pdk_hashes = yaml.safe_load(file)

        if pdk_family in pdk_hashes:
            print(pdk_hashes[pdk_family])
        else:
            sys.exit(1)


if __name__ == "__main__":
    get_pdk_hash()
