from strategies.mean_reversion.generate_signals import generate_mean_reversion_signals
from strategies.momentum.generate_signals import generate_momentum_signals
from strategies.defensive.generate_signals import generate_defensive_signals
from strategies.block_all.generate_signals import generate_block_all_signals

STRATEGY_FUNCTIONS = {
    "mean_reversion": generate_mean_reversion_signals,
    "momentum": generate_momentum_signals,
    "defensive": generate_defensive_signals,
    "block_all": generate_block_all_signals,
    # Expansion: "pead", "sector_rotation", etc.
}
