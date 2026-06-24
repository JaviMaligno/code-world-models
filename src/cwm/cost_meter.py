"""Token accounting and USD estimation.

PRICES are PLACEHOLDERS (USD per 1M tokens, input/output). Replace with real
Azure GPT-5.4 pricing before quoting any figure in the article.
"""
from dataclasses import dataclass, field

PRICES = {
    "large": (5.0, 25.0),   # TODO: real gpt-5.4 pricing
    "mini": (1.0, 5.0),     # TODO: real gpt-5.4-mini pricing
    "nano": (0.5, 2.0),     # TODO: real gpt-5.4-nano pricing
}

@dataclass
class CostMeter:
    by_role: dict = field(default_factory=dict)

    def add(self, role: str, usage) -> None:
        pin, pout = PRICES[role]
        cost = (usage.prompt_tokens / 1e6) * pin + (usage.completion_tokens / 1e6) * pout
        self.by_role[role] = self.by_role.get(role, 0.0) + cost

    def total_usd(self) -> float:
        return sum(self.by_role.values())

def extrapolate(per_game_usd: float, n_games: int) -> float:
    return per_game_usd * n_games
