"""数据可视化：把各季度的基金持仓统计画成柱状图并渲染成 HTML。

原始代码（见 ``docs/原始代码_可视化.py``）的问题：

* ``Bar`` / ``opts`` / ``pd`` 全部没导入 -> ``NameError``
* ``webbrowser`` 在另一个段落里 import，函数作用域内看不见 -> ``NameError``
* ``Position_Area`` 从未定义，也没在函数参数里 -> ``NameError``
* ``Year2`` 是形参但函数体里一次都没用
* 输出目录 ``基金数据分析/可视化结果/`` 不存在就 render -> 报错
* ``web.open_new_tab`` 用 Windows 反斜杠拼路径，跨平台失效
* 收益率那段 ``head(10)`` 的返回值没赋值，标题写"前200"却把全部行都画了
* 输出文件名和数据源文件名对不上（"重仓前10股票…" vs 实际是"持有家数"）

本模块把这些一并修掉，并且：

* 路径统一由 :class:`~fundlab.config.Config` 提供，不再散落硬编码
* 输出目录自动创建
* 浏览器自动打开改为可选开关（服务器 / CI 环境下默认关闭）
"""

from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Bar

from .config import Config

logger = logging.getLogger(__name__)


class VisualizeError(RuntimeError):
    """可视化过程中出错。"""


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise VisualizeError(
            f"找不到可视化所需的数据文件：{path}\n"
            f"请确认 data_root / 季度 / 基金类型等参数是否正确。"
        )
    return pd.read_csv(path, encoding="utf-8-sig")


def _bar(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list[str],
    title: str,
    out_path: Path,
    open_browser: bool,
) -> Path:
    """画一张双季度对比柱状图并渲染成 HTML。"""

    for col in [x_col, *y_cols]:
        if col not in df.columns:
            raise VisualizeError(
                f"数据里找不到列 {col!r}，实际列名：{list(df.columns)}"
            )

    bar = Bar()
    bar.add_xaxis(df[x_col].tolist())
    for col in y_cols:
        bar.add_yaxis(col, df[col].tolist())

    bar.set_global_opts(title_opts=opts.TitleOpts(title=title))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bar.render(str(out_path))
    logger.info("图表已生成：%s", out_path)

    if open_browser:
        # 统一用 pathlib 拼路径，Windows / Linux 通用
        webbrowser.open_new_tab(out_path.resolve().as_uri())

    return out_path


def data_visual(
    config: Config,
    quarterly1: str | None = None,
    quarterly2: str | None = None,
    top_n: int = 10,
    open_browser: bool = False,
) -> list[Path]:
    """生成三张对比图（持股总市值 / 持有家数 / 收益率），返回生成的 HTML 路径。

    :param quarterly1: 较新的季度，默认取配置的当前季度
    :param quarterly2: 较旧的季度，默认取配置的上一季度
    :param top_n: 收益率图只画前 N 名（原始代码写的是"前200"却没生效）
    :param open_browser: 是否用浏览器打开。服务器 / CI 环境请保持 False。
    """

    q1 = quarterly1 or config.current_quarter
    q2 = quarterly2 or config.previous_quarter
    out_dir = config.data_root / "可视化结果"
    out_dir.mkdir(parents=True, exist_ok=True)

    produced: list[Path] = []

    # ---------- 1. 各基金持仓股票总市值 ----------
    market = _read(config.market_value_file())
    produced.append(
        _bar(
            market,
            "股票名称",
            [
                f"{q1}各个基金持仓股票持股总市值",
                f"{q2}各个基金持仓股票持股总市值",
            ],
            "比较季度之间各个基金持仓股票持股总市值",
            out_dir / f"{q1}与{q2}比较季度之间各个基金持仓股票持股总市值统计.html",
            open_browser,
        )
    )

    # ---------- 2. 重仓股票持有基金家数 ----------
    number = _read(config.position_number_file())
    produced.append(
        _bar(
            number,
            "股票名称",
            [f"{q1}基金持有家数", f"{q2}基金持有家数"],
            "比较季度之间重仓股票持有基金数量",
            out_dir / f"{q1}与{q2}重仓前{top_n}股票基金持有家数统计.html",
            open_browser,
        )
    )

    # ---------- 3. 基金收益率 ----------
    rate = _read(config.rate_return_file())
    # 原始代码写的是 head(10) 但没赋值，收益率图实际画了全部行；这里真正截取前 N 名
    if "基金名称" in rate.columns:
        rate = rate.head(top_n)
    produced.append(
        _bar(
            rate,
            "基金名称",
            [f"{q1}收益率", f"{q2}收益率"],
            f"比较季度之间收益率（前{len(rate)}名）",
            out_dir / f"{q1}与{q2}收益率统计.html",
            open_browser,
        )
    )

    logger.info("共生成 %d 张图表 -> %s", len(produced), out_dir)
    return produced
