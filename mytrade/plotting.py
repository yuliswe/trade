import backtrader_plotting as bp
from backtrader_plotting.schemes import Tradimo


def Bokeh() -> bp.Bokeh:
    return bp.Bokeh(style="line", scheme=Tradimo(), filename="./plot.html")
