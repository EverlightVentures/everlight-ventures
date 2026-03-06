from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from execution.coinbase_advanced import CoinbaseAdvanced, OrderResult


@dataclass
class OrderRequest:
    product_id: str
    side: str
    size: int
    leverage: int
    stop_loss: float | None = None
    take_profit: float | None = None
    client_order_id: str = ""


class OrderManager:
    def __init__(self, api: CoinbaseAdvanced, paper: bool = True):
        self.api = api
        self.paper = paper

    def place_entry(self, req: OrderRequest) -> OrderResult:
        # Prefer exchange-native bracket protection when we have a stop/TP.
        if req.stop_loss is not None or req.take_profit is not None:
            return self.api.place_order_with_bracket(
                req.product_id,
                req.side,
                req.size,
                stop_loss=req.stop_loss,
                take_profit=req.take_profit,
                paper=self.paper,
                client_order_id=req.client_order_id,
            )
        return self.api.place_order(req.product_id, req.side, req.size, req.leverage, paper=self.paper, client_order_id=req.client_order_id)
