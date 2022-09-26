#!python3
from collections import deque
import datetime
import math  # For datetime objects
import os.path
import random  # To manage paths
import sys
from typing import Iterable  # To find out the script name (in argv[0])
from mytrade.pandadata import PandasData
from mytrade.strategy import DerStrategy
from mytrade.plotting import Bokeh
import click
import warnings

# Import the backtrader platform
import backtrader as bt
from mytrade.whma_observer import WHMAObserver
from mytrade.whma_selector import WHMASelector
from mytrade.selector_observer import SelectorObserver
from pandas.errors import PerformanceWarning
from pathos.multiprocessing import ProcessPool

warnings.simplefilter("ignore", PerformanceWarning)


@click.command()
@click.option("--plot", is_flag=True)
@click.option("-s", "--search-best-seq", is_flag=True)
def main(plot=False, search_best_seq=False):
    file = "./data/2022-09-09.csv"
    data, df = PandasData(file)
    data_len = df.shape[0]
    R = range(3, 40, 8)
    whma_params = [(h1, h2) for h1 in R for h2 in R]
    whmas_count = len(whma_params)
    period = 2
    num_periods = math.ceil(data_len / period)

    def eval_profit(path) -> float:
        cerebro, strat = run_once(
            data=data,
            name=file,
            plot=False,
            whma_sequence=path,
            partial_run=len(path),
            period=period,
            greedy=False,
            whma_params=whma_params,
        )
        return (strat.selector.get_score(), path)

    ### BFS with pruning
    edges = list(range(whmas_count))
    queue = deque([(0, [e]) for e in edges])
    levels = 1
    with ProcessPool() as pool:
        while queue:
            next_level = []
            while queue:
                pathprofit, path = queue.popleft()
                print(pathprofit, path)
                next_level.extend(pool.uimap(eval_profit, [path + [e] for e in edges]))
            random.shuffle(next_level)
            queue.extend(next_level)

            if levels % 3 == 0:
                # pruning every N levels
                queue = list(queue)
                queue.sort(reverse=True)
                scores = [s for s, _ in queue]
                best_score = scores[0]
                queue = [(s, p) for (s, p) in queue if s == best_score]
                random.shuffle(queue)
                queue = deque(queue)

            levels += 1
            if levels > num_periods:
                break

    best_profit, best_path = sorted(queue)[-1]
    print(best_profit, best_path)
    cerebro, derstrat = run_once(
        data=data,
        name=file,
        plot=plot,
        whma_sequence=best_path,
        whma_params=whma_params,
        partial_run=False,
        period=period,
        greedy=False,
    )

    # profit_sofar = 0
    # path_sofar = []
    # for d in range(1, num_periods + 1):
    #     best_edge = -1
    #     best_edge_profit = 0

    #     # with ProcessPool() as pool:

    #     #     def args():
    #     #         for edge in range(whmas_count):
    #     #             yield edge, data, file, path_sofar, d, period

    #     #     def __process_edge_helper(args):
    #     #         edge, data, file, path_sofar, depth, period = args
    #     #         return edge, *run_once(
    #     #             data=data,
    #     #             name=file,
    #     #             plot=False,
    #     #             whma_sequence=path_sofar + [edge],
    #     #             partial_run=depth,
    #     #             period=period,
    #     #         )

    #     #     for edge, cereboro, derstrat in pool.uimap(__process_edge_helper, args()):
    #     #         if (profit := derstrat.selector.get_score()) > best_edge_profit:
    #     #             best_edge = edge
    #     #             best_edge_profit = profit

    #     for edge in range(whmas_count):
    #         cerebro, derstrat = run_once(
    #             data=data,
    #             name=file,
    #             plot=False,
    #             whma_sequence=path_sofar + [edge],
    #             partial_run=d,
    #             period=period,
    #             greedy=False,
    #         )
    #         if (profit := derstrat.selector.get_score()) > best_edge_profit:
    #             best_edge = edge
    #             best_edge_profit = profit

    #     profit_sofar += best_edge_profit
    #     path_sofar.append(best_edge)
    #     print(profit_sofar, path_sofar)

    # print(profit_sofar, path_sofar)

    # cerebro, derstrat = run_once(
    #     data=data,
    #     name=file,
    #     plot=plot,
    #     whma_sequence=path_sofar,
    #     partial_run=d,
    #     period=period,
    # )

    # cerebro, derstrat = run_once(
    #     data=data,
    #     name=file,
    #     plot=plot,
    #     greedy=True,
    #     period=period,
    #     whma_sequence=[],
    #     partial_run=None,
    #     whma_params=whma_params,
    # )

    # return profit_sofar, path_sofar


def run_once(
    data,
    *,
    name,
    plot,
    whma_sequence,
    period,
    partial_run,
    greedy,
    whma_params,
):
    # Create a cerebro entity
    cerebro = bt.Cerebro(stdstats=False)

    cerebro.addobserver(
        SelectorObserver,
        get_selector=lambda strat: strat.selector,
        display_plots="price",
    )

    cerebro.addobserver(
        SelectorObserver,
        get_selector=lambda strat: strat.selector,
        display_plots="sequence",
    )

    cerebro.addobserver(
        SelectorObserver,
        get_selector=lambda strat: strat.selector,
        display_plots="value",
    )

    cerebro.addobserver(
        SelectorObserver,
        get_selector=lambda strat: strat.selector,
        display_plots="profit",
    )
    # for i in range(len(DerStrategy.whma_params)):
    #     # cerebro.addobserver(
    #     #     SelectorObserver,
    #     #     get_selector=lambda strat, p=p: strat.whma_selector,
    #     #     display_plots="profit",
    #     # )
    #     cerebro.addobserver(
    #         WHMAObserver,
    #         get_whma=lambda strat: strat.whmas[i],
    #         display_plots="price",
    #     )
    #     cerebro.addobserver(
    #         WHMAObserver,
    #         get_whma=lambda strat: strat.whmas[i],
    #         display_plots="speed",
    #     )
    #     cerebro.addobserver(
    #         WHMAObserver,
    #         get_whma=lambda strat: strat.whmas[i],
    #         display_plots="profit",
    #     )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data, name=name)

    cerebro.addstrategy(
        DerStrategy,
        whma_sequence=whma_sequence,
        partial_run=partial_run,
        period=period,
        greedy=greedy,
        whma_params=whma_params,
    )

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Run over everything
    [derstrat] = cerebro.run()

    # Plot the result
    if plot:
        cerebro.plot(Bokeh())

    return cerebro, derstrat


if __name__ == "__main__":
    main()
