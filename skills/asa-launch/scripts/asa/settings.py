from dataclasses import dataclass, field
from typing import Tuple

@dataclass
class ScoringSettings:
    impressions_threshold: int = 1000
    target_cpa: Tuple[float, float] = (0.1, 0.29)
    weight_impression: float = 0.2
    weight_ttr: float = 0.2
    weight_cpa: float = 0.4
    weight_cr: float = 0.2

@dataclass
class AutoBidSettings:
    score_range: Tuple[float, float] = (0.1, 0.5)
    target_cpa: Tuple[float, float] = (0.1, 0.35)
    bid_range: Tuple[float, float] = (0.01, 1.5)
    impressions_range: Tuple[int, int] = (500, 1000)
    
    # Bid adjustment multipliers
    score_multiplier: float = 0.1
    cpa_multiplier: float = 0.1
    low_impressions_multiplier: float = 1.1

class Settings:
    def __init__(self):
        self.scoring = ScoringSettings()
        self.autobid = AutoBidSettings()
