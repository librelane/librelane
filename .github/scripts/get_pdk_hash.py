#!/usr/bin/env python3
# Copyright (c) 2025 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
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
