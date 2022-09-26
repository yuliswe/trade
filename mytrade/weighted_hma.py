from datetime import datetime
import math
from typing import Tuple
import backtrader as bt
from .big4 import big4


class WeightedHMA(bt.Indicator):
    _lines = lines = (
        "hma1",
        "hma2",
        "hma3",
        "active_hma1",
        "active_hma2",
        "active_hma3",
        "w1",
        "w2",
        "w3",
        "speed_hma1",
        "accel_hma1",
        "jerk_hma1",
        "jounce_hma1",
        "speed_hma2",
        "accel_hma2",
        "jerk_hma2",
        "jounce_hma2",
        "speed_hma3",
        "accel_hma3",
        "jerk_hma3",
        "jounce_hma3",
        "buy",
        "sell",
        "gross_profit",
        "ohlc4",
        "tick_profit",
        # "great_trend",
        # "great_trend_2",
        "opentrades",
    )
    params = (
        ("h1", 4),
        ("h2", 8),
        ("h3", 3),
        ("stopprofit", 0.05),
        ("display_plots", "price"),
    )
    _plotlines = plotlines = {
        "great_trend": {"color": "purple"},
        "active_hma1": {"color": "blue"},
        "active_hma2": {"color": "orange"},
        "active_hma3": {"color": "red"},
        "ohlc4": {"color": "lightgray"},
        "buy": {"marker": "^", "markersize": 8.0, "color": "lime", "fillstyle": "full"},
        "sell": {"marker": "v", "markersize": 8.0, "color": "red", "fillstyle": "full"},
        "tick_profit": {"_method": "bar"},
    }
    display_plots = {
        "price": (
            "active_hma1",
            "active_hma2",
            "active_hma3",
            "ohlc4",
            "buy",
            "sell",
            # "great_trend",
            # "great_trend_2",
        ),
        "speed": (
            "speed_hma1",
            "accel_hma1",
            "jerk_hma1",
            "jounce_hma1",
            "speed_hma2",
            "accel_hma2",
            "jerk_hma2",
            "jounce_hma2",
            "speed_hma3",
            "accel_hma3",
            "jerk_hma3",
            "jounce_hma3",
        ),
        "profit": ("gross_profit", "tick_profit"),
    }

    def __init__(self):
        super().__init__()
        self.l.ohlc4 = (
            self.data.open + self.data.high + self.data.low + self.data.close
        ) / 4
        self.l.hma1 = bt.ind.HullMovingAverage(self.ohlc4, period=self.p.h1)
        self.l.hma2 = bt.ind.HullMovingAverage(self.ohlc4, period=self.p.h2)
        self.l.hma3 = bt.ind.HullMovingAverage(self.ohlc4, period=self.p.h3)

        # self.l.great_trend = bt.ind.ExponentialMovingAverage(self.ohlc4, period=20)
        # self.l.great_trend_2 = bt.ind.SMA(self.l.great_trend, period=20)
        # greater_trend = bt.ind.HullMovingAverage(self.ohlc4, period=80)

        self.opentrade_price = 0
        self.active_hma = None
        self.__paint_display_plots()

    def __paint_display_plots(self):
        for p in self._getlines():
            getattr(self.plotlines, p)._plotskip = True
        for p in self.display_plots[self.p.display_plots]:
            getattr(self.plotlines, p)._plotskip = False

    def __select_hma(self):
        profit = (
            self.data.close[0] - self.opentrade_price if self.opentrade_price else 0
        )
        profit_percent = profit / self.p.stopprofit
        if self.l.opentrades[0] == 0:
            return self.hma1
        elif profit_percent < 1 and self.active_hma is not self.hma3:
            return self.hma2
        else:
            return self.hma3

    def log(self):
        print(
            f"{self.__len__()}\t {self.l.opentrades[0]=} {self.opentrade_price=} {self.buy[0]=} {self.sell[0]=} {self.l.gross_profit[0]=}"
        )
        # print(f"{self.l.gross_profit[0]=}")

    def __can_buy(self, hma, ago) -> bool:
        speed, accel, jerk, jounce = big4(hma, ago)
        return speed > 0 and accel > 0

    def __can_sell(self, hma, ago) -> bool:
        speed, accel, jerk, jounce = big4(hma, ago)
        return (
            speed < 0
            or (sum([speed, accel]) < 0)
            or (sum([speed, accel, jerk]) < 0)
            or (sum([speed, accel, jerk, jounce]) < 0)
        )

    def prenext(self):
        super().prenext()
        self.l.gross_profit[0] = 0
        self.l.opentrades[0] = 0

    def __before_next(self):
        self.l.gross_profit[0] = self.l.gross_profit[-1]
        self.l.opentrades[0] = self.l.opentrades[-1]
        self.tick_profit[0] = 0

    def __paint_active_hma(self, active_hma):
        if active_hma is self.hma1:
            self.active_hma1[0] = self.hma1[0]
            # paint over hma1 if hma2 is holding back the next buy
            if self.__can_buy(self.hma1, -1) and self.__can_sell(self.hma2, 0):
                self.active_hma2[-1] = self.hma2[-1]
                self.active_hma2[0] = self.hma2[0]
        elif active_hma is self.hma2:
            self.active_hma2[0] = self.hma2[0]
            if self.__can_sell(self.hma2, -1) and self.__can_buy(self.hma1, 0):
                self.active_hma1[-1] = self.hma1[-1]
                self.active_hma1[0] = self.hma1[0]
        elif active_hma is self.hma3:
            self.active_hma3[0] = self.hma3[0]
            if self.__can_sell(self.hma3, -1) and self.__can_buy(self.hma1, 0):
                self.active_hma1[-1] = self.hma1[-1]
                self.active_hma1[0] = self.hma1[0]

    def __paint_speed(self, active_hma):
        (
            self.speed_hma1[0],
            self.accel_hma1[0],
            self.jerk_hma1[0],
            self.jounce_hma1[0],
        ) = big4(self.hma1, 0)
        (
            self.speed_hma2[0],
            self.accel_hma2[0],
            self.jerk_hma2[0],
            self.jounce_hma2[0],
        ) = big4(self.hma2, 0)
        (
            self.speed_hma3[0],
            self.accel_hma3[0],
            self.jerk_hma3[0],
            self.jounce_hma3[0],
        ) = big4(self.hma3, 0)

    def next(self):
        self.__before_next()
        self.active_hma = self.__select_hma()
        self.__paint_active_hma(self.active_hma)
        self.__paint_speed(self.active_hma)

        time: datetime = self.data.datetime.datetime()

        if time.hour >= 19 and time.minute >= 50:
            self.__sell(comment=f"market closed")
        elif (
            self.l.opentrades[0] == 0
            and self.__can_buy(self.l.hma1, -1)
            and not self.__can_sell(self.l.hma2, 0)
        ):
            self.__buy()
        elif (
            self.l.opentrades[0] > 0
            and self.__can_sell(self.active_hma, -1)
            and not self.__can_buy(self.l.hma1, 0)
        ):
            self.__sell()

        # self.log()

    def __buy(self, comment=""):
        if self.l.opentrades[0] == 0:
            self.l.opentrades[0] = self.__pos_size()
            self.opentrade_price = self.data.close[0]
            self.buy[0] = self.data.close[0]
            # print(f"* buy {self.data.close[0]} # {comment}")

    def __sell(self, comment=""):
        if self.l.opentrades[0] > 0:
            self.tick_profit[0] = (
                self.data.close[0] - self.opentrade_price
            ) * self.__pos_size()
            self.l.gross_profit[0] = self.l.gross_profit[-1] + self.tick_profit[0]
            self.l.opentrades[0] = 0
            self.opentrade_price = 0
            self.sell[0] = self.data.close[0]
            # print(
            #     f"* sold {self.tick_profit[0] :.2f} # {comment} big4(hma1)={big4(self.hma1, 0)} big4(hma2)={big4(self.hma2, 0)} big4(hma3)={big4(self.hma3, 0)}"
            # )

    def __pos_size(self):
        return 300

    def get_params(self) -> tuple[int, int]:
        return self.p.h1, self.p.h2

    # @property
    # def active_hma(self) -> bt.ind.HullMovingAverage:
    #     return self.__active_hma
