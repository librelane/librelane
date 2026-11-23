# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
import io
from decimal import Decimal
from typing import AnyStr

from yaml import ScalarNode, YAMLError, load
from yamlcore import CCoreLoader

from ..types import AnyPath


class _OpenLaneYAMLLoader(CCoreLoader):
    def construct_yaml_float(self, node: ScalarNode) -> Decimal:  # type: ignore
        value = str(self.construct_scalar(node))
        value = value.replace("_", "").lower()
        sign = +1
        if value[0] == "-":
            sign = -1
        if value[0] in "+-":
            value = value[1:]
        if value == ".inf":
            return sign * Decimal("Infinity")
        elif value == ".nan":
            return Decimal("nan")
        else:
            return sign * Decimal(value)

    def __init__(self, stream) -> None:
        super().__init__(stream)
        self.add_constructor(
            "tag:yaml.org,2002:float",
            constructor=_OpenLaneYAMLLoader.construct_yaml_float,
        )


def yaml_load(f: io.TextIOWrapper):
    return load(f, _OpenLaneYAMLLoader)


def yaml_loads(s: AnyStr):
    return load(s, _OpenLaneYAMLLoader)


def yaml_loadp(p: AnyPath):
    with open(p, encoding="utf8") as f:
        return load(f, _OpenLaneYAMLLoader)


__all__ = [
    "YAMLError",
    "yaml_load",
    "yaml_loadp",
    "yaml_loads",
]
