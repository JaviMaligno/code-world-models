"""Token accounting and USD estimation.

PRICES are real Azure OpenAI "Global Standard" list prices (USD per 1M tokens,
input/output), fetched from the Azure Retail Prices API on 2026-06-24. Re-check
before quoting in the article, as list prices change.
"""
from dataclasses import dataclass, field

from cwm.llm.provider import Usage

# (input, output) USD per 1M tokens — Azure Global Standard, 2026-06-24
PRICES = {
    "large": (2.5, 15.0),    # gpt-5.4
    "mini": (0.75, 4.5),     # gpt-5.4-mini
    "nano": (0.2, 1.25),     # gpt-5.4-nano
}

@dataclass
class CostMeter:
    by_role: dict = field(default_factory=dict)

    def add(self, role: str, usage: Usage) -> None:
        pin, pout = PRICES[role]
        cost = (usage.prompt_tokens / 1e6) * pin + (usage.completion_tokens / 1e6) * pout
        self.by_role[role] = self.by_role.get(role, 0.0) + cost

    def total_usd(self) -> float:
        return sum(self.by_role.values())

def extrapolate(per_game_usd: float, n_games: int) -> float:
    return per_game_usd * n_games
