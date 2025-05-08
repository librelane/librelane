# Copyright 2025 The American University in Cairo
#
# Adapted from ioplace_parser
#
# Copyright 2020-2023 Efabless Corporation
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
import re
from enum import IntEnum
from typing import Literal, Optional, Dict, List, Union
from decimal import Decimal
import warnings

from dataclasses import dataclass, field


class Order(IntEnum):
    busMajor = 0
    bitMajor = 1


@dataclass
class Side:
    min_distance: Optional[Decimal] = None
    reverse_result: bool = False
    pins: List[Union[str, int]] = field(default_factory=list)
    sort_mode: Optional[Order] = Order.busMajor


VALUE_ANNOTATIONS = ["min_distance"]
STANDALONE_ANNOTATIONS = [
    "bus_major",
    "bit_major",
]


def parse(string: str) -> Dict[Literal["N", "E", "W", "S"], Side]:
    """
    Parses a pin configuration into a dictionary of the four cardinal sides.

    :param string: The input configuration as a string (not a file path)
    :returns: A dictionary where each cardinal direction points to a Side object.
    :raises ValueError: On syntax or token recognition errors
    """
    sides = {}
    current_side: Optional[Side] = None
    global_sort_mode: Order = Order.busMajor
    global_min_distance: Optional[Decimal] = None

    string_mut = string

    ws_rx = re.compile(r"^\s+")
    annotation_rx = re.compile(r"^@\s*(\w+)(?:\s*=\s*([0-9]+(?:.[0-9]+)?))?")
    direction_rx = re.compile(r"^#\s*([NEWS]R?|BUS_SORT)")
    virtual_pin_rx = re.compile(r"^\$\s*([0-9]+)")
    non_ws_rx = re.compile(r"^\S+")
    while len(string_mut):
        # annotation
        if skip_match := ws_rx.search(string_mut):
            string_mut = string_mut[skip_match.end() :]
        elif anno_match := annotation_rx.search(string_mut):
            annotation = anno_match[1]
            if annotation in VALUE_ANNOTATIONS:
                if anno_match[2] is None:
                    raise ValueError(f"Annotation {annotation} requires a value")
                value = anno_match[2]
                if annotation == "min_distance":
                    if current_side is None:
                        global_min_distance = Decimal(value)
                    else:
                        current_side.min_distance = Decimal(value)
            elif annotation in STANDALONE_ANNOTATIONS:
                if anno_match[2] is not None:
                    raise ValueError(
                        f"Annotation {annotation} cannot be assigned a value"
                    )
                if annotation == "bus_major":
                    if current_side is None:
                        global_sort_mode = Order.busMajor
                    else:
                        current_side.sort_mode = Order.busMajor
                elif annotation == "bit_major":
                    if current_side is None:
                        global_sort_mode = Order.bitMajor
                    else:
                        current_side.sort_mode = Order.bitMajor
            else:
                raise ValueError(f"Unknown annotation '{annotation}'")
            string_mut = string_mut[anno_match.end() :]
        elif dir_match := direction_rx.search(string_mut):
            direction = dir_match[1]
            if direction == "BUS_SORT":
                warnings.warn(
                    "Specifying bit-major using the direction token ('#BUS_SORT') is deprecated: use @bit_major."
                )
                global_sort_mode = Order.bitMajor
            else:
                current_side = Side(
                    min_distance=global_min_distance,
                    reverse_result=len(direction) == 2,
                    sort_mode=global_sort_mode,
                )
                side: Literal["N", "E", "W", "S"] = direction[0]  # type: ignore
                sides[side] = current_side
            string_mut = string_mut[dir_match.end() :]
        elif vp_match := virtual_pin_rx.search(string_mut):
            count = int(vp_match[1])
            if current_side is None:
                raise ValueError(
                    f"virtual pin declaration ${count} requires a direction to be set first"
                )
            current_side.pins.append(count)
            string_mut = string_mut[vp_match.end() :]
        elif nonws_match := non_ws_rx.match(string_mut):
            # assume regex
            if current_side is None:
                raise ValueError(
                    f"identifier/regex '{nonws_match[0]}' requires a direction to be set first"
                )
            current_side.pins.append(nonws_match[0])
            string_mut = string_mut[nonws_match.end() :]
        else:
            raise ValueError(
                f"Syntax Error: Unexpected character starting at {string_mut[:10]}…"
            )

    all_sides: List[Literal["N", "E", "W", "S"]] = ["N", "E", "W", "S"]
    for side in all_sides:
        if side in sides:
            continue
        sides[side] = Side(
            min_distance=global_min_distance,
            reverse_result=False,
            sort_mode=global_sort_mode,
        )

    return sides
