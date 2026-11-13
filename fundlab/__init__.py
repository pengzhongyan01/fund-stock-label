"""融合基金持仓与股票的市值，并进行标签化，为下一步的训练提供数据。"""

from .config import Config
from .pipeline import get_stock_label, merge_position_and_market, run

__all__ = [
    "Config",
    "merge_position_and_market",
    "get_stock_label",
    "run",
]

__version__ = "1.0.0"
