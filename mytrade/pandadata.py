from datetime import datetime, timezone
import backtrader as bt  # type: ignore
import pandas as pd
import pytz


def PandasData(filepath: str) -> bt.feeds.PandasData:
    df = pd.read_csv(
        filepath,
        index_col="time",
        parse_dates=["time"],
        date_parser=lambda x: datetime.fromtimestamp(
            int(x), tz=pytz.UTC
        ),  # convert to US timezone
    )
    # pad time before the trade day starts
    time_interval = df.index[1] - df.index[0]
    insert_rows = []
    N = 25
    for i in range(1, N):
        insert_rows.append([df.index[0] - i * time_interval, *df.iloc[0, :]])
    insert_rows.reverse()
    df = pd.concat(
        [
            pd.DataFrame(
                [x[1:] for x in insert_rows],
                index=[x[0] for x in insert_rows],
                columns=df.columns,
            ),
            df,
        ]
    )
    print(df)
    return bt.feeds.PandasData(dataname=df), df
