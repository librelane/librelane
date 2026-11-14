# Copyright 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
import os
import sys

import click
from klayout.dbcore import LayerInfo, Layout, TilingProcessor
from klayout.rdbcore import ReportDatabase


@click.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    required=True,
    help="Klayout RDB (.xml) output file (required)",
)
@click.option(
    "-j",
    "--threads",
    type=int,
    default=os.cpu_count(),
    help="Lower bound on the thread count used by this process (+ managing threads)",
)
@click.option(
    "-T",
    "--tile-size",
    type=int,
    default=500,
    help="Tile size in µm",
)
@click.option(
    "-t",
    "--top",
    "design_name",
    required=True,
    help="Name of the design/top module",
)
@click.option(
    "-I", "--ignore", multiple=True, help="Layer ids ({layer}/{datatype}) to ignore"
)
@click.argument(
    "gds_a",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.argument(
    "gds_b",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def xor(output, threads, ignore, tile_size, design_name, gds_a, gds_b):
    try:
        print(f"[INFO] Using {threads} threads…", file=sys.stderr)

        a = Layout()
        a.read(gds_a)
        a_top = a.cell(design_name)

        b = Layout()
        b.read(gds_b)
        b_top = b.cell(design_name)

        x = Layout()
        xor_top = x.create_cell(design_name)
        xor_top.clear_shapes()

        report_name = f"XOR {gds_a} vs. {gds_b}"
        if os.path.basename(gds_a) != os.path.basename(gds_b):
            report_name = f"XOR {os.path.basename(gds_a)} vs. {os.path.basename(gds_b)}"
        rdb = ReportDatabase(report_name)
        rdbc = rdb.create_cell(design_name)

        tp = TilingProcessor()
        tp.threads = threads
        tp.tile_size(tile_size, tile_size)

        print(f"[INFO] Using a tile size of {tile_size} µm (square)…", file=sys.stderr)

        layers: dict[str, LayerInfo] = {}
        for layout in (a, b):
            for layer_index in layout.layer_indices():
                layer_info = layout.get_info(layer_index)
                layer_id = f"{layer_info.layer}/{layer_info.datatype}"
                layers[layer_id] = layer_info

        def _make_cat(layer_id):
            nonlocal rdb
            cat = rdb.create_category(layer_id)
            cat.description = f"XOR data for layer {layer_id}"
            return cat

        print("[INFO] Preparing layers for XOR…", file=sys.stderr)
        for layer_id in sorted(layers):
            if layer_id in ignore:
                print(f"[INFO] Skipping ignored layer {layer_id}…")
                continue
            layer_info = layers[layer_id]
            layer_slugified = layer_id.replace("/", "_")
            tp.input(f"a_{layer_slugified}", a, a_top.cell_index(), layer_info)
            tp.input(f"b_{layer_slugified}", b, b_top.cell_index(), layer_info)
            tp.output(f"xor_{layer_slugified}", x, xor_top.cell_index(), layer_info)
            ## there is a tp.output overload that enables us to pass the
            ## ReportDatabase directly, but it is currently missing in Python due to
            ## a bug
            # cat = _make_cat(layer_id)
            # tp.output(f"xor_{layer_slugified}", rdb, rdbc.rdb_id(), cat.rdb_id())
            tp.queue(
                f"_output(xor_{layer_slugified}, a_{layer_slugified} ^ b_{layer_slugified})"
            )

        print("[INFO] Starting XOR…", file=sys.stderr)
        tp.execute("XOR")

        print("[INFO] Generating XOR report…", file=sys.stderr)

        total_xor_differences = 0
        for layer_index in sorted(x.layer_indices()):
            layer_info = layout.get_info(layer_index)
            layer_id = f"{layer_info.layer}/{layer_info.datatype}"
            shapes = xor_top.shapes(layer_info)
            print(f"\t{layer_id}: {len(shapes)} differences")
            total_xor_differences += len(shapes)
            cat = _make_cat(layer_id)
            rdb.create_items(
                rdbc.rdb_id(),
                cat.rdb_id(),
                xor_top.begin_shapes_rec(layer_index),
            )
        rdb.save(output)

        print("---")
        print(f"Total XOR differences: {total_xor_differences}")
        print(f"%OL_METRIC_I design__xor_difference__count {total_xor_differences}")
    except Exception as e:
        print(e)
        try:
            import pya

            pya.Application.instance().exit(1)
        except AttributeError:
            sys.exit(1)


if __name__ == "__main__":
    # compatibility block for built-in interpreter
    argv_resolved = sys.argv
    if "karg0" in globals():
        argv_resolved: list[str] = []
        counter = 0
        try:
            while True:
                argv_resolved.append(globals()[f"karg{counter}"])
                counter += 1
        except KeyError:
            pass
    xor(argv_resolved[1:])
