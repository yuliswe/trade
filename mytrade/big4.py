from typing import Tuple
import math


def speed(line, ago: int) -> float:
    assert ago <= 0, "-1 is the previous index"
    # a0 is the previous value, a1 is the current value
    match line.get(ago, 2):
        case a0, a1:
            return a1 - a0
        case []:
            return math.nan


def accel(line, ago: int) -> float:
    a0, a1 = speed(line, ago - 2), speed(line, ago)
    return (a1 - a0) / 2


def jerk(line, ago: int) -> float:
    a0, a1 = accel(line, ago - 4), accel(line, ago)
    return (a1 - a0) / 4


def jounce(line, ago: int) -> float:
    a0, a1 = jerk(line, ago - 8), jerk(line, ago)
    return (a1 - a0) / 8


def big4(line, ago: int) -> Tuple[float, float, float, float]:
    scale = 100
    _speed = scale * speed(line, ago)
    _accel = scale * accel(line, ago)
    _jerk = scale * jerk(line, ago)
    _jounce = scale * jounce(line, ago)
    return _speed, _accel, _jerk, _jounce
