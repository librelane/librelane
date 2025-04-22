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
from typing import Iterable, Iterator, Type, TypeVar

VT = TypeVar("VT")


class RingBuffer(Iterable[VT]):
    """
    A generic ring (circular) buffer that automatically pops the element at the
    head when full, and emplaces a new element in its place.
    """

    def __init__(
        self,
        t: Type[VT],
        max: int,
    ) -> None:
        super().__init__()
        self._store = [t()] * max
        self._max = max
        self._head = 0
        self._tail = 0
        self._len = 0

    def pop(self) -> VT:
        if self._len == 0:
            raise IndexError("pop from empty ring buffer")
        element = self[0]
        self._head = (self._head + 1) % self._max
        self._len -= 1
        return element

    def push(self, element: VT):
        if self._len == self._max:
            self.pop()
        self._store[self._tail] = element
        self._tail = (self._tail + 1) % self._max
        self._len += 1

    def __getitem__(self, idx: int, /) -> VT:
        if idx + 1 > self._len:
            raise IndexError(f"{idx} is out of range")
        i = (self._head + idx) % self._max
        return self._store[i]

    def __len__(self) -> int:
        return self._len

    def __iter__(self) -> Iterator[VT]:
        for i in range(0, self._len):
            yield self[i]
