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

import os
import sys
import json
import shutil
from decimal import Decimal
from typing import Callable, List, Mapping, Tuple, Union, Optional, Dict, Any

from .design_format import (
    DesignFormat,
    DesignFormatObject,
)

from ..common import (
    Path,
    GenericImmutableDict,
    mkdirp,
    copy_recursive,
)
from ..logging import info


class InvalidState(RuntimeError):
    pass


StateElement = Union[Path, List[Path], Dict[str, Union[Path, List[Path]]], None]


class State(GenericImmutableDict[str, StateElement]):
    """
    Basically, a dictionary from :class:`DesignFormat`\\s and values
    of (nested dictionaries of) :class:`librelane.common.Path`\\.

    The state is the only thing that can be altered by steps other than the
    filesystem.

    States are **immutable**. To construct a new state with some modifications,
    you may do so as follows::

        state_b = State(
            copying=state_a,
            overrides={
                …
            },
            metrics=GenericImmutableDict(copying=state_a.metrics, overrides={
                …
            })
        )

    Though in the majority of cases, you do not have to construct States on your
    own: after executing a Step, you only return your deltas and then the Flow
    is responsible for the creation of a new Step object.

    :param copying: A mutable or immutable mapping to use as the starting
        value for this State.
    :param overrides: A mutable or immutable mapping to override the starting
        values with.
    :param metrics: A dictionary that carries statistics about the design: area,
        wire length, et cetera, but also miscellaneous data, for example, whether
        it passed a certain check or not.
    """

    def __init__(
        self,
        copying: Optional[
            Union[Mapping[str, StateElement], Mapping[DesignFormat, StateElement]]
        ] = None,
        *args,
        overrides: Optional[
            Union[Mapping[str, StateElement], Mapping[DesignFormat, StateElement]]
        ] = None,
        metrics: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> None:
        copying_resolved: Dict[str, StateElement] = {}
        if c_mapping := copying:
            for key, value in c_mapping.items():
                if isinstance(key, DesignFormat):
                    copying_resolved[key.value.id] = value
                else:
                    copying_resolved[key] = value

        for format in DesignFormat:
            assert isinstance(format.value, DesignFormatObject)  # type checker shut up
            if format.value.id not in copying_resolved:
                copying_resolved[format.value.id] = None

        overrides_resolved = {}
        if o_mapping := overrides:
            for k, value in o_mapping.items():
                if isinstance(k, DesignFormat):
                    assert isinstance(
                        k.value, DesignFormatObject
                    )  # type checker shut up
                    k = k.value.id
                overrides_resolved[k] = value

        self.metrics = GenericImmutableDict(metrics or {})

        super().__init__(
            copying_resolved,
            *args,
            overrides=overrides_resolved,
            **kwargs,
        )

    def __getitem__(self, key: Union[DesignFormat, str]) -> StateElement:
        if isinstance(key, DesignFormat):
            id: str = key.value.id
            key = id
        return super().__getitem__(key)

    def __setitem__(self, key: Union[DesignFormat, str], item: StateElement):
        if isinstance(key, DesignFormat):
            id: str = key.value.id
            key = id
        return super().__setitem__(key, item)

    def __delitem__(self, key: Union[DesignFormat, str]):
        if isinstance(key, DesignFormat):
            id: str = key.value.id
            key = id
        return super().__delitem__(key)

    def to_raw_dict(self, metrics: bool = True) -> Dict[str, Any]:
        final = super().to_raw_dict()
        if metrics:
            final["metrics"] = self.metrics.to_raw_dict()
        return final

    def copy(self: "State") -> "State":
        metrics: GenericImmutableDict[str, Any] = GenericImmutableDict(
            copy_recursive(self.metrics)
        )
        new = State(self, metrics=metrics)
        return new

    def _walk(
        self,
        views: Union[Dict, "State"],
        save_directory: Union[str, os.PathLike],
        visit: Callable[[str, StateElement, str, str, int], StateElement],
        key_path: str = "",
        depth: int = 0,
        top_key: Optional[str] = None,
    ):
        for key, value in views.items():
            current_top_key = top_key
            if current_top_key is None:
                current_top_key = key
            current_folder = key.strip("_*")
            if df := DesignFormat.by_id(key):
                # For type-checker: all guaranteed to be DesignFormatObjects
                assert isinstance(df.value, DesignFormatObject)
                current_folder = df.value.folder

            target_dir = os.path.join(save_directory, current_folder)

            current_key_path = f"{key_path}.{key}"
            visit(current_key_path, value, current_top_key, target_dir, depth)
            if isinstance(value, dict):
                self._walk(
                    value,
                    target_dir,
                    visit,
                    current_key_path,
                    depth + 1,
                    current_top_key,
                )
            if isinstance(value, list):
                for i, element in enumerate(value):
                    element_key_path = f"{current_key_path}[{i}]"
                    visit(
                        element_key_path,
                        element,
                        current_top_key,
                        target_dir,
                        depth + 1,
                    )

    def save_snapshot(self, path: Union[str, os.PathLike]):
        """
        Validates the current state then saves all views to a folder by
        design format, including the metrics.

        :param path: The folder that would contain other folders.
        """

        def visitor(key, value, top_key, save_directory, depth):
            if not isinstance(value, Path):
                return
            mkdirp(save_directory)
            target_path = os.path.join(save_directory, os.path.basename(value))
            shutil.copyfile(value, target_path, follow_symlinks=True)

        self.validate()
        info(f"Saving views to '{os.path.abspath(path)}'…")
        mkdirp(path)
        self._walk(self, path, visitor)
        metrics_csv_path = os.path.join(path, "metrics.csv")
        with open(metrics_csv_path, "w", encoding="utf8") as f:
            f.write("Metric,Value\n")
            for metric in self.metrics:
                f.write(f"{metric},{self.metrics[metric]}\n")

        metrics_json_path = os.path.join(path, "metrics.json")
        with open(metrics_json_path, "w", encoding="utf8") as f:
            f.write(self.metrics.dumps())

    def validate(self):
        """
        Ensures that all paths exist in a State.
        """

        def visitor(key, value, top_key, _, depth):
            if depth == 0 and DesignFormat.by_id(top_key) is None:
                raise InvalidState(
                    f"Key '{top_key}' does not match a known design format."
                )
            if value is None:
                return
            if not (
                isinstance(value, Path)
                or isinstance(value, dict)
                or isinstance(value, list)
            ):
                raise InvalidState(
                    f"Value at '{key}' is not a Path nor a dictionary/list of Paths: '{value}'."
                )

        self._walk(self.to_raw_dict(metrics=False), "", visit=visitor)

    @classmethod
    def __loads_recursive(
        Self,
        views: Dict,
        validate_path: bool = True,
        key_path: str = "",
    ) -> dict:
        target: dict = {}
        for key, value in views.items():
            current_key_path = f"{key_path}.{key}"
            if value is None:
                target[key] = value
                continue

            if isinstance(value, dict):
                target[key] = Self.__loads_recursive(
                    value,
                    validate_path,
                    key_path=current_key_path,
                )
            else:
                if validate_path and not os.path.exists(value):
                    raise ValueError(
                        f"Provided path '{value}' to design format '{current_key_path}' does not exist."
                    )
                target[key] = Path(value)
        return target

    @classmethod
    def loads(Self, json_in: str, validate_path: bool = True) -> "State":
        try:
            raw = json.loads(json_in, parse_float=Decimal)
        except json.JSONDecodeError as e:
            raise InvalidState(f"Invalid JSON string provided for state: {e}")

        if not isinstance(raw, dict):
            raise InvalidState("Failed to load state: JSON result is not a dictionary")

        metrics = raw.get("metrics")
        if metrics is not None:
            del raw["metrics"]

        views = Self.__loads_recursive(raw, validate_path)
        state = Self(views, metrics=metrics)

        return state

    def __mapping_to_html_rec(
        self,
        mapping: Mapping[str, Any],
        header_optional: Optional[Tuple[str, str]] = None,
    ):
        result = """
        <table style="grid-column-start: 1; grid-column-end: 2; ">
        """
        if header := header_optional:
            key_h, value_h = header
            result += f"""
                <tr>
                    <th style="text-align: left;">{key_h}</th>
                    <th style="text-align: left;">{value_h}</th>
                </tr>
            """

        for id, value in mapping.items():
            if value is None:
                continue

            key_content = id
            if format := DesignFormat.by_id(id):
                key_content = format.value.id

            value_content = str(value)
            if isinstance(value, Mapping):
                value_content = self.__mapping_to_html_rec(value)
            elif isinstance(value, Path):
                value_rel = os.path.relpath(value, ".")

                value_content = f'<a href="{value_rel}">{value_rel}</a>'
                if "google.colab" in sys.modules:
                    # Can't link in colab
                    value_content = value_rel

            result += f"""
                <tr>
                    <td style="text-align: left;">{key_content}</td>
                    <td style="text-align: left;">{value_content}</td>
                </tr>
            """

        result += """
        </table>
        """
        return result

    def _repr_html_(self) -> str:
        return (
            '<div style="display: grid; grid-auto-columns: minmax(0, 1fr); grid-auto-rows: minmax(0, 1fr); grid-auto-flow: column;">'
            + self.__mapping_to_html_rec(
                self.to_raw_dict(metrics=False),
                ("Format", "Path"),
            )
            + "</div>"
        )
