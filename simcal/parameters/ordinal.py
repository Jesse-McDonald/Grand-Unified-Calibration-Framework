from __future__ import annotations

from typing import Self
from typing import TYPE_CHECKING

from simcal.parameters.ordered import Ordered

if TYPE_CHECKING:
    from simcal.parameters import Value


class Ordinal(Ordered):
    def __init__(self, options):
        super().__init__(0, 1)
        self.options = options

    def constrain(self, new_range_start: float | Value, new_range_end: float | Value) -> Self:
        from simcal.parameters import Value
        if isinstance(new_range_start, Value):
            new_range_start = new_range_start.value
        if isinstance(new_range_end, Value):
            new_range_end = new_range_end.value
        start = self.options.index(new_range_start)
        end = self.options.index(new_range_end)
        ret = Ordinal(self.options[start:end])
        ret.range_start = self.range_start
        ret.range_end = self.range_end
        return ret

    def is_valid_value(self, x: float | Value) -> bool:
        if isinstance(x, Value):
            x = x.value
        return x in self.options

    def from_normalized(self, x: float):
        if self.from_normalize_override:
            return self.from_normalize_override(self, x)
        x_normal = (x - self.range_start) / (self.range_end - self.range_start)
        idx = int(x_normal * len(self.options))
        if idx >= len(self.options):
            idx = len(self.options) - 1
        value = self.options[idx]
        return self.apply_format(value)

    def to_normalized(self, x: any):
        if self.to_normalize_override:
            return self.to_normalize_override(self, x)
        idx = self.options.index(x)
        x_normal = idx / len(self.options)
        return x_normal * (self.range_end - self.range_start) + self.range_start

    def from_index(self,i : int):
        return self.apply_format(self.options[i])