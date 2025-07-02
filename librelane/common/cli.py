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
from enum import IntEnum
from cloup import (
    HelpFormatter,
    HelpTheme,
    Style,
)
from typing import Optional, Type, Union

from click import (
    Choice,
    Context,
    Parameter,
)

formatter_settings = HelpFormatter.settings(
    theme=HelpTheme(
        invoked_command=Style(fg="bright_yellow"),
        heading=Style(fg="cyan", bold=True),
        constraint=Style(fg="magenta"),
        col1=Style(fg="bright_yellow"),
    )
)


class IntEnumChoice(Choice):
    def __init__(self, enum: Type[IntEnum], case_sensitive: bool = True) -> None:
        super().__init__([e.name for e in enum], case_sensitive)
        self.__enum = enum

    def convert(
        self,
        value: Union[str, int],
        param: Optional[Parameter],
        ctx: Optional[Context],
    ) -> IntEnum:
        try:
            if isinstance(value, int):
                return self.__enum(value)
            else:
                as_int: Optional[int] = None
                try:
                    as_int = int(value)
                except ValueError:
                    pass
                if as_int is not None:
                    return self.__enum(as_int)
                return self.__enum[value]
        except KeyError:
            self.fail(
                f"{value} is not a not a valid key nor value for IntEnum {self.__enum.__name__}"
            )
        except ValueError:
            self.fail(
                f"{value} is not a not a valid value for IntEnum {self.__enum.__name__}"
            )

    def get_metavar(self, param: Parameter) -> str:
        _bk = self.choices
        self.choices = [f"{e.name} or {e.value}" for e in self.__enum]
        result = super().get_metavar(param)
        self.choices = _bk
        return result
