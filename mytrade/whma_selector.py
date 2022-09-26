from collections import namedtuple
from dataclasses import dataclass
import math
import random
from re import L
from typing import Iterator, NamedTuple, Tuple
import backtrader as bt
from .big4 import big4
from .weighted_hma import WeightedHMA


def name_whma(params: Tuple[int, int]) -> str:
    h1, h2 = params
    return f"whma_{h1}_{h2}"


def whma_name(whma: WeightedHMA) -> str:
    h1, h2 = whma.get_params()
    return f"whma_{h1}_{h2}"


def default_whma_sequence():
    while True:
        yield 0


@dataclass(frozen=True, kw_only=True, slots=True)
class _ComputeBarResult:
    gross_profit: float
    opentrades: int
    opentrade_price: float
    position_value: float
    buy_price: float
    sell_price: float


class WHMASelector(bt.ind.Indicator):
    params = [
        ("period", 20),
        ("display_plots", "price"),
        ("whmas", []),
        ("whma_sequence", default_whma_sequence()),
        ("greedy", True),
        ("partial_run", None),
    ]
    plotinfo = {"plot": False}
    _lines = lines = (
        "ohlc4",
        "active_whma_index",
        "active_whma_price",
        "gross_profit",
        "position_value",
        "opentrades",
        "opentrade_price",
        "buy",
        "sell",
    )
    _plotlines = plotlines = {
        "ohlc4": {"color": "lightgray"},
        "buy": {"marker": "^", "markersize": 8.0, "color": "lime", "fillstyle": "full"},
        "sell": {"marker": "v", "markersize": 8.0, "color": "red", "fillstyle": "full"},
    }
    display_plots = {
        "price": ("ohlc4", "active_whma_price", "buy", "sell"),
        "sequence": ("active_whma_index",),
        "profit": ("gross_profit",),
        "value": ("position_value",),
    }

    def __init__(self) -> None:
        super().__init__()
        self.l.ohlc4 = (
            self.data.open + self.data.high + self.data.low + self.data.close
        ) / 4
        self.__set_display_plots()
        self.p.whma_sequence = list(self.p.whma_sequence)

    def __set_display_plots(self):
        for p in self._getlines():
            getattr(self.plotlines, p)._plotskip = True
        for p in self.display_plots[self.p.display_plots]:
            getattr(self.plotlines, p)._plotskip = False

    def whmas_dict(self) -> dict[tuple, WeightedHMA]:
        return {x.get_params(): x for x in self.whmas_list()}

    def whmas_list(self) -> list[WeightedHMA]:
        return self.p.whmas

    def get_whma(self, whma_params: tuple) -> WeightedHMA:
        return self.__whmas[whma_params]

    def __period_start(self, start_bar_index: int):
        self.__start_bar_index = start_bar_index

    def __select_active_whma(
        self, end_bar_index: int, gross_profit, opentrades, opentrade_price
    ) -> int:
        if self.p.greedy:
            max_score = -math.inf
            max_index = -1
            edges = list(enumerate(self.whmas_list()))
            random.shuffle(edges)
            for active_whma_idx, active_whma in edges:
                n_gross_profit = gross_profit
                n_opentrades = opentrades
                n_opentrade_price = opentrade_price
                n_position_value = None
                for bar_index in self.__iter_period_bar_index():
                    match self.__compute_bar(
                        bar_index=bar_index,
                        active_whma_index=active_whma_idx,
                        active_whma=active_whma,
                        gross_profit=n_gross_profit,
                        opentrades=n_opentrades,
                        opentrade_price=n_opentrade_price,
                    ):
                        case _ComputeBarResult(
                            gross_profit=n_gross_profit,
                            opentrades=n_opentrades,
                            opentrade_price=n_opentrade_price,
                            position_value=n_position_value,
                        ):
                            pass
                        case x:
                            raise Exception(f"No match {x}")
                n_score = n_gross_profit + n_position_value
                if n_score > max_score:
                    max_score = n_score
                    max_index = active_whma_idx
            return max_index
        else:
            period_index = end_bar_index // self.p.period
            whma_idx = int(self.p.whma_sequence[period_index])
            return whma_idx

    def __period_end(self, end_bar_index: int):
        if self.__start_bar_index == 0:
            gross_profit = 0
            opentrades = 0
            opentrade_price = 0
        else:
            gross_profit = self.l.gross_profit.array[self.__start_bar_index - 1]
            opentrades = self.l.opentrades.array[self.__start_bar_index - 1]
            opentrade_price = self.l.opentrade_price.array[self.__start_bar_index - 1]
        active_whma_idx = self.__select_active_whma(
            end_bar_index, gross_profit, opentrades, opentrade_price
        )
        active_whma = self.p.whmas[active_whma_idx]
        for bar_index in self.__iter_period_bar_index():
            match self.__compute_bar(
                bar_index=bar_index,
                active_whma_index=active_whma_idx,
                active_whma=active_whma,
                gross_profit=gross_profit,
                opentrades=opentrades,
                opentrade_price=opentrade_price,
            ):
                case _ComputeBarResult(
                    gross_profit=gross_profit,
                    opentrades=opentrades,
                    opentrade_price=opentrade_price,
                    position_value=position_value,
                    buy_price=buy_price,
                    sell_price=sell_price,
                ):
                    self.__paint_active_whma_price(bar_index, active_whma)
                    self.__paint_gross_profit(bar_index, gross_profit)
                    self.__paint_active_whma_index(bar_index, active_whma_idx)
                    self.__paint_buy(bar_index, buy_price)
                    self.__paint_sell(bar_index, sell_price)
                    self.__paint_position_value(bar_index, position_value)
                    self.__paint_opentrades(bar_index, opentrades)
                    self.__paint_opentrade_price(bar_index, opentrade_price)
                case x:
                    raise Exception(f"No match {x}")

        # print(self.l.gross_profit.array[end_bar_index], self.l.active_whma_index.array)

    def __compute_bar(
        self,
        *,
        bar_index: int,
        active_whma_index: int,
        active_whma: WeightedHMA,
        gross_profit: float,
        opentrades: int,
        opentrade_price: float,
    ) -> _ComputeBarResult:
        price = self.l.ohlc4.array[bar_index]
        target_opentrades = active_whma.l.opentrades.array[bar_index]
        buy_price, sell_price = math.nan, math.nan
        bar_profit = 0
        if active_whma_index == -1:
            if opentrades > 0:
                bar_profit, opentrades, sell_price = self.__compute_sell(
                    bar_index, opentrades, opentrade_price
                )
        elif target_opentrades > opentrades and opentrades == 0:
            opentrades, opentrade_price, buy_price = self.__compute_buy(
                bar_index, active_whma
            )
        elif target_opentrades < opentrades and opentrades > 0:
            bar_profit, opentrades, sell_price = self.__compute_sell(
                bar_index, opentrades, opentrade_price
            )

        position_value = opentrades * (price - opentrade_price)
        gross_profit += bar_profit
        return _ComputeBarResult(
            gross_profit=gross_profit,
            opentrades=opentrades,
            opentrade_price=opentrade_price,
            position_value=position_value,
            buy_price=buy_price,
            sell_price=sell_price,
        )

    def __iter_period_bar_index(self) -> Iterator[int]:
        bar_index = self.__len__() - 1
        period_index = bar_index // self.p.period
        min_index = period_index * self.p.period
        max_index = min(len(self.array) - 1, (period_index + 1) * self.p.period - 1)
        for i in range(min_index, max_index + 1):
            yield i

    def __paint_gross_profit(self, bar_index: int, profit: int):
        self.l.gross_profit.array[bar_index] = profit

    def __partial_run_stop(self):
        return self.p.partial_run and len(self) > self.p.period * self.p.partial_run

    def next(self):
        if self.__partial_run_stop():
            return
        bar_index = self.__len__() - 1
        if bar_index % self.p.period == 0:
            self.__period_start(bar_index)
        if (
            bar_index % self.p.period == self.p.period - 1
            or bar_index == len(self.data.array) - 1
        ):
            self.__period_end(bar_index)

    def __paint_active_whma_price(self, bar_index: int, active_whma: WeightedHMA):
        self.l.active_whma_price.array[bar_index] = active_whma.active_hma.array[
            bar_index
        ]

    def __paint_position_value(self, bar_index: int, value: float):
        self.l.position_value.array[bar_index] = value

    def __paint_buy(self, bar_index: int, buy_price: float):
        self.l.buy.array[bar_index] = buy_price

    def __paint_sell(self, bar_index: int, sell_price: float):
        self.l.sell.array[bar_index] = sell_price

    def __paint_opentrade_price(self, bar_index: int, opentrade_price: float):
        self.l.opentrade_price.array[bar_index] = opentrade_price

    def __paint_opentrades(self, bar_index: int, opentrades: int):
        self.l.opentrades.array[bar_index] = opentrades

    def __paint_active_whma_index(self, bar_index, active_whma_idx):
        self.l.active_whma_index.array[bar_index] = active_whma_idx

    def __compute_buy(self, bar_index: int, active_whma: WeightedHMA) -> Tuple[int]:
        opentrade_price = buy_price = self.l.ohlc4.array[bar_index]
        opentrades = active_whma.l.opentrades.array[bar_index]
        return opentrades, opentrade_price, buy_price

    def __compute_sell(
        self, bar_index: int, opentrades: int, opentrade_price: float
    ) -> Tuple[float, int, float]:
        sell_price = self.l.ohlc4.array[bar_index]
        profit = (sell_price - opentrade_price) * opentrades
        opentrades = 0
        return profit, opentrades, sell_price

    def get_score(self) -> float:
        if self.p.partial_run:
            bar_index = min(
                self.l.position_value.lencount - 1,
                self.p.partial_run * self.p.period - 1,
            )
        else:
            bar_index = -1
        return (
            self.l.position_value.array[bar_index]
            + self.l.gross_profit.array[bar_index]
        )

    def _plotlabel(self) -> list[str]:
        return [self.p.period, list(self.l.active_whma_index)]
