from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExitPlan:
    tp1: float
    tp2: float
    tp3: float
    full_close_at_tp1: bool


def tp_prices(
    entry: float,
    leverage: int,
    direction: str,
    tp1_move: float,
    tp2_move: float,
    tp3_move: float,
    full_close_at_tp1: bool = True,
) -> ExitPlan:
    if leverage <= 0:
        leverage = 1
    move1 = tp1_move / leverage
    move2 = tp2_move / leverage
    move3 = tp3_move / leverage
    if direction == "long":
        tp1 = entry * (1 + move1)
        tp2 = entry * (1 + move2)
        tp3 = entry * (1 + move3)
    else:
        tp1 = entry * (1 - move1)
        tp2 = entry * (1 - move2)
        tp3 = entry * (1 - move3)
    return ExitPlan(tp1=tp1, tp2=tp2, tp3=tp3, full_close_at_tp1=full_close_at_tp1)
