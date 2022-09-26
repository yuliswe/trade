from functools import cached_property
from typing import Callable
import backtrader as bt
from .weighted_hma import WeightedHMA
from .strategy import DerStrategy


class WHMAObserver(bt.Observer):
    params = (("get_whma", None), ("display_plots", "price"))
    plotinfo = dict(plot=True, subplot=True)
    lines = WeightedHMA._lines
    plotlines = WeightedHMA._plotlines
    display_plots = WeightedHMA.display_plots

    def __init__(self) -> None:
        super().__init__()
        self.__set_display_plots(self.p.display_plots)

    def __set_display_plots(self, display_plots: str):
        for p in self._getlines():
            getattr(self.plotlines, p)._plotskip = True
        for p in self.display_plots[display_plots]:
            getattr(self.plotlines, p)._plotskip = False

    def _plotlabel(self) -> list[str]:
        """Controls the paranthesis part of the plotname."""
        parent = super()._plotlabel()[1:]  # removes the lambda
        whma = self.__whma._plotlabel()[:-1]  # drops the display_plot name
        return whma + parent

    def next(self):
        bar_index = len(self) - 1
        for lname in self._getlines():
            src = getattr(self.__whma, lname)
            dest = getattr(self.l, lname)
            # It appers that sometimes the internal index of src is not in sync
            # with the observer. Therefore, directly accessing the internal
            # .arrary is safer.
            dest[0] = src.array[bar_index]

    @property
    def __strategy(self) -> DerStrategy:
        return self._owner

    @property
    def __whma(self) -> WeightedHMA:
        return self.p.get_whma(self.__strategy)
