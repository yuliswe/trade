#!python3

from datetime import datetime
import click

# time,open,high,low,close


@click.command()
@click.argument("input", type=click.File("r"))
def main(input):
    visited = set()
    deduped = []
    for ln in input.readlines():
        ln: str
        time, *ohlc = ln.strip().split(",")[:5]
        try:
            time, *ohlc = int(time), *ohlc
        except ValueError:
            continue
        if time not in visited:
            visited.add(time)
            deduped.append((time, *ohlc))
    deduped.sort()
    cur_date, cur_file = None, None
    for (time, *ohlc) in deduped:
        dt = datetime.utcfromtimestamp(time)
        if dt.date() != cur_date:
            cur_date = dt.date()
            if cur_file:
                cur_file.close()
            fname = "data/" + cur_date.strftime("%Y-%m-%d.csv")
            cur_file = open(fname, "w")
            print("time,open,high,low,close", file=cur_file)
        ln = ",".join([str(time), *ohlc])
        print(ln, file=cur_file)
    if cur_file:
        cur_file.close()


main()
