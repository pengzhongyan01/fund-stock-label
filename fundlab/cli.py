"""命令行入口。

用法::

    python -m fundlab --data-root ./基金数据分析 \
        --current-quarter 2026年第一季度 --previous-quarter 2025年第四季度 \
        --fund-type 股票 --current-year 2026 --previous-year 2025
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import Config
from .pipeline import get_stock_label, merge_position_and_market, run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fundlab",
        description="融合基金持仓与股票市值，并进行标签化，为下一步的训练提供数据",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("基金数据分析"),
        help="数据根目录，默认 ./基金数据分析",
    )
    parser.add_argument("--position-area", default="", help="持仓区域后缀，例如 沪市")
    parser.add_argument("--fund-type", default="股票", help="基金类型，例如 股票 / 混合")
    parser.add_argument("--current-quarter", default="2026年第一季度", help="当前季度标签")
    parser.add_argument("--previous-quarter", default="2025年第四季度", help="上一季度标签")
    parser.add_argument("--current-year", default="2026", help="当前年份")
    parser.add_argument("--previous-year", default="2025", help="上一年度")
    parser.add_argument(
        "--year-quarter-pairing",
        choices=("crossed", "straight"),
        default="crossed",
        help="持仓文件名的年份-季度配对方式，默认 crossed（与原始代码一致）",
    )
    parser.add_argument("--label-lookback", type=int, default=20, help="计算涨跌幅的回看交易日数")
    parser.add_argument("--adjust", default="qfq", choices=("qfq", "hfq", ""), help="复权方式")
    parser.add_argument("--retries", type=int, default=3, help="抓取重试次数")
    parser.add_argument("--backoff", type=float, default=2.0, help="重试退避基数（秒）")
    parser.add_argument("--pause", type=float, default=0.6, help="每次抓取之间的间隔（秒）")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 只股票，用于快速验证")
    parser.add_argument("--cache-dir", type=Path, default=None, help="行情缓存目录")
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="跳过合并步骤，直接用已有的合并结果打标签",
    )
    parser.add_argument(
        "--skip-label",
        action="store_true",
        help="只做合并，不抓行情",
    )
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = Config(
        data_root=args.data_root,
        position_area=args.position_area,
        fund_type=args.fund_type,
        current_quarter=args.current_quarter,
        previous_quarter=args.previous_quarter,
        current_year=args.current_year,
        previous_year=args.previous_year,
        year_quarter_pairing=args.year_quarter_pairing,
        label_lookback=args.label_lookback,
        adjust=args.adjust,
        retries=args.retries,
        backoff=args.backoff,
        pause=args.pause,
        limit=args.limit,
        cache_dir=args.cache_dir,
    )

    try:
        if args.skip_label:
            merge_position_and_market(config)
        elif args.skip_merge:
            get_stock_label(config)
        else:
            run(config)
    except FileNotFoundError as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 2
    except Exception as exc:
        logging.getLogger(__name__).error("运行失败：%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
