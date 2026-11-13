"""融合基金持仓与股票市值，并进行标签化。

对应作业要求的两步：

1. ``merge_position_and_market`` —— 把"连续二季度基金持有家数"和
   "连续二季度各基金持仓股票持股总市值"按股票名称合并成一张表；
2. ``get_stock_label`` —— 抓取个股行情，算出各季度流通市值并打标签。

原始代码里被修掉的问题（详见 ``docs/修复说明.md``）：

* 模块级直接调用未定义变量（``position_area`` 等），import 即崩；
* ``get_stock_label`` 里的 ``current_quarter`` / ``previous_quarter`` /
  ``previous_year`` / ``current_year`` / ``fund_type`` 全是未定义名字；
* 持仓文件名的**年份和季度交叉配对**（当前季度用 previous_year、
  上一季度用 current_year），和合并步骤的命名规则对不上；
* ``price1 = stock_data.iloc[0, 4]`` 取第一行而不是当前行 ``i``；
* ``price2 = stock_data.iloc[58, 4]`` 取写死的第 58 行；
* ``stock_data.iloc[i, 7] = 1`` 用位置下标写标签，列顺序一变就写错列；
* ``begin_price`` / ``end_price`` 取整表第 118 / 141 行，与季度无关；
* ``str(stock_code[2:3]=='6')`` —— ``str(bool)`` 恒为非空字符串，条件形同虚设；
* ``except`` 之后继续往下走，``history_data`` 未定义 -> NameError；
* ``with open(...)`` 块外又调用 ``f.close()``；
* 目录不存在时直接崩，没有自动创建。
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from .config import Config
from .market import (
    MarketDataError,
    fetch_daily,
    label_by_return,
    to_akshare_symbol,
)

logger = logging.getLogger(__name__)

# 合并步骤写出的表头
MERGE_HEADER_FACTORY = (
    "股票名称",
    "{current}基金持有家数",
    "{previous}基金持有家数",
    "{current}各个基金持仓股票持股总市值",
    "{previous}各个基金持仓股票持股总市值",
)


def _read_csv(path: Path, dtype: str | dict | None = None) -> pd.DataFrame:
    """读 CSV，统一按 utf-8-sig 解析（Excel 导出的中文 CSV 常见）。

    ``dtype="str"`` 用于持仓明细：pandas 默认会把 ``000001`` 解析成整数 ``1``，
    前导零丢失后股票代码就错了。
    """

    if not path.exists():
        raise FileNotFoundError(
            f"找不到输入文件：{path}\n"
            f"请确认 data_root / 季度 / 基金类型等参数是否正确。"
        )
    return pd.read_csv(path, encoding="utf-8-sig", dtype=dtype)


def merge_position_and_market(config: Config) -> Path:
    """合并"连续二季度基金持有家数"与"连续二季度持股总市值"。

    输出 ``处理数据/股票对应的基金持有家数和总市值.csv``。
    """

    config.ensure_dirs()

    market_value = _read_csv(config.market_value_file())
    position_number = _read_csv(config.position_number_file())

    if market_value.empty or position_number.empty:
        raise ValueError("合并用的两张输入表不能为空")

    if market_value.shape[1] < 3 or position_number.shape[1] < 3:
        raise ValueError(
            "合并用的输入表至少要有 3 列（股票名称、当前季度、上一季度），"
            f"实际：市值表 {list(market_value.columns)}，家数表 {list(position_number.columns)}"
        )

    # 两张表都是：第一列股票名称，第二列当前季度，第三列上一季度。
    # 先把两张表的列名改成规范名再合并，避免两份 CSV 的表头写法不一致（比如多空格）导致 merge 失败。
    key = "股票名称"
    number = position_number.iloc[:, :3].copy()
    number.columns = [key, "__cur_number__", "__prev_number__"]

    value = market_value.iloc[:, :3].copy()
    value.columns = [key, "__cur_value__", "__prev_value__"]

    merged = pd.merge(number, value, on=key, how="inner").reset_index(drop=True)

    header = [
        "股票名称",
        f"{config.current_quarter}基金持有家数",
        f"{config.previous_quarter}基金持有家数",
        f"{config.current_quarter}各个基金持仓股票持股总市值",
        f"{config.previous_quarter}各个基金持仓股票持股总市值",
    ]

    # 按表头顺序重排
    out = pd.DataFrame()
    out["股票名称"] = merged[key]
    out[header[1]] = merged["__cur_number__"]
    out[header[2]] = merged["__prev_number__"]
    out[header[3]] = merged["__cur_value__"]
    out[header[4]] = merged["__prev_value__"]

    config.merged_file().parent.mkdir(parents=True, exist_ok=True)
    with open(config.merged_file(), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in out.itertuples(index=False, name=None):
            writer.writerow(dict(zip(header, row)))

    logger.info("合并完成：%s，共 %d 行", config.merged_file(), len(out))
    return config.merged_file()


def _build_code_lookup(config: Config) -> dict[str, str]:
    """从两个季度的持仓明细里建立 ``股票名称 -> akshare symbol`` 映射。"""

    lookup: dict[str, str] = {}
    current_file, previous_file = config.holdings_files()

    for path in (current_file, previous_file):
        # 用 str 读，保留 "000001" 的前导零
        df = _read_csv(path, dtype=str)
        if df.empty:
            continue

        if "持仓股票代码" not in df.columns:
            raise ValueError(
                f"{path} 里找不到 '持仓股票代码' 列，实际列名：{list(df.columns)}"
            )

        # 股票名称列：优先按列名找，找不到就用第 5 列（原始代码用的 iloc[j, 4]）
        name_col = None
        for candidate in ("持仓股票名称", "股票名称"):
            if candidate in df.columns:
                name_col = candidate
                break
        if name_col is None:
            if df.shape[1] <= 4:
                raise ValueError(
                    f"{path} 里找不到股票名称列（持仓股票名称/股票名称），实际列名：{list(df.columns)}"
                )
            name_col = df.columns[4]

        for name, raw_code in zip(df[name_col], df["持仓股票代码"]):
            symbol = to_akshare_symbol(raw_code)
            if symbol and str(name) not in lookup:
                lookup[str(name)] = symbol

    logger.info("从持仓明细中解析出 %d 个股票代码", len(lookup))
    return lookup


def get_stock_label(config: Config) -> Path:
    """抓取行情、计算各季度流通市值并打标签。

    输出 ``处理数据/股票对应的基金持有家数和总市值和股票市值及标签.csv``。
    """

    config.ensure_dirs()

    if not config.merged_file().exists():
        raise FileNotFoundError(
            f"找不到合并结果：{config.merged_file()}，请先运行 merge_position_and_market"
        )

    stock_data = pd.read_csv(config.merged_file(), encoding="utf-8-sig")
    stock_data = stock_data.dropna(axis=0).reset_index(drop=True)

    cur_mkt_col = f"{config.current_quarter}股票流通市值"
    prev_mkt_col = f"{config.previous_quarter}股票流通市值"

    stock_data[cur_mkt_col] = 0.0
    stock_data[prev_mkt_col] = 0.0
    stock_data["标签"] = 3

    name_col = stock_data.columns[0]
    lookup = _build_code_lookup(config)

    failed: list[str] = []
    total = len(stock_data) if config.limit is None else min(config.limit, len(stock_data))

    for i in range(total):
        stock_name = str(stock_data.iloc[i][name_col])
        symbol = lookup.get(stock_name)

        if symbol is None:
            failed.append(f"{stock_name}(未匹配到代码)")
            continue

        try:
            history = fetch_daily(
                symbol=symbol,
                start_date=config.history_start,
                end_date=config.history_end,
                adjust=config.adjust,
                retries=config.retries,
                backoff=config.backoff,
                pause=config.pause,
                cache_dir=config.cache_dir,
            )
            result = label_by_return(
                history,
                current_quarter_end=config.current_quarter_end,
                previous_quarter_end=config.previous_quarter_end,
                lookback=config.label_lookback,
            )
        except MarketDataError as exc:
            logger.warning("%s 抓取/计算失败：%s", symbol, exc)
            failed.append(f"{symbol}(抓取失败)")
            continue
        except Exception as exc:  # 单只股票出错不能中断整批
            logger.warning("%s 处理出现未预期错误：%s", symbol, exc)
            failed.append(f"{symbol}({type(exc).__name__})")
            continue

        # 用 loc + 列名写值，不再依赖列的位置
        stock_data.loc[i, cur_mkt_col] = result["当前季度市值"]
        stock_data.loc[i, prev_mkt_col] = result["上一季度市值"]
        stock_data.loc[i, "标签"] = result["标签"]

    config.labeled_file().parent.mkdir(parents=True, exist_ok=True)
    stock_data.to_csv(config.labeled_file(), encoding="utf-8-sig", index=False)

    logger.info(
        "标注完成：%s，共 %d 行，失败 %d 只",
        config.labeled_file(),
        len(stock_data),
        len(failed),
    )
    if failed:
        logger.info("失败清单（前 20 条）：%s", "，".join(failed[:20]))

    return config.labeled_file()


def run(config: Config) -> Path:
    """完整跑一遍：合并 -> 打标签。"""

    merge_position_and_market(config)
    return get_stock_label(config)
