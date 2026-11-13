"""路径与参数配置。

所有跟"课程作业目录结构"有关的路径都集中在这里，方便在 GitHub 上换目录、
换季度、换基金类型，而不用改业务代码。
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

# --------------------------------------------------------------------------
# 季度标签解析
# --------------------------------------------------------------------------

_CN_QUARTER = {"一": 1, "二": 2, "三": 3, "四": 4}

_QUARTER_PATTERNS = (
    # 2026年第一季度 / 2026年一季度 / 2026 年第 1 季度
    re.compile(r"^(?P<year>\d{4})\s*年\s*第?\s*(?P<q>[1-4一二三四])\s*季度$"),
    # 2026Q1 / 2026-Q1 / 2026 q1
    re.compile(r"^(?P<year>\d{4})\s*[-/]?\s*[Qq](?P<q>[1-4])$"),
    # 2026-1 / 2026年1季度 / 2026年1
    re.compile(r"^(?P<year>\d{4})\s*年?\s*[-/]?\s*(?P<q>[1-4])\s*(?:季度?)?$"),
    # 2026年第一季度这种带"第一"的写法单独处理（上面的正则已覆盖，这里兜底）
    re.compile(r"^(?P<year>\d{4}).*?(?P<q>[1-4一二三四])\s*季度$"),
)


class QuarterParseError(ValueError):
    """季度标签无法解析时抛出。"""


def parse_quarter(label: str) -> tuple[int, int]:
    """把季度标签解析成 ``(年, 季度序号)``。

    支持 ``2026年第一季度`` / ``2026年一季度`` / ``2026Q1`` / ``2026-1`` 等写法。
    解析不出来时抛 :class:`QuarterParseError`，而不是让后面出现莫名其妙的下标错误。
    """

    text = str(label).strip()
    for pattern in _QUARTER_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        raw_q = match.group("q")
        quarter = _CN_QUARTER.get(raw_q, None)
        if quarter is None:
            quarter = int(raw_q)
        return int(match.group("year")), quarter

    raise QuarterParseError(
        f"无法解析季度标签 {label!r}，支持的写法如：2026年第一季度、2026年一季度、2026Q1、2026-1"
    )


def quarter_start(year: int, quarter: int) -> date:
    """季度第一天。"""

    return date(year, 3 * (quarter - 1) + 1, 1)


def quarter_end(year: int, quarter: int) -> date:
    """季度最后一天。"""

    if quarter == 4:
        return date(year, 12, 31)
    month = 3 * quarter
    return date(year, month, calendar.monthrange(year, month)[1])


def quarter_end_of(label: str) -> date:
    """季度标签 -> 季度最后一天。"""

    year, quarter = parse_quarter(label)
    return quarter_end(year, quarter)


def quarter_start_of(label: str) -> date:
    """季度标签 -> 季度第一天。"""

    year, quarter = parse_quarter(label)
    return quarter_start(year, quarter)


# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------


@dataclass
class Config:
    """整条流水线的参数。

    目录结构（相对 ``data_root``）::

        data_root/
            处理数据/      # 中间产物
            数据清洗后/    # 清洗后的持仓明细
    """

    data_root: Path = Path("基金数据分析")

    # 业务参数
    position_area: str = ""
    fund_type: str = "股票"
    current_quarter: str = "2026年第一季度"
    previous_quarter: str = "2025年第四季度"
    current_year: str = "2026"
    previous_year: str = "2025"

    # "前十大持仓"文件里年份与季度的配对方式：
    #   straight —— 当年对当年（2026年 → 2026年第一季度）
    #   crossed  —— 保留原始代码的写法（当前季度用 previous_year，上一季度用 current_year）
    # 原始代码用的是 crossed，这里保持不变；确认命名规则后可用 straight。
    year_quarter_pairing: str = "crossed"

    # 标签计算参数
    label_lookback: int = 20
    adjust: str = "qfq"

    # 抓取参数
    retries: int = 3
    backoff: float = 2.0
    pause: float = 0.6
    limit: int | None = None

    # 缓存目录（可选）。同一个股票重复跑时直接读缓存，避免新浪封 IP。
    cache_dir: Path | None = None

    extra: dict = field(default_factory=dict)

    # ---------------- 目录 ----------------

    @property
    def processed_dir(self) -> Path:
        return self.data_root / "处理数据"

    @property
    def cleaned_dir(self) -> Path:
        return self.data_root / "数据清洗后"

    # ---------------- 文件名 ----------------

    def market_value_file(self) -> Path:
        """连续二季度各个基金持仓股票持股总市值。"""

        return self.processed_dir / (
            f"连续二季度各个基金持仓股票持股总市值{self.position_area}"
            f"-{self.current_quarter}与{self.previous_quarter}.csv"
        )

    def position_number_file(self) -> Path:
        """连续二季度股票持有的基金持有家数。"""

        return self.processed_dir / (
            f"连续二季度股票持有的基金持有家数{self.position_area}"
            f"-{self.current_quarter}与{self.previous_quarter}.csv"
        )

    def merged_file(self) -> Path:
        """合并后的中间文件：股票对应的基金持有家数和总市值。"""

        return self.processed_dir / "股票对应的基金持有家数和总市值.csv"

    def labeled_file(self) -> Path:
        """最终产物：带股票流通市值和标签。"""

        return self.processed_dir / "股票对应的基金持有家数和总市值和股票市值及标签.csv"

    def holdings_file(self, quarter: str, year: str) -> Path:
        """某季度的高收益率基金前十大持仓明细。"""

        return self.cleaned_dir / (
            f"{year}年{self.fund_type}型基金近一年高收益率基金的"
            f"前十大持仓-{quarter}.csv"
        )

    def holdings_files(self) -> tuple[Path, Path]:
        """返回 ``(当前季度持仓文件, 上一季度持仓文件)``。"""

        if self.year_quarter_pairing == "straight":
            current_year, previous_year = self.current_year, self.previous_year
        else:
            current_year, previous_year = self.previous_year, self.current_year
        return (
            self.holdings_file(self.current_quarter, current_year),
            self.holdings_file(self.previous_quarter, previous_year),
        )

    # ---------------- 日期 ----------------

    @property
    def current_quarter_end(self) -> date:
        return quarter_end_of(self.current_quarter)

    @property
    def previous_quarter_end(self) -> date:
        return quarter_end_of(self.previous_quarter)

    @property
    def history_start(self) -> str:
        """行情抓取起始日：上一季度开始前留 45 天缓冲，保证股本/价格齐全。"""

        start = quarter_start_of(self.previous_quarter) - timedelta(days=45)
        return start.strftime("%Y%m%d")

    @property
    def history_end(self) -> str:
        """行情抓取结束日：当前季度最后一天。"""

        return self.current_quarter_end.strftime("%Y%m%d")

    def ensure_dirs(self) -> None:
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
