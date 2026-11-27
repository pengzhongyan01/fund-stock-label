"""可视化模块的测试（全部离线，不打开浏览器）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fundlab.config import Config  # noqa: E402
from fundlab.visualize import VisualizeError, data_visual  # noqa: E402
from tests.sample_data import (  # noqa: E402
    CURRENT_QUARTER,
    CURRENT_YEAR,
    FUND_TYPE,
    PREVIOUS_QUARTER,
    PREVIOUS_YEAR,
    build_sample_data,
)


@pytest.fixture
def viz_config(tmp_path) -> Config:
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


def test_rate_return_file_name(viz_config):
    """收益率文件名必须和原始代码的规则一致。"""

    path = viz_config.rate_return_file()
    assert path.name == (
        f"连续二季度基金收益率前200-{CURRENT_QUARTER}与{PREVIOUS_QUARTER}.csv"
    )
    assert path.parent == viz_config.processed_dir


def test_visualize_generates_three_charts(viz_config):
    """应该生成 3 张 HTML 图表。"""

    produced = data_visual(viz_config, open_browser=False)
    assert len(produced) == 3
    for path in produced:
        assert path.exists(), f"{path} 没生成"
        assert path.suffix == ".html"
        # HTML 内容非空，且包含 pyecharts 的产物特征
        content = path.read_text(encoding="utf-8")
        assert len(content) > 1000
        assert "echarts" in content.lower()


def test_output_dir_created(viz_config):
    """输出目录不存在时应该自动创建（原始代码在这里会崩）。"""

    out_dir = viz_config.data_root / "可视化结果"
    assert not out_dir.exists()
    data_visual(viz_config, open_browser=False)
    assert out_dir.is_dir()


def test_top_n_applied(viz_config):
    """top_n 应该真正生效：收益率图只画前 N 行。"""

    # 造一个 30 行的收益率表
    csv_path = viz_config.rate_return_file()
    df = pd.DataFrame(
        {
            "基金名称": [f"基金{i:02d}" for i in range(30)],
            f"{CURRENT_QUARTER}收益率": [0.1] * 30,
            f"{PREVIOUS_QUARTER}收益率": [0.05] * 30,
        }
    )
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    produced = data_visual(viz_config, top_n=5, open_browser=False)
    content = produced[2].read_text(encoding="utf-8")

    # pyecharts 把内容写成 JSON，中文是 \uXXXX 转义
    # 先把转义还原成真实文字，再做断言
    decoded_text = re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda m: chr(int(m.group(1), 16)),
        content,
    )

    assert "前5名" in decoded_text, "标题没体现 top_n"

    # 分类名在 xAxis 的 data 里
    names = re.findall(r'"(基金\d\d)"', decoded_text)
    assert names == ["基金00", "基金01", "基金02", "基金03", "基金04"], names


def test_missing_file_raises_clear_error(tmp_path):
    """数据文件缺失时抛 VisualizeError，而不是难以理解的 KeyError。"""

    config = Config(
        data_root=tmp_path / "没有数据",
        current_quarter=CURRENT_QUARTER,
        previous_quarter=PREVIOUS_QUARTER,
    )
    with pytest.raises(VisualizeError) as exc:
        data_visual(config, open_browser=False)
    assert "找不到" in str(exc.value)


def test_missing_column_raises_clear_error(viz_config):
    """列名对不上时抛 VisualizeError。"""

    csv_path = viz_config.market_value_file()
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df.rename(columns={f"{CURRENT_QUARTER}各个基金持仓股票持股总市值": "错误的列名"})
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with pytest.raises(VisualizeError) as exc:
        data_visual(viz_config, open_browser=False)
    assert "找不到列" in str(exc.value)


def test_no_browser_opened(viz_config, monkeypatch):
    """open_browser=False 时不应该真的去开浏览器。"""

    import fundlab.visualize as viz

    called = []
    monkeypatch.setattr(viz.webbrowser, "open_new_tab", lambda u: called.append(u))

    data_visual(viz_config, open_browser=False)
    assert called == []

    data_visual(viz_config, open_browser=True)
    assert len(called) == 3
    # 必须是 file:// 协议的 URI，不能是 Windows 反斜杠路径
    for uri in called:
        assert uri.startswith("file://")
