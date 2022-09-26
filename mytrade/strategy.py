from datetime import datetime
import math
from typing import Iterable, Tuple
import backtrader as bt
from .weighted_hma import WeightedHMA
from .whma_selector import WHMASelector


class DerStrategy(bt.Strategy):
    params = [
        ("whma_sequence", []),
        ("period", 20),
        ("partial_run", None),
        ("greedy", False),
        ("whma_params", []),
    ]
    # def log(self, txt, dt=None):
    #     """Logging function for this strategy"""
    #     dt = dt or self.datas[0].datetime.date(0)
    #     print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # https://github.com/verybadsoldier/backtrader_plotting/wiki
        self.whmas = []
        for h1, h2 in self.p.whma_params:
            self.whmas.append(WeightedHMA(plot=False, h1=h1, h2=h2))

        # Additional parameters of backtrader_plotting are not recognized by
        # backtrader so they cannot be set manually.
        # self.hma.plotinfo.plotid = "HMA"
        # self.hma.plotlines.hma.color = "blue"

        def generate_paths(whmas_count, periods_count) -> Iterable[Iterable[int]]:
            if periods_count == 0:
                yield []
                return
            for i in range(whmas_count):
                for path in generate_paths(whmas_count, periods_count - 1):
                    yield [i] + path

        self.selector = WHMASelector(
            period=self.p.period,
            display_plots="price",
            whmas=self.whmas,
            whma_sequence=self.p.whma_sequence,
            partial_run=self.p.partial_run,
            greedy=self.p.greedy,
        )

        # WHMASelector(subplot=True, display_plots="speed")
        # WHMASelector(subplot=True, display_plots="profit")

        # self.demo_whma = WeightedHMA(subplot=True, h1=10, h2=10, display_plots="price")
        # WeightedHMA(subplot=True, h1=11, h2=3, display_plots="speed")
        # WeightedHMA(subplot=True, h1=11, h2=3, display_plots="profit")

        # WeightedHMA(subplot=True, h1=4, h2=8, display_plots="main")
        # WeightedHMA(subplot=True, h1=4, h2=8, display_plots="profit")

        # WeightedHMA(subplot=True, h1=8, h2=8, display_plots="main")
        # WeightedHMA(subplot=True, h1=8, h2=8, display_plots="profit")

        # WeightedHMA(subplot=True, h1=8, h2=16, display_plots="main")
        # WeightedHMA(subplot=True, h1=8, h2=16, display_plots="profit")

        # WeightedHMA(subplot=True, h1=8, h2=32, display_plots="main")
        # WeightedHMA(subplot=True, h1=8, h2=32, display_plots="profit")

        # WeightedHMA(subplot=True, h1=16, h2=32, display_plots="main")
        # WeightedHMA(subplot=True, h1=16, h2=32, display_plots="profit")

        # WeightedHMA(subplot=True, h1=32, h2=32, display_plots="main")
        # WeightedHMA(subplot=True, h1=32, h2=32, display_plots="profit")

        self.__curr_gear = self.__select_gear(self.__init_state())

    def next(self):

        # Simply log the closing price of the series from the reference
        # self.log("Close, %.2f" % self.dataclose[0])
        state = self.__curr_state()
        next_gear = self.__select_gear(state)
        if next_gear != self.__curr_gear:
            self.__queue_gear(next_gear)

        if self.__should_buy():
            self.buy()
        elif self.__should_sell():
            self.sell()

    def __queue_gear(self, index: int):
        pass

    def __switch_gear(self, index: int):
        pass

    def __select_gear(self, curr_state) -> int:
        return 0

    def __get_whmas(self) -> list[WeightedHMA]:
        pass

    def __curr_state(self) -> list:
        pass

    def __init_state(self) -> tuple:
        pass

    def evalutate_score(self) -> float:
        pass

    def __should_buy(self) -> bool:
        return False

    def __should_sell(self) -> bool:
        return False
