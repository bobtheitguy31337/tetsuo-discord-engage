from dataclasses import dataclass
from datetime import datetime

@dataclass
class Trade:
    tx_hash: str
    kind: str
    usd_value: float
    price_usd: float
    amount_tokens: float
    timestamp: datetime