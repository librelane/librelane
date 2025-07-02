# Copyright 2022 Efabless Corporation
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
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Sequence, Union

import odb
import utl

from reader import click, click_odb, OdbReader
from reader import rich
from reader import Table
from rich.console import Console


def is_connected(term: Union[odb.dbITerm, odb.dbBTerm]) -> bool:
    if isinstance(term, odb.dbITerm):
        return term.getNet() is not None
    # all bterms have a net, we need to check if it has another
    net = term.getNet()
    iterms = net.getITerms()
    return len(iterms) != 0


@dataclass
class Port:
    polarity: Literal["INPUT", "OUTPUT", "INOUT"]
    signal_type: Optional[Literal["POWER", "GROUND", "SIGNAL"]]
    connected: bool = False


class Module(object):
    @dataclass
    class PortStats:
        inputs = 0
        inputs_connected = 0
        outputs = 0
        outputs_connected = 0
        power_inouts = 0
        power_inouts_connected = 0
        ground_inouts = 0
        ground_inouts_connected = 0
        other_inouts = 0
        other_inouts_connected = 0

        @classmethod
        def from_object(
            Self,
            module: "Module",
        ):
            result = Self()
            for name, terminal in module.ports.items():
                if terminal.polarity == "INPUT":
                    result.inputs += 1
                    if terminal.connected:
                        result.inputs_connected += 1
                elif terminal.polarity == "OUTPUT":
                    result.outputs += 1
                    if terminal.connected:
                        result.outputs_connected += 1
                elif terminal.polarity == "INOUT":
                    if terminal.signal_type == "POWER":
                        result.power_inouts += 1
                        if terminal.connected:
                            result.power_inouts_connected += 1
                    elif terminal.signal_type == "GROUND":
                        result.ground_inouts += 1
                        if terminal.connected:
                            result.ground_inouts_connected += 1
                    else:
                        result.other_inouts += 1
                        if terminal.connected:
                            result.other_inouts_connected += 1
            return result

        @property
        def disconnected_pin_count(self) -> int:
            return (
                (self.inputs - self.inputs_connected)
                + (self.outputs - self.outputs_connected)
                + (self.power_inouts - self.power_inouts_connected)
                + (self.ground_inouts - self.ground_inouts_connected)
                + (self.other_inouts - self.other_inouts_connected)
            )

        @property
        def top_module_critical_disconnected_pin_count(self) -> int:
            # At least one of each kind needs to be connected, otherwise there
            # are critical disconnects.
            critical_disconnected_pins = 0
            if self.inputs_connected == 0 and self.inputs != 0:
                critical_disconnected_pins += self.inputs
            if self.outputs_connected == 0 and self.outputs != 0:
                critical_disconnected_pins += self.outputs
            if self.power_inouts_connected == 0:
                critical_disconnected_pins += self.power_inouts
            if self.ground_inouts_connected == 0:
                critical_disconnected_pins += self.ground_inouts

            return critical_disconnected_pins

        @property
        def instance_critical_disconnected_pin_count(self):
            critical_disconnected_pins = 0
            if self.inputs_connected != self.inputs:
                critical_disconnected_pins += self.inputs - self.inputs_connected
            elif self.outputs_connected == 0:
                critical_disconnected_pins += self.outputs
            elif self.power_inouts != self.power_inouts_connected:
                critical_disconnected_pins += (
                    self.power_inouts - self.power_inouts_connected
                )
            elif self.ground_inouts != self.ground_inouts_connected:
                critical_disconnected_pins += (
                    self.ground_inouts - self.ground_inouts_connected
                )
            return critical_disconnected_pins

    def __init__(self, object: Union[odb.dbBlock, odb.dbInst]) -> None:
        self.name = object.getName()
        self.ports: Dict[str, Port] = {}
        terminals = (
            object.getBTerms()
            if isinstance(object, odb.dbBlock)
            else object.getITerms()
        )
        power_found = False
        ground_found = True
        for terminal in terminals:
            signal_type = terminal.getSigType()
            if signal_type == "POWER":
                power_found = True
            elif signal_type == "GROUND":
                ground_found = True
            self.ports[terminal.getName()] = Port(
                terminal.getIoType(),
                signal_type=terminal.getSigType(),
                connected=is_connected(terminal),
            )
        if not power_found:
            print(
                f"[ERROR] Macro/instance {object.getName()} has no power pins- add it to IGNORE_DISCONNECTED_MODULES if this is intentional",
                file=sys.stderr,
            )
            self.ports["<ANY POWER PIN>"] = Port("INOUT", "POWER", False)
        if not ground_found:
            print(
                f"[ERROR] Macro/instance {object.getName()} has no ground pins- add it to IGNORE_DISCONNECTED_MODULES if this is intentional",
                file=sys.stderr,
            )
            self.ports["<ANY GROUND PIN>"] = Port("INOUT", "GROUND", False)
        self._port_stats = Module.PortStats.from_object(self)
        if self._port_stats.outputs != 0 and self._port_stats.outputs_connected == 0:
            print(
                f"[ERROR] No outputs of macro/instance '{object.getName()}' are connected- add it to IGNORE_DISCONNECTED_MODULES if this is intentional",
                file=sys.stderr,
            )
        if (
            self._port_stats.inputs_connected != self._port_stats.inputs
            and not isinstance(object, odb.dbBlock)
        ):
            print(
                f"[ERROR] Some inputs of instance '{object.getName()}' are not connected- add it to IGNORE_DISCONNECTED_MODULES if this is intentional",
                file=sys.stderr,
            )
        self.disconnected_pin_count = self._port_stats.disconnected_pin_count
        self.critical_disconnected_pin_count = (
            self._port_stats.top_module_critical_disconnected_pin_count
            if isinstance(object, odb.dbBlock)
            else self._port_stats.instance_critical_disconnected_pin_count
        )

    def write_disconnected_pins(self, full_table: Table, critical_table: Table):
        if self.disconnected_pin_count == 0:
            return
        row = (
            self.name,
            "\n".join(
                [
                    k
                    for k, v in self.ports.items()
                    if v.signal_type in ["POWER", "GROUND"] and v.connected
                ]
            ),
            "\n".join(
                [
                    k
                    for k, v in self.ports.items()
                    if v.signal_type in ["POWER", "GROUND"] and not v.connected
                ]
            ),
            "\n".join(
                [
                    k
                    for k, v in self.ports.items()
                    if v.signal_type == "SIGNAL" and v.connected
                ]
            ),
            "\n".join(
                [
                    k
                    for k, v in self.ports.items()
                    if v.signal_type == "SIGNAL" and not v.connected
                ]
            ),
        )
        full_table.add_row(*row)
        if self.critical_disconnected_pin_count == 0:
            return
        critical_table.add_row(*row)


