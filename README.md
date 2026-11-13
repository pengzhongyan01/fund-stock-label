# 基金持仓与股票市值融合、标签化

把「连续二季度基金持有家数」和「连续二季度各基金持仓股票持股总市值」合并，
再抓取个股行情计算各季度流通市值并打标签（优 / 良 / 中 / 差），为下一步的模型训练
提供数据。

本仓库是《计算机系统》课程「代码阅读及调试」作业的工程化版本：原始代码见
`docs/原始代码.py`，逐条问题分析见 [`docs/修复说明.md`](docs/修复说明.md)。

## 快速开始

```bash
git clone <your-repo-url>
cd <your-repo-dir>

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 跑一遍完整流程（合并 -> 打标签）
python -m fundlab --data-root ./基金数据分析 \
    --current-quarter 2026年第一季度 \
    --previous-quarter 2025年第四季度 \
    --current-year 2026 \
    --previous-year 2025 \
    --fund-type 股票
```

首次验证可以加 `--limit 10` 只处理前 10 只股票，快速确认链路通不通。

## 输入 / 输出目录约定

```
基金数据分析/
├── 处理数据/                                   # 中间产物
│   ├── 连续二季度各个基金持仓股票持股总市值-{当前季度}与{上一季度}.csv
│   ├── 连续二季度股票持有的基金持有家数-{当前季度}与{上一季度}.csv
│   ├── 股票对应的基金持有家数和总市值.csv        ← 合并产物
│   └── 股票对应的基金持有家数和总市值和股票市值及标签.csv  ← 最终产物
└── 数据清洗后/                                 # 持仓明细
    ├── {年份}年{基金类型}型基金近一年高收益率基金的前十大持仓-{当前季度}.csv
    └── {年份}年{基金类型}型基金近一年高收益率基金的前十大持仓-{上一季度}.csv
```

输入 CSV 用 Excel 导出时默认是 UTF-8 BOM，代码按 `utf-8-sig` 读取。

### 输入表的列要求

| 文件 | 需要的列 |
| --- | --- |
| 连续二季度各个基金持仓股票持股总市值 | 第一列股票名称，第 2 列当前季度，第 3 列上一季度 |
| 连续二季度股票持有的基金持有家数 | 第一列股票名称，第 2 列当前季度，第 3 列上一季度 |
| 前十大持仓 | `持仓股票代码`、`持仓股票名称`（或第 5 列为股票名称） |

持仓明细会用 `dtype=str` 读取，否则 pandas 会把 `000001` 解析成整数 `1`，前导零丢失后
股票代码就错了。

## 标签规则

按当前季度最后一个交易日往前回看 20 个交易日的涨跌幅：

| 区间涨跌幅 | 标签 | 含义 |
| --- | --- | --- |
| ≥ 1.2 | 1 | 优 |
| 1.1 ~ 1.2 | 2 | 良 |
| 0.85 ~ 1.1 | 3 | 中 |
| < 0.85 | 4 | 差 |

无法获取行情的股票保持默认标签 3，并在日志的「失败清单」里列出，不会中断整批任务。

## 命令行参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--data-root` | `基金数据分析` | 数据根目录 |
| `--position-area` | 空 | 持仓区域后缀，参与中间文件名 |
| `--fund-type` | `股票` | 基金类型，参与持仓文件名 |
| `--current-quarter` | `2026年第一季度` | 当前季度标签 |
| `--previous-quarter` | `2025年第四季度` | 上一季度标签 |
| `--current-year` / `--previous-year` | `2026` / `2025` | 年份 |
| `--year-quarter-pairing` | `crossed` | 持仓文件的年份-季度配对方式，见下 |
| `--label-lookback` | `20` | 计算涨跌幅的回看交易日数 |
| `--adjust` | `qfq` | 复权方式，`qfq` / `hfq` / 空（不复权） |
| `--retries` | `3` | 抓取重试次数 |
| `--backoff` | `2.0` | 重试退避基数（秒） |
| `--pause` | `0.6` | 每次抓取之间的间隔（秒），避免被新浪封 IP |
| `--limit` | 无 | 只处理前 N 只股票，用于快速验证 |
| `--cache-dir` | 无 | 行情缓存目录，重跑时直接读缓存 |
| `--skip-merge` | 关 | 跳过合并，直接用已有合并结果打标签 |
| `--skip-label` | 关 | 只做合并，不抓行情 |

### 年份-季度配对

原始代码里，当前季度的持仓文件用 `previous_year` 命名、上一季度的用 `current_year`
命名（年份和季度交叉）。本项目保留了这一行为（`--year-quarter-pairing crossed`），
确认命名规则后可以改成 `straight` 让年份和季度对应上。

## 交付与截图

作业实体是 **GitHub 仓库 + Word 文档**；老师要的截图是"代码真的跑起来了"的**证据**。

| 优先级 | 截图 | 从哪儿截 |
| --- | --- | --- |
| ⭐ 必交 | GitHub Actions 全绿 | 仓库 → Actions 标签页 |
| ⭐ 必交 | Actions 里 pytest 的 `25 passed` | 点进 test job → "运行测试" step |
| 🟡 加分 | 本地运行成功的终端 | `bash scripts/verify_local.sh` |

生成一份可直接复制的验证报告：

```bash
python scripts/make_evidence.py     # 输出到 docs/验证报告.txt
```

完整步骤（含推送命令、截图要点、发给老师的话术）见
[`docs/交付指南.md`](docs/交付指南.md)。

## GitHub Actions

`.github/workflows/ci.yml` 会在 push / PR 时自动：

1. 在 Python 3.11 / 3.12 / 3.13 上跑单元测试（全部离线，不访问外网）；
2. 做编译检查；
3. 跑一个使用内置样例数据的端到端冒烟测试。

> ⚠️ Python 3.10 已从矩阵中移除：pandas ≥ 3.1 与 akshare ≥ 1.20 均要求
> Python ≥ 3.11，3.10 无法安装依赖会让 job 变红。

因为新浪接口会封 IP，CI 不直接抓真实行情；真实数据请在本地跑，或用
[Actions 定时任务](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows)
在有缓存的环境里执行。

## 开发

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

测试全部离线运行（`tests/sample_data.py` 会生成一份完整的样例数据集），
不依赖外网和真实数据文件。

## 项目结构

```
fundlab/
├── config.py      # 路径、季度标签解析、参数配置
├── market.py      # 股票代码规范化、行情抓取（重试/退避/缓存）、打标签
├── pipeline.py    # 合并持仓与市值 -> 抓行情 -> 打标签
└── cli.py         # 命令行入口
docs/
├── 原始代码.py    # 作业原始代码存档
├── 修复说明.md    # 逐条问题分析与修复对照
├── 交付指南.md    # 推送步骤、截图清单、话术
└── 验证报告.txt   # 自动生成的验证报告（可复制进实验报告）
scripts/
├── verify_local.sh   # 本地复现 CI 全流程，用于截图
├── make_evidence.py  # 生成验证报告
└── update_docx.py    # 把修复说明与修复后代码写回作业 Word 文档
tests/
├── sample_data.py # 样例数据生成器
└── test_pipeline.py
```

## 许可

课程作业，仅供学习交流。
