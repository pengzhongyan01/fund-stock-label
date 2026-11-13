"""测试用的样例数据生成器。

构造一小份"基金数据分析"目录，覆盖合并 + 打标签两步所需的全部输入文件。
行情用固定随机种子生成，保证测试可重复。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

CURRENT_QUARTER = "2026年第一季度"
PREVIOUS_QUARTER = "2025年第四季度"
CURRENT_YEAR = "2026"
PREVIOUS_YEAR = "2025"
FUND_TYPE = "股票"

_STOCKS = [
    ("贵州茅台", "600519", 1500.0),
    ("宁德时代", "300750", 220.0),
    ("平安银行", "000001", 11.5),
]


def build_sample_data(root: Path, seed: int = 42) -> Path:
    """在 ``root`` 下生成完整的样例数据集，返回 data_root。"""

    rng = np.random.default_rng(seed)
    processed = root / "处理数据"
    cleaned = root / "数据清洗后"
    processed.mkdir(parents=True, exist_ok=True)
    cleaned.mkdir(parents=True, exist_ok=True)

    names = [s[0] for s in _STOCKS]

    # --- 连续二季度各个基金持仓股票持股总市值 ---
    pd.DataFrame(
        {
            "股票名称": names,
            f"{CURRENT_QUARTER}各个基金持仓股票持股总市值": [1.2e10, 8.8e9, 3.1e9],
            f"{PREVIOUS_QUARTER}各个基金持仓股票持股总市值": [1.1e10, 9.5e9, 3.0e9],
        }
    ).to_csv(
        processed / f"连续二季度各个基金持仓股票持股总市值-{CURRENT_QUARTER}与{PREVIOUS_QUARTER}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # --- 连续二季度股票持有的基金持有家数 ---
    pd.DataFrame(
        {
            "股票名称": names,
            f"{CURRENT_QUARTER}基金持有家数": [120, 85, 40],
            f"{PREVIOUS_QUARTER}基金持有家数": [110, 90, 38],
        }
    ).to_csv(
        processed / f"连续二季度股票持有的基金持有家数-{CURRENT_QUARTER}与{PREVIOUS_QUARTER}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # --- 高收益率基金前十大持仓（两个季度各一份）---
    holdings = pd.DataFrame(
        {
            "基金代码": ["000001", "000002", "000003"],
            "持仓股票代码": [code for _, code, _ in _STOCKS],
            "持仓股票名称": names,
        }
    )
    # crossed 配对：当前季度文件用 previous_year，上一季度文件用 current_year
    holdings.to_csv(
        cleaned
        / f"{PREVIOUS_YEAR}年{FUND_TYPE}型基金近一年高收益率基金的前十大持仓-{CURRENT_QUARTER}.csv",
        index=False,
        encoding="utf-8-sig",
    )
    holdings.to_csv(
        cleaned
        / f"{CURRENT_YEAR}年{FUND_TYPE}型基金近一年高收益率基金的前十大持仓-{PREVIOUS_QUARTER}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return root


def make_history(
    symbol: str,
    start: str = "2025-09-01",
    end: str = "2026-03-31",
    base_price: float = 100.0,
    drift: float = 0.0006,
    seed: int = 7,
) -> pd.DataFrame:
    """生成一段确定性的日线数据，用于测试打标签逻辑。"""

    # 不能用内置 hash()：字符串哈希每个进程都带随机盐，会让测试不可重复
    symbol_seed = int(hashlib.md5(symbol.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed + symbol_seed % 1000)
    dates = pd.bdate_range(start=start, end=end)
    n = len(dates)

    shocks = rng.normal(loc=drift, scale=0.015, size=n)
    closes = base_price * np.cumprod(1 + shocks)

    return pd.DataFrame(
        {
            "date": dates,
            "open": closes * 0.995,
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": rng.integers(1_000_000, 10_000_000, size=n),
            "outstanding_share": np.full(n, 1.0e9),
        }
    )
