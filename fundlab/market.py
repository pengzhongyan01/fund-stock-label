"""行情抓取与股票代码处理。

把 akshare 的调用包一层，原因是原始代码直接依赖新浪接口，有三个坑：

1. 新浪按 symbol（前缀 + 6 位数字）取数，代码格式错了只会返回空表或者 404；
2. 大量抓取会被新浪限流封 IP，需要重试 + 退避；
3. akshare 返回的列名是英文（close / outstanding_share），原始代码用 .iloc[0, 6]
   这种位置下标取"流通股本"，一旦 akshare 调整列顺序就静默取错列 —— 改成按列名取。
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from .config import Config

try:  # pragma: no cover - 取决于运行环境是否装了 akshare
    import akshare as ak
except ImportError:  # pragma: no cover
    ak = None


class MarketDataError(RuntimeError):
    """行情抓取失败。"""


# --------------------------------------------------------------------------
# 股票代码
# --------------------------------------------------------------------------

# 上海 / 深圳 / 北京 的代码前缀规则
_EXCHANGE_RULES = (
    ("60", "sh"),  # 沪市主板
    ("68", "sh"),  # 科创板
    ("00", "sz"),  # 深市主板
    ("30", "sz"),  # 创业板
    ("43", "bj"),  # 北交所
    ("83", "bj"),
    ("87", "bj"),
    ("92", "bj"),
)


def normalize_code(raw: str) -> str | None:
    """把持仓表里的股票代码清洗成 6 位纯数字。

    原始代码用 ``.iloc[j, '持仓股票代码'][1:]`` 砍掉第一个字符，隐含假设是原始值
    形如 ``"1600000"``（带一个多余前缀）。这里改成用正则提取 6 位数字，兼容
    ``"600000"``、``"sh600000"``、``"600000.SH"``、``"1600000"`` 等多种写法。

    另外 A 股代码必须是 6 位，位数不足时左侧补零（``1`` -> ``000001``）。
    """

    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None

    # 去掉交易所后缀，再抽取 6 位数字
    text = text.replace("SH", "").replace("SZ", "").replace("BJ", "")
    text = text.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    digits = "".join(ch for ch in text if ch.isdigit())

    if not digits:
        return None

    if len(digits) >= 6:
        # 取后 6 位：兼容 "1600000" 这种前面多带一位数字的情况
        code = digits[-6:]
    else:
        # 位数不足，左侧补零：pandas 读 CSV 会把 "000001" 变成整数 1
        code = digits.zfill(6)

    return code


def with_exchange(code: str) -> str | None:
    """给 6 位代码加上交易所前缀，akshare 需要 ``sh600000`` 这种格式。"""

    for prefix, exchange in _EXCHANGE_RULES:
        if code.startswith(prefix):
            return f"{exchange}{code}"
    return None


def to_akshare_symbol(raw: str) -> str | None:
    """持仓表里的原始代码 -> akshare symbol。"""

    code = normalize_code(raw)
    if code is None:
        return None
    return with_exchange(code)


# --------------------------------------------------------------------------
# 行情抓取
# --------------------------------------------------------------------------


def fetch_daily(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
    retries: int = 3,
    backoff: float = 2.0,
    pause: float = 0.0,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """抓取单只股票的前复权日线。

    返回列固定为 ``date / open / high / low / close / volume / outstanding_share``，
    按日期升序，日期列转成 ``datetime64[ns]``。
    """

    if ak is None:
        raise MarketDataError(
            "未安装 akshare，请先执行 `pip install -r requirements.txt`"
        )

    cached = _read_cache(cache_dir, symbol, start_date, end_date, adjust)
    if cached is not None:
        return cached

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except Exception as exc:  # 网络/接口/退市股都可能抛错
            last_error = exc
            if attempt < retries:
                time.sleep(backoff * attempt)
                continue
            raise MarketDataError(
                f"抓取 {symbol} 行情失败（重试 {retries} 次）：{exc}"
            ) from exc

        if df is None or df.empty:
            raise MarketDataError(f"{symbol} 在 {start_date}~{end_date} 没有行情数据")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        keep = [c for c in ("date", "open", "high", "low", "close", "volume", "outstanding_share") if c in df.columns]
        df = df[keep]

        _write_cache(cache_dir, symbol, start_date, end_date, adjust, df)
        if pause:
            time.sleep(pause)
        return df

    raise MarketDataError(f"抓取 {symbol} 行情失败：{last_error}")


def _cache_path(
    cache_dir: Path, symbol: str, start_date: str, end_date: str, adjust: str
) -> Path:
    return cache_dir / f"{symbol}_{start_date}_{end_date}_{adjust or 'raw'}.csv"


def _read_cache(
    cache_dir: Path | None,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> pd.DataFrame | None:
    if cache_dir is None:
        return None
    path = _cache_path(cache_dir, symbol, start_date, end_date, adjust)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        return df.sort_values("date").reset_index(drop=True)
    except Exception:
        return None


def _write_cache(
    cache_dir: Path | None,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
    df: pd.DataFrame,
) -> None:
    if cache_dir is None:
        return
    path = _cache_path(cache_dir, symbol, start_date, end_date, adjust)
    try:
        df.to_csv(path, index=False)
    except Exception:
        pass


def label_by_return(
    history: pd.DataFrame,
    current_quarter_end,
    previous_quarter_end,
    lookback: int = 20,
) -> dict:
    """按区间涨跌幅给股票打标签。

    返回 ``{"标签": 1|2|3|4, "当前季度市值": float, "上一季度市值": float}``：

    * 1 优：区间涨幅 >= 20%
    * 2 良：10% ~ 20%
    * 3 中：-15% ~ 10%
    * 4 差：< -15%

    原始代码的问题：

    * ``price1 = stock_data.iloc[0, 4]`` 取的是 **第一行** 的值，不是当前行 ``i``；
    * ``price2 = stock_data.iloc[58, 4]`` 取的是写死的第 58 行；
    * ``stock_data.iloc[i, 7] = 1`` 用位置下标写标签，而该列位置依赖前面
      追加列的顺序，改动列名就会写错列；
    * ``begin_price`` / ``end_price`` 取的是整张表的第 118 / 141 行，跟当前季度无关；
    * 条件写成 ``str(stock_code[2:3]=='6')``，``str(bool)`` 永远是非空字符串，
      恒为真，等于这个判断根本没起作用。
    """

    from .config import quarter_end_of  # 局部导入避免循环

    if history is None or history.empty:
        raise MarketDataError("没有行情数据，无法打标签")

    df = history.copy()
    df["date"] = pd.to_datetime(df["date"])

    cur_end = pd.Timestamp(current_quarter_end)
    prev_end = pd.Timestamp(previous_quarter_end)

    # 当前季度最后一个有行情的交易日
    cur_rows = df[df["date"] <= cur_end]
    if cur_rows.empty:
        raise MarketDataError("当前季度区间内没有交易数据")
    cur_row = cur_rows.iloc[-1]

    # 上一季度最后一个有行情的交易日
    prev_rows = df[df["date"] <= prev_end]
    if prev_rows.empty:
        raise MarketDataError("上一季度区间内没有交易数据")
    prev_row = prev_rows.iloc[-1]

    # 回看 N 个交易日的价格区间
    cur_idx = df.index[df["date"] == cur_row["date"]][0]
    begin_idx = max(0, cur_idx - lookback)
    begin_price = float(df.iloc[begin_idx]["close"])
    end_price = float(cur_row["close"])

    if begin_price <= 0:
        raise MarketDataError("期初价格异常，无法计算涨跌幅")

    ratio = end_price / begin_price

    if ratio >= 1.2:
        label = 1  # 优
    elif ratio >= 1.1:
        label = 2  # 良
    elif ratio >= 0.85:
        label = 3  # 中
    else:
        label = 4  # 差

    outstanding = float(cur_row.get("outstanding_share", 0) or 0)

    return {
        "标签": label,
        "当前季度市值": end_price * outstanding,
        "上一季度市值": float(prev_row["close"]) * outstanding,
        "区间涨跌幅": ratio,
        "期初价格": begin_price,
        "期末价格": end_price,
    }
