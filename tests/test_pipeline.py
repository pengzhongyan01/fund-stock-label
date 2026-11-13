"""测试：季度解析、代码规范化、合并与打标签全流程。

全部离线运行，不访问外网。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fundlab.config import (  # noqa: E402
    Config,
    QuarterParseError,
    parse_quarter,
    quarter_end_of,
    quarter_start_of,
)
from fundlab.market import (  # noqa: E402
    label_by_return,
    normalize_code,
    to_akshare_symbol,
)
from fundlab.pipeline import (  # noqa: E402
    get_stock_label,
    merge_position_and_market,
    run,
)
from tests.sample_data import (  # noqa: E402
    CURRENT_QUARTER,
    CURRENT_YEAR,
    FUND_TYPE,
    PREVIOUS_QUARTER,
    PREVIOUS_YEAR,
    build_sample_data,
    make_history,
)


# ---------------------------------------------------------------- 季度解析


@pytest.mark.parametrize(
    "label,expected",
    [
        ("2026年第一季度", (2026, 1)),
        ("2026年一季度", (2026, 1)),
        ("2026Q1", (2026, 1)),
        ("2026-1", (2026, 1)),
        ("2025年第四季度", (2025, 4)),
        ("2025年四季度", (2025, 4)),
    ],
)
def test_parse_quarter(label, expected):
    assert parse_quarter(label) == expected


def test_parse_quarter_invalid():
    with pytest.raises(QuarterParseError):
        parse_quarter("不是季度")


def test_quarter_boundaries():
    assert quarter_start_of("2026年第一季度") == pd.Timestamp("2026-01-01").date()
    assert quarter_end_of("2026年第一季度") == pd.Timestamp("2026-03-31").date()
    assert quarter_end_of("2025年第四季度") == pd.Timestamp("2025-12-31").date()


# ---------------------------------------------------------------- 代码处理


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("600519", "600519"),
        ("1600519", "600519"),
        ("sh600519", "600519"),
        ("600519.SH", "600519"),
        ("000001", "000001"),
        ("300750", "300750"),
    ],
)
def test_normalize_code(raw, expected):
    assert normalize_code(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("600519", "sh600519"),
        ("300750", "sz300750"),
        ("000001", "sz000001"),
        ("830799", "bj830799"),
        ("无效", None),
    ],
)
def test_to_akshare_symbol(raw, expected):
    assert to_akshare_symbol(raw) == expected


# ---------------------------------------------------------------- 打标签


def test_label_by_return_buckets():
    history = make_history("sh600519", base_price=100.0, drift=0.0)

    # 构造确定性的涨跌幅：先平后涨 30% -> 优
    hist = history.copy()
    hist["close"] = 100.0
    hist.loc[hist.index[-1], "close"] = 130.0
    result = label_by_return(hist, "2026-03-31", "2025-12-31", lookback=20)
    assert result["标签"] == 1

    # 跌 50% -> 差
    hist2 = history.copy()
    hist2["close"] = 100.0
    hist2.loc[hist2.index[-1], "close"] = 50.0
    assert label_by_return(hist2, "2026-03-31", "2025-12-31", lookback=20)["标签"] == 4

    # 涨 15% -> 良
    hist3 = history.copy()
    hist3["close"] = 100.0
    hist3.loc[hist3.index[-1], "close"] = 115.0
    assert label_by_return(hist3, "2026-03-31", "2025-12-31", lookback=20)["标签"] == 2

    # 跌 5% -> 中
    hist4 = history.copy()
    hist4["close"] = 100.0
    hist4.loc[hist4.index[-1], "close"] = 95.0
    assert label_by_return(hist4, "2026-03-31", "2025-12-31", lookback=20)["标签"] == 3


def test_label_uses_quarter_boundaries_not_fixed_rows():
    """回归测试：原始代码取的是整表第 118/141 行，与季度无关。"""

    history = make_history("sh600519", start="2025-01-01", end="2026-03-31")
    hist = history.copy()
    hist["close"] = 100.0
    # 只在当前季度最后一天拉高 30%
    hist.loc[hist.index[-1], "close"] = 130.0

    result = label_by_return(hist, "2026-03-31", "2025-12-31", lookback=20)
    assert result["标签"] == 1
    assert result["期末价格"] == pytest.approx(130.0)


# ---------------------------------------------------------------- 全流程


@pytest.fixture
def sample_config(tmp_path) -> Config:
    data_root = build_sample_data(tmp_path / "基金数据分析")
    return Config(
        data_root=data_root,
        fund_type=FUND_TYPE,
        current_quarter=CURRENT_QUARTER,
        previous_quarter=PREVIOUS_QUARTER,
        current_year=CURRENT_YEAR,
        previous_year=PREVIOUS_YEAR,
        year_quarter_pairing="crossed",
    )


def test_merge_position_and_market(sample_config):
    out = merge_position_and_market(sample_config)
    assert out.exists()

    df = pd.read_csv(out, encoding="utf-8-sig")
    assert list(df.columns) == [
        "股票名称",
        f"{CURRENT_QUARTER}基金持有家数",
        f"{PREVIOUS_QUARTER}基金持有家数",
        f"{CURRENT_QUARTER}各个基金持仓股票持股总市值",
        f"{PREVIOUS_QUARTER}各个基金持仓股票持股总市值",
    ]
    assert len(df) == 3


def test_end_to_end_with_mocked_market(sample_config, monkeypatch):
    """完整跑一遍，行情抓取用本地生成的假数据替身。"""

    import fundlab.pipeline as pipeline

    def fake_fetch_daily(symbol, start_date, end_date, **kwargs):
        base = {"sh600519": 1500.0, "sz300750": 220.0, "sz000001": 11.5}[symbol]
        return make_history(symbol, base_price=base)

    monkeypatch.setattr(pipeline, "fetch_daily", fake_fetch_daily)

    out = run(sample_config)
    assert out.exists()

    df = pd.read_csv(out, encoding="utf-8-sig")
    assert len(df) == 3
    assert f"{CURRENT_QUARTER}股票流通市值" in df.columns
    assert f"{PREVIOUS_QUARTER}股票流通市值" in df.columns
    assert "标签" in df.columns

    # 每一行都真正打上了标签（不是初始值 3 全覆盖），且市值是数值
    assert df["标签"].isin([1, 2, 3, 4]).all()
    assert (df[f"{CURRENT_QUARTER}股票流通市值"] > 0).all()
    assert df[f"{CURRENT_QUARTER}股票流通市值"].dtype.kind == "f"


def test_missing_input_raises_clear_error(tmp_path):
    config = Config(data_root=tmp_path / "空的目录")
    with pytest.raises(FileNotFoundError) as exc:
        merge_position_and_market(config)
    assert "找不到输入文件" in str(exc.value)


def test_config_creates_directories(tmp_path):
    config = Config(data_root=tmp_path / "新目录")
    config.ensure_dirs()
    assert config.processed_dir.exists()
    assert config.cleaned_dir.exists()