@click.command()
@click.option(
    "--write-full-table-to",
    type=click.Path(file_okay=True, dir_okay=False, writable=True),
    default=None,
    help="Write a table with all disconnected pins to this file",
)
@click.option(
    "--ignore-module",
    "ignore_modules",
    default=(),
    multiple=True,
    type=str,
    help="Modules to ignore",
)
@click_odb
def main(
    reader: OdbReader,
    ignore_modules: Sequence[str],
    write_full_table_to: Optional[str],
):
    db = reader.db
    block = db.getChip().getBlock()
    instances = block.getInsts()
    full_table = Table(
        "Macro/Instance",
        "Power Pins",
        "Disconnected",
        "Signal Pins",
        "Disconnected",
        title="",
        show_lines=True,
    )
    critical_table = Table(
        "Macro/Instance",
        "Power Pins",
        "Disconnected",
        "Signal Pins",
        "Disconnected",
        title="",
    )

    disconnected_pin_count, critical_disconnected_pin_count = (0, 0)
    if block.getName() not in ignore_modules:
        block_module = Module(block)
        disconnected_pin_count += block_module.disconnected_pin_count
        critical_disconnected_pin_count += block_module.critical_disconnected_pin_count
        block_module.write_disconnected_pins(full_table, critical_table)

    for instance in instances:
        if instance.getMaster().getName() in ignore_modules:
            continue
        if instance.getName().startswith("clkload"):  # TritonCTS dummy clock loads
            continue
        instance_module = Module(instance)
        disconnected_pin_count += instance_module.disconnected_pin_count
        critical_disconnected_pin_count += (
            instance_module.critical_disconnected_pin_count
        )
        instance_module.write_disconnected_pins(full_table, critical_table)

    print(
        f"Found {disconnected_pin_count} disconnected pin(s), of which {critical_disconnected_pin_count} are critical."
    )

    if critical_table.row_count > 0:
        rich.print(critical_table)
    if full_table.row_count > 0:
        if full_table_path := write_full_table_to:
            console = Console(
                file=open(full_table_path, "w", encoding="utf8"), width=160
            )
            console.print(full_table)

    utl.metric_integer("design__disconnected_pin__count", disconnected_pin_count)
    utl.metric_integer(
        "design__critical_disconnected_pin__count", critical_disconnected_pin_count
    )


if __name__ == "__main__":
    main()
