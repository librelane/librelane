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
import os
import json
import dataclasses
from enum import Enum
from decimal import Decimal
from collections import UserString
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    ItemsView,
    Iterator,
    Mapping,
    Sequence,
    Type,
    TypeVar,
    Tuple,
    Optional,
)

from .misc import idem
from .types import is_string


class GenericDictEncoder(json.JSONEncoder):
    """
    A JSON encoder for :class:`GenericDict` objects. Also handles some types not
    necessarily handled by the default JSON encoder, i.e., UserString, os.PathLike,
    Decimals, etcetera.

    It is recommended to use :meth:`GenericDict.to_json` unless you know what
    you're doing.
    """

    def default(self, o):
        if isinstance(o, GenericDict):
            return o.to_raw_dict()
        elif isinstance(o, os.PathLike) or isinstance(o, UserString):
            return str(o)
        elif not isinstance(o, type) and dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return o.name
        elif isinstance(o, Decimal):
            if o.is_infinite() or o.as_integer_ratio()[1] != 1:
                return float(o)
            else:
                return int(o)
        return o


KT = TypeVar("KT", bound=Hashable)
VT = TypeVar("VT")


class GenericDict(Mapping[KT, VT]):
    """
    A dictionary with generic keys and values that is compatible with Python 3.8.1.

    :param copying: A base Mapping object to copy values from.
    :param overrides: Another mapping object to override the value from `copying`
        with.
    """

    _data: Dict[KT, VT]

    def __init__(
        self,
        copying: Optional[Mapping[KT, VT]] = None,
        /,
        overrides: Optional[Mapping[KT, VT]] = None,
    ) -> None:
        super().__init__()
        self.__data = {}
        copying = copying or {}
        overrides = overrides or {}

        for key, value in copying.items():
            self.__data[key] = value
        for key, value in overrides.items():
            self.__data[key] = value

    def __getitem__(self, key: KT) -> VT:
        return self.__data[key]

    def __setitem__(self, key: KT, item: VT):
        self.__data[key] = item

    def __delitem__(self, key: KT):
        del self.__data[key]

    def __len__(self) -> int:
        return len(self.__data)

    def __repr__(self) -> str:
        return self.to_raw_dict().__repr__()

    def __iter__(self) -> Iterator[KT]:
        return iter(self.__data)

    def __eq__(self, __o: object) -> bool:
        if not (isinstance(__o, GenericDict) or isinstance(__o, dict)):
            raise NotImplementedError()

        rhs = __o
        if isinstance(__o, GenericDict):
            rhs = __o.to_raw_dict()

        lhs = self.to_raw_dict()

        return rhs == lhs

        # ---
        for key in set(self.keys()).union(__o.keys()):
            if key not in self or key not in __o:
                return False
            if self[key] != __o[key]:
                return False
        return True

    def pop(self, key: KT, /) -> VT:
        """
        :param key: The key to pop the value for.
        :returns: The value for key. Raises ``IndexError`` if the key does not
            exist. The key/value pair is then deleted from the dictionary.
        """
        value = self[key]
        del self[key]
        return value

    T = TypeVar("T", bound="GenericDict")

    def copy(self: T) -> T:
        """
        Convenience replacement for `object.__class__(object)`, which would
        create a copy of the ``GenericDict`` object.

        :returns: The copy
        """
        return self.__class__(self)

    def to_raw_dict(self) -> dict:
        """
        :returns: A copy of the underlying Python built-in ``dict`` for this class.
        """
        return self.__data.copy()

    def get_encoder(self) -> Type[GenericDictEncoder]:
        """
        :returns: A JSON encoder handling GenericDict objects.
        """
        return GenericDictEncoder

    def keys(self):
        """
        :returns: A set-like object providing a view of the keys of the GenericDict object.
        """
        return self.__data.keys()

    def values(self):
        """
        :returns: A set-like object providing a view of the values of the GenericDict object.
        """
        return self.__data.values()

    def items(self) -> ItemsView[KT, VT]:
        """
        :returns: A set-like object providing a view of the GenericDict object as (key, value) tuples.
        """
        return self.__data.items()

    def dumps(self, **kwargs) -> str:
        """
        :param kwargs: Passed to ``json.dumps``.
        :returns: A JSON string representing the the GenericDict object.
        """
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        return json.dumps(self.to_raw_dict(), cls=self.get_encoder(), **kwargs)

    def check(self, key: KT, /) -> Tuple[Optional[KT], Optional[VT]]:
        """
        Checks if a key exists and returns a tuple in the form ``(key, value)``.

        :param key: The key in question
        :returns: If the key does not exist, the value of ``key`` will be ``None`` and so will
            ``value``. If the key exists, ``key`` will be the key being checked for
            existence and ``value`` will be the value assigned to said key in the
            GenericDict object.

            Do note ``None`` is a valid value for some keys, so simply
            checking if the second element ``is not None`` is insufficient to check
            whether a key exists.
        """
        return (key if key in self.__data else None, self.get(key))

    def update(self, incoming: "Mapping[KT, VT]"):
        """
        A convenience function to update multiple values in the GenericDict object
        at the same time.
        :param incoming: The values to update
        """
        for key, value in incoming.items():
            self[key] = value

    def update_reorder(self, incoming: "Mapping[KT, VT]"):
        """
        A convenience function to update multiple values in the GenericDict object
        at the same time. Pre-existing keys are deleted first so the values in
        incoming are emplaced at the end of the dictionary.

        :param incoming: The values to update
        """
        for key, value in incoming.items():
            if key in self:
                del self[key]
            self[key] = value


