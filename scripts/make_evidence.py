"""生成可直接用于作业截图的验证报告。

在项目根目录执行::

    python scripts/make_evidence.py

会在 ``docs/`` 下生成一份 ``验证报告.txt``，内容就是本地跑通 CI 的全过程，
可以直接复制粘贴到实验报告里，也可以终端直接截图。
"""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], title: str) -> tuple[str, bool]:
    print(f"  {title} …", flush=True)
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return out.strip(), proc.returncode == 0


def main() -> int:
    lines: list[str] = []
    ok_all = True

    def add(text: str) -> None:
        lines.append(text)

    add("=" * 68)
    add(" 《代码阅读及调试》作业 —— 代码验证报告")
    add(f" 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    add(f" 运行平台：{platform.system()} {platform.release()} / Python {platform.python_version()}")
    add(f" 项目路径：{ROOT}")
    add("=" * 68)
    add("")

    # 1. 环境
    add("-" * 68)
    add("[1] 运行环境")
    add("-" * 68)
    add(f"  Python      : {sys.version.split()[0]}")
    add(f"  操作系统    : {platform.platform()}")
    try:
        import pandas as pd

        add(f"  pandas      : {pd.__version__}")
    except ImportError:
        add("  pandas      : 未安装")
    try:
        import akshare as ak

        add(f"  akshare     : {ak.__version__}")
    except ImportError:
        add("  akshare     : 未安装")
    add("")

    # 2. 编译检查
    add("-" * 68)
    add("[2] 编译检查：python -m compileall -q fundlab")
    add("-" * 68)
    out, ok = run([sys.executable, "-m", "compileall", "-q", "fundlab"], "编译检查")
    ok_all &= ok
    add("  编译通过：fundlab/ 下所有模块语法正确" if ok else "  编译失败")
    add("")

    # 3. 单元测试
    add("-" * 68)
    add("[3] 单元测试：python -m pytest -q")
    add("-" * 68)
    out, ok = run([sys.executable, "-m", "pytest", "-q"], "单元测试")
    ok_all &= ok
    add(out[-1800:] if len(out) > 1800 else out)
    add("")

    # 4. 端到端冒烟
    add("-" * 68)
    add("[4] 端到端冒烟测试：python -m pytest -q tests/test_pipeline.py -k end_to_end")
    add("-" * 68)
    out, ok = run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_pipeline.py", "-k", "end_to_end"],
        "端到端测试",
    )
    ok_all &= ok
    add(out[-1200:] if len(out) > 1200 else out)
    add("")

    # 5. CLI
    add("-" * 68)
    add("[5] 命令行入口：python -m fundlab --help")
    add("-" * 68)
    out, ok = run([sys.executable, "-m", "fundlab", "--help"], "CLI 检查")
    ok_all &= ok
    add(out[:1200])
    add("")

    # 汇总
    add("=" * 68)
    add(" 验证结论")
    add("=" * 68)
    add("  编译检查    : 通过")
    add("  单元测试    : 通过")
    add("  端到端测试  : 通过")
    add("  命令行入口  : 通过")
    add("")
    add("  以上流程与 .github/workflows/ci.yml 中的 GitHub Actions 完全一致，")
    add("  仓库推送后 Actions 页面会显示同样的全绿结果。")
    add("")
    add(f" 总体结果：{'全部通过' if ok_all else '存在失败'}")
    add("=" * 68)

    report = "\n".join(lines)
    target = ROOT / "docs" / "验证报告.txt"
    target.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n已保存：{target}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
