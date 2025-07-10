# Copyright 2023 Efabless Corporation
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
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, ClassVar
from deprecated.sphinx import deprecated


class DFMetaclass(type):
    def __getattr__(Self, key: str):
        if df := Self.factory.get(key):
            return df
        raise AttributeError(
            "Unknown DesignFormat or Type[DesignFormat] attribute",
            key,
            Self,
        )


@dataclass
class DesignFormat(metaclass=DFMetaclass):
    """
    Metadata about the various possible text or binary representations (views)
    of any design.

    For example, ``DesignFormat.nl`` has the metadata for Netlist views.

    :param id: A lowercase alphanumeric/underscore identifier for the design
        format.
    :param extension: The file extension for designs saved in this format.
    :param full_name: A human-readable name for this design format.
    :param alts: A list of alternate ids used to access the DesignFormat by
        the subscript operator. Includes its OpenLane <3.0.0 enumeration name
        for limited backwards compatibility.
    :param folder_override: The subdirectory when
        :meth:`librelane.state.State.save_snapshot` is called on a state. If
        unset, the value for ``id`` will be used.
    :param multiple: Whether this view may have multiple files (typically, files
        that are different across multiple corners or similar.)
    """

    id: str
    extension: str
    full_name: str
    alts: List[str] = field(default_factory=list)
    folder_override: Optional[str] = None
    multiple: bool = False

    _instance_optional: bool = False

    @property
    def folder(self) -> str:
        return self.folder_override or self.id

    @property
    @deprecated(
        "The DesignFormat is directly returned now, no need for .value",
        version="3.0.0",
        action="once",
    )
    def value(self) -> DesignFormat:
        return self

    @property
    def optional(self) -> bool:
        return self._instance_optional

    @property
    @deprecated(
        ".name has been removed because it's redundant, use .id",
        version="3.0.0",
        action="once",
    )
    def name(self) -> str:
        return self.id

    def register(self):
        self.__class__.factory.register(self)

    def __str__(self) -> str:
        return self.id

    def __hash__(self):
        return hash(self.id)

    @staticmethod
    @deprecated(
        "Use DesignFormat.factory.get",
        version="3.0.0",
        action="once",
    )
    def by_id(id: str) -> Optional["DesignFormat"]:
        return DesignFormat.factory.get(id)

    class DesignFormatFactory(object):
        """
        A factory singleton for DesignFormats, allowing them to be registered
        and then retrieved by a string name.

        See https://en.wikipedia.org/wiki/Factory_(object-oriented_programming) for
        a primer.
        """

        _registry: ClassVar[Dict[str, DesignFormat]] = {}

        @classmethod
        def register(Self, df: DesignFormat) -> DesignFormat:
            """
            Adds a DesignFormat to the registry using its
            :attr:`DesignFormat.id`, :attr:`DesignFormat.name` and
            :attr:`DesignFormat.alts` attributes.
            """
            Self._registry[df.id] = df
            for alt in df.alts:
                Self._registry[alt] = df
            return df

        @classmethod
        def get(Self, name: str) -> Optional[DesignFormat]:
            """
            Retrieves a DesignFormat type from the registry using a lookup
            string.

            :param name: The registered name of the Step. Case-insensitive.
            """
            return Self._registry.get(name)

        @classmethod
        def list(Self) -> List[str]:
            """
            :returns: A list of IDs of all registered DesignFormat.
            """
            return [cls.id for cls in Self._registry.values()]

    factory: ClassVar = DesignFormatFactory

    def mkOptional(self) -> "DesignFormat":
        return replace(self, _instance_optional=True)


# Common Design Formats
DesignFormat(
    "nl",
    "nl.v",
    "Verilog Netlist",
    alts=["NETLIST"],
).register()

DesignFormat(
    "logical_nl",
    "logical_nl.v",
    "Logical cell-only Verilog Netlist",
    folder_override="nl",
).register()

DesignFormat(
    "pnl",
    "pnl.v",
    "Powered Verilog Netlist",
    alts=["POWERED_NETLIST"],
).register()

DesignFormat(
    "sdf_pnl",
    "sdf_pnl.v",
    "Powered Verilog Netlist for SDF Simulation (No Fills)",
    alts=["SDF_FRIENDLY_POWERED_NETLIST"],
    folder_override="pnl",
).register()

DesignFormat(
    "logical_pnl",
    "logical_pnl.v",
    "Logical cell-only Powered Verilog Netlist",
    alts=["LOGICAL_POWERED_NETLIST"],
    folder_override="pnl",
).register()

DesignFormat(
    "def",
    "def",
    "Design Exchange Format",
    alts=["def_", "DEF"],
).register()

DesignFormat(
    "lef",
    "lef",
    "Library Exchange Format",
    alts=["LEF"],
).register()

DesignFormat(
    "sdc",
    "sdc",
    "Design Constraints",
    alts=["SDC"],
).register()

DesignFormat(
    "sdf",
    "sdf",
    "Standard Delay Format",
    alts=["SDF"],
    multiple=True,
).register()

DesignFormat(
    "spef",
    "spef",
    "Standard Parasitics Extraction Format",
    alts=["SPEF"],
    multiple=True,  # nom, min, max, ...
).register()

DesignFormat(
    "lib",
    "lib",
    "LIB Timing Library Format",
    alts=["LIB"],
    multiple=True,
).register()

DesignFormat(
    "spice",
    "spice",
    "Simulation Program with Integrated Circuit Emphasis",
    alts=["SPICE"],
).register()

DesignFormat(
    "cdl",
    "cdl",
    "Circuit Design Language",
    alts=["CDL"],
).register()

DesignFormat(
    "gds",
    "gds",
    "GDSII Stream",
    alts=["GDS"],
).register()

DesignFormat(
    "vh",
    "vh",
    "Verilog Header",
    alts=["VERILOG_HEADER"],
).register()
