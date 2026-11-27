# 推送到 Gitee

## 现状

| 项 | 状态 |
| --- | --- |
| Gitee 用户名 | `pengzhongyan`（SSH 认证已通过） |
| SSH 密钥 | `~/.ssh/id_ed25519_git` ✓ 已存在 |
| 本地代码 | ✓ 32 个文件、8 次提交，工作区干净 |
| Gitee 远程 | 已配置好（`git@gitee.com:pengzhongyan/fund-stock-label.git`） |
| **Gitee 上的仓库** | ⚠️ **还没建 —— 需要你操作** |

`git push` 只能推已有的仓库，不能凭空创建（这是 Gitee 和 GitHub 的区别，
GitHub 支持 push-to-create，Gitee 不支持）。

---

## 第 1 步：建空仓库（30 秒，必须你做）

浏览器打开：<https://gitee.com/projects/new>

| 字段 | 填什么 |
| --- | --- |
| 仓库名称 | `fund-stock-label` |
| 路径 | `pengzhongyan`（一般自动带出） |
| 归属 | `pengzhongyan` |
| 仓库属性 | **私有**（作业建议）或 公开 |
| 设置 | **不要勾选**「使用 Readme 文件初始化这个仓库」 |

> ⚠️ 最后一项必须不勾 —— 勾了远端就有一个 README 提交，
> 后面推送会撞 `non-fast-forward`，还得回来删文件重来。

> **注意仓库名要和本地配置一致**。如果你想用别的名字，
> 告诉我，我改一下 `scripts/推送Gitee.bat` 里的 `REPO_NAME`。

---

## 第 2 步：一键推送

建好后，双击项目里的：

```
scripts\推送Gitee.bat
```

它会自动完成：

1. 检查 SSH 密钥存在
2. 用绝对路径配置 `GIT_SSH_COMMAND`（中文用户名下才不出错）
3. 测试 SSH 认证，失败会提示去加公钥
4. 检查远端仓库是否存在
5. 设置 `gitee` 远程并推送 `main` 分支

---

## 第 3 步：确认

浏览器打开 <https://gitee.com/pengzhongyan/fund-stock-label>

应该能看到：

```
fundlab/          核心代码（5 个模块）
tests/            32 个测试
docs/             修复说明、原始代码存档、操作文档
scripts/          作业助手、推送脚本
.github/workflows/ci.yml
README.md
```

---

## 如果 Gitee 报 404 / 找不到仓库

说明仓库名或用户名不对。手动检查一下：

```bash
# 看本地配的地址
git remote -v
# 应该是 git@gitee.com:pengzhongyan/fund-stock-label.git
```

或者直接命令行推：

```bash
git push -u gitee main
```

---

## 附：SSH 密钥相关

### 公钥在哪

```
C:\Users\彭忠燕\.ssh\id_ed25519_git.pub
```

内容长这样：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPR3eU1nsc1xu8VfiD3iglKiWVTlXVCFjvXGmTTDze8K 15085958265@163.com
```

需要添加到：<https://gitee.com/profile/sshkeys>

> 已经能认证成功，说明公钥早就加过了，不需要再加。

### 为什么命令行要额外配 SSH 参数

你的用户名是中文（`彭忠燕`），Git 默认用 `~/.ssh/known_hosts`，
在某些工具链里会被误解码成 `/c/Users/\305\355\326\322\321\340/.ssh`，
报 `Could not create directory`。

`推送Gitee.bat` 里用的是**绝对路径**：

```
ssh -i "C:\Users\彭忠燕\.ssh\id_ed25519_git" -o IdentitiesOnly=yes ...
```

所以不会踩这个坑。你手动敲命令时如果报错，也用绝对路径。

### Gitee 上没有 GitHub Actions

Gitee 没有 GitHub Actions 那样的 CI。有两个替代方案：

1. **Gitee Go**（<https://gitee.com/enterprise>，企业版功能）—— 有真正的 CI
2. **Gitee 流水线** —— 部分仓库有，需要在仓库设置里开启

**如果老师只看 GitHub**，那 GitHub 那边已经有全绿的 CI 了：

<https://github.com/pengzhongyan01/fund-stock-label/actions>

Gitee 作为"同一个作业的另一份存档"推到就行，不需要额外的 CI。