class GenericImmutableDict(GenericDict[KT, VT]):
    __lock: bool

    def __init__(
        self,
        copying: Optional[Mapping[KT, VT]] = None,
        /,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(copying, *args, **kwargs)
        self.__lock = True

    def __setitem__(self, key: KT, item: VT):
        if self.__lock:
            raise TypeError(f"{self.__class__.__name__} is immutable")
        return super().__setitem__(key, item)

    def __delitem__(self, key: KT):
        if self.__lock:
            raise TypeError(f"{self.__class__.__name__} is immutable")
        return super().__delitem__(key)

    def __delattr__(self, attr: str):
        if self.__lock:
            raise TypeError(f"{self.__class__.__name__} is immutable")
        return super().__delattr__(attr)

    def __setattr__(self, attr: str, value: Any):
        try:
            if self.__lock:
                raise TypeError(f"{self.__class__.__name__} is immutable")
        except AttributeError:
            pass
        return super().__setattr__(attr, value)

    def copy_mut(self) -> GenericDict[KT, VT]:
        return GenericDict(self)


# Screw this, if you can figure out how to type hint mapping in dictionary out
# and non-mapping in sequence out in Python, be my guest
def copy_recursive(input, translator: Callable = idem):
    """
    Copies any arbitrarily-deep nested structure of Mappings and/or Sequences.

    :param input: The input nested structure
    :param translator: Before an object is appended, this function will be
        called to process the value.

        By default, :func:`idem` is called.
    :returns: The copy.

        All sequences will become built-in ``list``\\(s) and all mappings will
        become built-in ``dict``\\(s).
    """

    def recursive(input, visit_stack: list, *, sequence_cls=list, mapping_cls=dict):
        if id(input) in visit_stack:
            raise ValueError("Circular reference found in target object")

        visit_stack.append(id(input))

        result: Any = input

        if isinstance(input, Mapping):  # Mappings are Sequences, but not vice versa
            result = mapping_cls()
            for key, value in input.items():
                result[key] = recursive(value, visit_stack)
        elif dataclasses.is_dataclass(input) and not isinstance(input, type):
            replace = {}
            as_dict = dataclasses.asdict(input)
            for key, value in as_dict.items():
                replace[key] = recursive(value, visit_stack)
            result = dataclasses.replace(input, **replace)
        elif not is_string(input) and isinstance(input, Sequence):
            result = sequence_cls()
            for value in input:
                result.append(recursive(value, visit_stack))

        visit_stack.pop()

        result = translator(result)
        return result

    return recursive(input, [])
