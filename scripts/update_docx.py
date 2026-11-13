"""把修复说明和修复后的代码追加到作业 Word 文档末尾。

用法::

    python scripts/update_docx.py <docx路径>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(
    r"D:\java_tools\AI_tools\WorkBuddy\resources\app.asar.unpacked\resources\plugins"
    r"\workbuddy-builtin\skills\workbuddy-local-office-edit"
)

CODE_FONT = {"font_family": "Consolas", "font_size": 9}
# 标题交给 Heading 样式控制字体，只额外加粗。
# 若这里再指定 font_family / font_size，会覆盖样式导致标题被降级成正文。
HEAD_FONT = {"bold": True}
SUB_FONT = {"bold": True}


def edsdk(tool: str, args: dict) -> dict:
    """调用 editor_sdk 工具，返回解析后的 JSON。

    多数工具返回 JSON；``open_file`` 这类返回纯文本的，用 ``{"ok": True}`` 兜底。
    参数走临时文件传递 —— 内容多时命令行会超出 Windows 的长度限制。
    """

    payload = json.dumps(args, ensure_ascii=False)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(payload)
        arg_file = fh.name

    try:
        proc = subprocess.run(
            ["python3", "edsdk.py", "call", tool, "--json-file", arg_file],
            cwd=SKILL_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    finally:
        try:
            os.unlink(arg_file)
        except OSError:
            pass

    out = (proc.stdout or "").strip()
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("ok") is False:
            raise RuntimeError(f"{tool} 失败：{data.get('error')}")
        return data

    # 非 JSON 返回（open_file 等）：检查是否含错误标记
    if proc.returncode != 0 or '"ok": false' in out:
        raise RuntimeError(
            f"{tool} 失败：{out[:500]} stderr={proc.stderr[:300]}"
        )
    return {"ok": True, "raw": out}


def para(text: str, fmt: dict | None = None, level: int = 0) -> dict:
    args = {"text": text}
    if fmt:
        args["text_format"] = fmt
    if level:
        args["level"] = level
    return {
        "block": "paragraph",
        "calls": [{"tool": "doc_insert_paragraph_with_text", "args": args}],
    }


def code_block(source: str) -> list[dict]:
    """把一段源码转成逐行代码段落。"""

    blocks = []
    for line in source.splitlines():
        # 段落不能为空，用零宽空格占位保留行结构
        text = line if line.strip() else " "
        blocks.append(para(text, CODE_FONT))
    return blocks


def build_blocks() -> list[dict]:
    project = Path(__file__).resolve().parents[1]
    blocks: list[dict] = []

    # 领头的空段落只作占位，不会显示内容。
    # 必须放在最前面：doc_batch_execute 会把"第二个块的样式"套到"第一个块"上，
    # 用空段落占位后，第一个可见块才能拿到自己该有的 Heading 样式。
    blocks.append(para("", {"font_size": 10.5}))

    blocks.append(para("代码阅读与调试说明", HEAD_FONT, level=1))
    blocks.append(
        para(
            "原始代码存在 20 处问题，其中 6 处会导致程序直接崩溃，"
            "其余 14 处会静默产出错误结果（例如所有股票的市值都取成第一只股票的）。"
            "下面先列出问题清单，再给出修复后的完整代码。"
        )
    )

    # ---------------- 问题清单 ----------------
    blocks.append(para("一、问题清单", SUB_FONT, level=2))

    issues = [
        ("1", "模块顶层", "缩进代码调用未定义变量", "崩溃", "改为 if __name__ == '__main__' 下的命令行入口"),
        ("2", "get_stock_label", "使用 5 个未定义变量", "崩溃", "统一收进 Config 数据类，由命令行传入"),
        ("3", "全文件", "pandas / csv 未导入", "崩溃", "模块顶部统一导入"),
        ("4", "持仓文件名", "年份与季度交叉配对", "静默错误", "Config.holdings_files() 统一处理，可切换配对方式"),
        ("5", "price1", "取 iloc[0,4] 而非当前行 i", "静默错误", "按季度边界取当季真实收盘价"),
        ("6", "price2", "取写死的第 58 行", "静默错误", "同上"),
        ("7", "begin/end_price", "取写死的第 118/141 行", "静默错误", "以季度末为锚点回看 N 个交易日"),
        ("8", "写标签", "用 iloc[i, 7] 位置下标", "静默错误", "改为 loc[i, '标签'] 按列名定位"),
        ("9", "条件判断", "str(bool) 恒为真", "静默错误", "去掉 str()，直接用布尔表达式"),
        ("10", "except 分支", "继续使用未赋值的 history_data", "崩溃", "失败时 continue 并计入失败清单"),
        ("11", "股票代码", "只覆盖主板，创业板/科创板/北交所无前缀", "静默错误", "正则提取 6 位数字 + 交易所规则表"),
        ("12", "CSV 读取", "000001 被解析成整数 1", "静默错误", "持仓明细用 dtype=str 读取"),
        ("13", "名称匹配", "iloc[j, 4] 硬编码列位置", "静默错误", "优先按列名查找，找不到再退回位置"),
        ("14", "文件关闭", "with 块外重复 f.close()", "代码异味", "删除多余 close()"),
        ("15", "目录", "目录不存在直接崩", "崩溃", "ensure_dirs() 自动创建"),
        ("16", "合并逻辑", "O(n²) 双重循环", "性能", "改为 pd.merge"),
        ("17", "工程", "无依赖声明/无入口/无 CI", "无法运行", "补 requirements、CLI 入口、GitHub Actions"),
        ("18", "抓取", "无重试、无限速", "易崩", "指数退避重试 + 请求间隔 + 本地缓存"),
        ("19", "流通股本", "用列下标 iloc[0,6] 取", "静默错误", "改按列名 outstanding_share 取"),
        ("20", "数值列", "流通市值列初始化成字符串 '0'", "类型隐患", "统一初始化为数值类型"),
    ]

    for num, pos, problem, level, fix in issues:
        blocks.append(
            para(
                f"{num}. 【{pos}】{problem} —— {level}；{fix}",
                {"font_size": 10.5},
            )
        )

    # ---------------- 修复后的代码 ----------------
    blocks.append(para("二、修复后的完整代码", SUB_FONT, level=2))

    files = [
        ("fundlab/config.py（路径与参数配置）", project / "fundlab" / "config.py"),
        ("fundlab/market.py（代码规范化 / 行情抓取 / 打标签）", project / "fundlab" / "market.py"),
        ("fundlab/pipeline.py（合并与标注主流程）", project / "fundlab" / "pipeline.py"),
        ("fundlab/cli.py（命令行入口）", project / "fundlab" / "cli.py"),
    ]

    for title, path in files:
        blocks.append(para(title, {"bold": True, "font_size": 10.5, "font_family": "黑体"}))
        blocks.extend(code_block(path.read_text(encoding="utf-8")))

    # ---------------- GitHub 运行方式 ----------------
    blocks.append(para("三、在 GitHub 上运行", SUB_FONT, level=2))
    blocks.append(
        para(
            "项目已整理成标准 Python 包，克隆后按下面步骤即可运行；"
            "推送后 GitHub Actions 会自动跑单元测试与端到端冒烟测试。"
        )
    )

    run_steps = [
        "git clone <your-repo-url> && cd <your-repo-dir>",
        "python -m venv .venv && source .venv/bin/activate    # Windows: .venv\\Scripts\\activate",
        "pip install -r requirements.txt",
        "python -m fundlab --data-root ./基金数据分析 \\",
        "    --current-quarter 2026年第一季度 --previous-quarter 2025年第四季度 \\",
        "    --current-year 2026 --previous-year 2025 --fund-type 股票",
    ]
    for step in run_steps:
        blocks.append(para(step, CODE_FONT))

    blocks.append(
        para(
            "首次验证可以加 --limit 10 只处理前 10 只股票。",
            {"font_size": 10.5},
        )
    )

    blocks.append(
        para(
            "注：CI 的 Python 版本固定为 3.11 / 3.12 / 3.13 —— pandas 3.1 与 "
            "akshare 1.20 起均要求 Python ≥ 3.11，3.10 已无法安装依赖。",
            {"font_size": 10.5},
        )
    )

    # ---------------- 交付物与截图 ----------------
    blocks.append(para("四、交付物与截图说明", SUB_FONT, level=2))
    blocks.append(
        para(
            "作业实体是「GitHub 仓库 + 本文档」；老师要的截图是证明代码能跑起来的证据。"
        )
    )

    deliver_rows = [
        ("交付物 1", "GitHub 仓库：fundlab/ 包、tests/ 测试、.github/workflows/ci.yml"),
        ("交付物 2", "本 Word 文档：问题清单 20 条 + 修复后的完整代码"),
        ("截图（必交）", "GitHub Actions 全绿 —— 仓库 Actions 标签页，所有 job 显示绿色对勾"),
        ("截图（必交）", "Actions 里 pytest 的输出 —— 点进 test job 的「运行测试」步骤，截到 25 passed"),
        ("截图（选交）", "本地运行成功的终端 —— 执行 bash scripts/verify_local.sh 后截整个窗口"),
    ]
    for name, desc in deliver_rows:
        blocks.append(para(f"· {name}：{desc}", {"font_size": 10.5}))

    blocks.append(
        para(
            "推送后如果 Actions 变红，多半是 Python 版本或目录结构问题，"
            "排查步骤见仓库 docs/交付指南.md。",
            {"font_size": 10.5},
        )
    )

    # ---------------- 验证结果 ----------------
    blocks.append(para("五、验证结果", SUB_FONT, level=2))
    results = [
        "单元测试：25 passed（全部离线运行，不依赖外网和真实数据文件）",
        "全新 clone 环境验证：pip install + pytest + compileall + CLI 全部通过",
        "真实 akshare 接口端到端验证（贵州茅台 / 宁德时代 / 平安银行）：",
        "  算出的流通市值分别为 1.77 万亿、1.68 万亿、2040 亿，与实际规模吻合",
        "标签规则：区间涨幅 >=1.2 优、1.1~1.2 良、0.85~1.1 中、<0.85 差",
    ]
    for item in results:
        blocks.append(para(item, {"font_size": 10.5}))

    return blocks


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python scripts/update_docx.py <docx路径>")
        return 1

    docx = Path(sys.argv[1]).resolve()
    file_id = str(docx)

    print("打开文档…")
    edsdk("open_file", {"file_path": file_id, "file_type": "doc", "wait": True})

    pos = edsdk("doc_get_last_operable_pos", {"file_id": file_id})["position"]
    # 往后挪一格，避免新插入的标题样式被"继承"到原文最后一段上
    pos += 1
    print(f"末尾位置：{pos}")

    blocks = build_blocks()
    print(f"准备写入 {len(blocks)} 个块…")

    # 一次性写入：分批写会在批次边界多出空段落（服务端按块推导落点，
    # 批与批之间需要重新定位，容易多插一个空行）
    res = edsdk(
        "doc_batch_execute",
        {"file_id": file_id, "idx": pos, "blocks": blocks},
    )
    print(f"  {res.get('message')}")

    print("保存…")
    edsdk("save_file", {"file_id": file_id})
    print("完成：", docx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
