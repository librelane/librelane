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
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from math import inf
from typing import Any, ClassVar

from ..types import Number, is_number, is_real_number

MetricAggregator = tuple[Number, Callable[[Iterable[Number]], Number]]

sum_aggregator: MetricAggregator = (0, sum)
min_aggregator: MetricAggregator = (inf, min)
max_aggregator: MetricAggregator = (-inf, max)


@dataclass
class MetricComparisonResult:
    """
    :param metric_name: The name of the metric that has been compared
    :param gold: The "gold" value being compared against
    :param new: The new value being evaluated
    :param delta: ``None`` if and only if ``before`` - ``after`` is an invalid number.
        Evaluates to ``after - before``\\.
    :param delta_pct: ``None`` if ``delta`` is None or before is zero.
        Otherwise, evaluates to ``delta / before * 100``\\.
    :param better: Whether the change in the value is considered a good thing or
        not. ``None`` if ``delta`` is None or has no value set for
        ``Metric.higher_is_better``\\.
    :param critical: Whether this change of value very likely results in a dead
        chip, i.e., an increase in DRC values, or an inexplicable change in
        the number of I/O pins.

    """

    metric_name: str
    gold: Any
    new: Any
    delta: Number | None
    delta_pct: Number | None
    better: bool | None
    critical: bool
    significant_figures: int | None

    def is_changed(self) -> bool:
        return (self.delta is not None and self.delta != 0) or self.gold != self.new

    def format_values(self) -> tuple[str, str, str]:
        before_str = str(self.gold)
        if isinstance(self.gold, (float, Decimal)):
            before_str = str(f"{self.gold:.{self.significant_figures}f}")

        after_str = str(self.new)
        if isinstance(self.new, (float, Decimal)):
            after_str = str(f"{self.new:.{self.significant_figures}f}")

        delta_str = "N/A"
        if self.delta is not None:
            delta_str = str(round(self.delta, 6))
            if isinstance(self.delta, (float, Decimal)):
                delta_str = str(f"{self.delta:.{self.significant_figures}f}")
            if self.delta_pct is not None:
                delta_pct_str = str(f"{self.delta_pct:.{self.significant_figures}f}")
                if self.delta_pct > 0:
                    delta_pct_str = f"+{delta_pct_str}"
                delta_str = f"{delta_str} ({delta_pct_str}%)"

        return before_str, after_str, delta_str


@dataclass
class Metric:
    """
    An object storing data about a metric as defined in METRICS2.1.

    :param name: The string name of the metric.
    :param aggregator: A tuple of:
        - A starting value for an accumulator
        - A reduction function

        The aim is the ability to aggregate values from various sub-metrics,
        i.e., for the metric ``timing__hold_vio__count``, the sub-metrics:

        - ``timing__hold_vio__count__corner:A``
        - ``timing__hold_vio__count__corner:B``

        Would be summed up to generate the value for ``timing__hold_vio__count``.
    :param higher_is_better: At a high level, whether a higher numeric value for
        this metric is considered "good" (such as: better utilization) or "bad"
        (such as: more antenna violations.)
    :param critical: A critical metric is always watched for any change.

    """

    name: str
    aggregator: MetricAggregator | None = None
    higher_is_better: bool | None = None
    dont_aggregate: Iterable[str] | None = None
    critical: bool = False

    by_name: ClassVar[dict[str, "Metric"]] = {}

    def __post_init__(self):
        Metric.by_name[self.name] = self

    def modified_name(self, modifiers: Mapping[str, str]) -> str:
        """
        :param modifiers: Modifiers of a metric (i.e. the elements postfixed to the metric in the format {key}:{value})
        :returns: The name with the modifiers added
        """
        return "__".join([self.name] + [f"{k}:{v}" for k, v in modifiers.items()])

    def compare(
        self,
        gold: Any,
        new: Any,
        significant_figures: int,
        modifiers: Mapping[str, str] | None = None,
    ) -> MetricComparisonResult:
        """
        :param gold: The "gold-standard" value for this metric to compare against
        :param new: The new value for this metric being evaluated
        :param modifier: The modifiers that were parsed from the metric name
            (if applicable)- used to set the ``metric_name`` property of
            :class:`MetricComparisonResult`.
        :returns: The result of comparing two values for this metric.
        """
        is_better = None
        is_critical = self.critical and (gold != new)
        delta = None
        delta_pct = None

        if modifiers is None:
            modifiers = {}

        if is_real_number(gold) and is_real_number(new):
            if isinstance(gold, float) or isinstance(new, float):
                gold = Decimal(gold)
                new = Decimal(new)
            delta = new - gold

            if gold == 0:
                if new == 0:
                    delta_pct = Decimal(0)
            else:
                delta_pct = Decimal((delta / gold) * 100)
                if delta_pct == 0:
                    delta_pct = Decimal(0)  # Fix negative zero

            if self.higher_is_better is not None:
                if self.higher_is_better:
                    is_better = delta >= 0
                else:
                    is_better = delta <= 0
        elif self.higher_is_better is not None:
            if not is_number(gold):
                raise TypeError(
                    f"'{gold}' is not a number for metric {self.name} with non-None 'higher_is_better' field"
                )
            if not is_number(new):
                raise TypeError(
                    f"'{new}' is not a number  for metric {self.name} with non-None 'higher_is_better' field"
                )

        return MetricComparisonResult(
            self.modified_name(modifiers),
            gold,
            new,
            delta,
            delta_pct,
            is_better,
            is_critical,
            significant_figures,
        )
