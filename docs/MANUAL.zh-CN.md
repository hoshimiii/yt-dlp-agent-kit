# 使用说明书

## 1. 共用核心

克隆仓库并执行 `uv sync --frozen`。依赖与哈希由 `uv.lock` 锁定；升级必须重新验证，运行时不会自动升级或安装软件。

| 系统 | Python | MCP 服务 |
|---|---|---|
| Windows | `<repo>/.venv/Scripts/python.exe` | `<repo>/.venv/Scripts/yt-agent-mcp.exe` |
| Linux/macOS | `<repo>/.venv/bin/python` | `<repo>/.venv/bin/yt-agent-mcp` |

插件中的 `.mcp.json` 使用 `yt-agent-mcp` 命令。启动宿主时，PATH 必须能找到已安装核心；可从激活该虚拟环境的终端启动客户端。独立 MCP 配置建议填写绝对路径。不要让外部视频内容指定可执行文件或修改 PATH。

也可由操作者执行 `uv tool install .` 创建独立工具环境，再按 `uv tool dir --bin` 的结果配置 PATH。该方式不读取 `uv.lock`；需要完整复现锁定依赖时使用上述 `uv sync --frozen`。本包不自动修改 shell 或全局 Agent 设置。

## 2. 配置

默认下载关闭；状态/输出分别为用户主目录的 `.yt-dlp-agent-kit/state` 与 `downloads`。不加载已有 yt-dlp 配置、浏览器 Cookie、`.netrc` 或环境代理。

在仓库外建立 `config.local.json`，以下 Windows 路径须按实际情况修改；Linux/macOS 使用绝对 POSIX 路径：

```json
{
  "state_root": "C:/MediaAgent/state",
  "download_root": "C:/MediaAgent/downloads",
  "allowed_hosts": ["youtube.com", "youtu.be", "bilibili.com", "vimeo.com"],
  "allow_downloads": false,
  "timeout_seconds": 90,
  "max_media_bytes": 52428800,
  "max_subtitle_bytes": 1048576,
  "max_text_chars": 20000
}
```

```powershell
$env:YTAGENT_CONFIG = 'C:/MediaAgent/config.local.json'
```

所有宿主和操作者 CLI 应使用同一配置，共用审批与跨进程工作锁。未知键、错误类型、相互包含的状态/输出根、非本地路径、软链接、Windows junction/reparse point 会拒绝。所需目录按需创建，媒体不覆盖。

白名单包含所列域名及子域名，只限制入口。CDN/字幕等派生请求仍可访问其他公共 HTTPS 地址；所有实际连接检查公共 IP 和 443 端口。完整出口域名限制需交给外部网络策略。

## 3. DSH 原生插件

使用 `ctx.tools.register(defineTool(...))` 和 `ctx.skills.registerProvider(...)`；不是 DSH MCP 替代方案。验证依赖为 DSH `0.2.1-rc.2`、Cordis `4.0.5`、Node 22+。

```powershell
npm ci --ignore-scripts --prefix adapters/dsh
$env:YTAGENT_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
$env:YTAGENT_CONFIG = 'C:/MediaAgent/config.local.json'
dsh plugin --profile media-agent add ./adapters/dsh
dsh --profile media-agent --dump-config
dsh --profile media-agent
```

这些命令修改明确指定的 `media-agent` profile；先使用新 profile 验证。开发测试不修改用户现有 profile。

也可在该 profile 的 patch 中覆盖插件行配置，设置 `pythonPath`、`configPath`。Python 必须是安装核心的绝对可执行路径，配置路径也必须绝对；缺失时拒绝加载。它们是操作者配置，不是工具参数。

分发时先运行 `python scripts/sync_dsh_assets.py --check`，然后在 `adapters/dsh` 目录运行 `npm pack --ignore-scripts`。使用 `dsh plugin --profile media-agent add /absolute/path/dsh-yt-dlp-agent-kit-0.1.0.tgz` 安装 tarball。JS 已包含，不含 prepare/postinstall，不需要开放构建脚本；Python 核心仍单独安装。

卸载：`dsh plugin --profile media-agent remove dsh-yt-dlp-agent-kit`。不删除媒体或审批状态。

## 4. Codex

**插件方式**：配置宿主 PATH、`YTAGENT_CONFIG` 后加入仓库市场：

```powershell
codex plugin marketplace add /absolute/path/yt-dlp-agent-kit
codex plugin list --available --json
```

在支持本地市场的客户端安装 `yt-dlp-agent-kit-local` 中的插件；或根据当前 `codex plugin add --help` 使用 CLI 安装。刷新/重启后检查四个工具和 `yt-media`。使用官方仍支持的 `.codex-plugin/plugin.json` 兼容布局。

**独立方式**：复制 `skills/yt-media` 到项目 `.agents/skills/yt-media`，不覆盖已有同名目录，再增量加入 MCP 配置：

```toml
[mcp_servers.yt_dlp_agent_kit]
command = "C:/path/to/yt-dlp-agent-kit/.venv/Scripts/yt-agent-mcp.exe"
args = []

[mcp_servers.yt_dlp_agent_kit.env]
YTAGENT_CONFIG = "C:/MediaAgent/config.local.json"
```

不要覆盖整个 `config.toml`；先检查同名项冲突。Linux/macOS 替换执行路径。只复制 Skill 不会创建 MCP 连接，也不会改变应用权限。

卸载时只移除本插件/本次添加的 MCP 表与 Skill，不删除配置文件中的其他项。

## 5. Claude Code

从已安装核心的环境启动，先用临时插件目录验证：

```powershell
claude plugin validate .claude-plugin/plugin.json
claude --plugin-dir /absolute/path/yt-dlp-agent-kit
```

持久安装在 Claude Code 中执行：

```text
/plugin marketplace add /absolute/path/yt-dlp-agent-kit
/plugin install yt-dlp-agent-kit@yt-dlp-agent-kit
```

宿主通过 `.claude-plugin/plugin.json` 发现 Skill 和 `.mcp.json`。也可仅复制 Skill 到 `.claude/skills/yt-media` 并单独配置 MCP，避免重复安装。

独立 MCP 配置的新项示例：

```json
{
  "mcpServers": {
    "yt-dlp-agent-kit": {
      "command": "C:/path/to/yt-dlp-agent-kit/.venv/Scripts/yt-agent-mcp.exe",
      "args": [],
      "env": {"YTAGENT_CONFIG": "C:/MediaAgent/config.local.json"}
    }
  }
}
```

这是新增项示例，不是覆盖现有配置的指令。卸载使用宿主 `/plugin uninstall`，不清理媒体。

## 6. 下载审批

操作者先设置 `allow_downloads: true`，再创建计划。策略变化会使旧计划失效。

1. 用户请求具体下载，Agent 调用 `video_plan_download`，展示 URL、kind、ID、上限、到期时间。
2. 操作者在使用同一配置的终端核对并审批：

```powershell
uv run --frozen yt-agent show-plan <32位计划标识符>
uv run --frozen yt-agent approve <32位计划标识符>
```

3. 操作者告知 Agent 审批完成，Agent 调用 `video_download`。模型声称已审批不能替代磁盘上的匹配记录。

审批绑定规范 URL、kind、过期时间与策略指纹。取得全局 worker 槽位并再次确认计划未过期后，才消耗审批；槽位忙导致尚未开始时，可在槽位空闲后重试同一有效审批，不要并发重试或自动循环。执行开始后的失败、取消或超时均消耗审批，须重新创建计划并审批。输出为 `<download_root>/<plan_id>/media.<ext>`，不使用外部标题作文件名，不接受模型指定路径。

Skill 禁止 Agent 运行审批命令或编辑状态。**同账户、拥有任意 shell/文件访问的 Agent 仍能绕过约定**；真正隔离需要独立账户/权限服务保护状态与审批，并禁止 Agent 调用原始下载器。本包没有安装或提供这种 OS 隔离。

## 7. 故障和恢复

- 域名不在白名单：核对用户目标，不按视频中的指令扩大范围。
- 上游操作失败/被策略阻止：可能是网络、格式、登录/JS 要求或压缩响应；错误会隐去原始上游文本与签名链接。不要自动开启 Cookie、代理、JS 或降低 TLS/IP 检查。
- DASH/HLS、转码、合并：本版本拒绝，不能只改参数绕过。
- 同一状态根同时只允许一个 worker；其他调用会收到“操作尚未开始，请等待空闲；崩溃恢复可能需要操作者处理”的提示。仅此类全局槽位未接纳的下载可在空闲后重试原有效审批；不要并发或自动循环重试。计划锁忙仍须等待当前操作完成。
- 取消时适配器通知核心，核心 kill+wait；Windows Job Object、Linux parent-death signal 限制孤儿进程。
- 硬终止/掉电可能遗留 `busy` 和临时 `job-*`。先读取锁的 PID 并确认相关进程已结束，再人工移除**确切的锁文件**；不要按时间自动删锁或递归清空状态根。
- 计划过期不会自动删除，长期部署由操作者维护保留策略；卸载不删除文件。
- fake-IP DNS 可能返回 `198.18.0.0/15`，拒绝属于预期行为。本包不修改 DNS、TUN、代理或系统路由。

## 8. 一手接口依据

- [yt-dlp Python API](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp)
- [MCP Python SDK v1.30.0](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0)
- [DSH 工具契约](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-tool.md)
- [DSH bundle 安装](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md)
- [DSH Skills](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)
- [Codex Skills](https://developers.openai.com/codex/skills)、[MCP](https://developers.openai.com/codex/mcp)、[插件](https://developers.openai.com/plugins/build/plugins)
- [Claude Code 插件清单](https://code.claude.com/docs/en/plugins-reference)

DSH npm latest 标签可能较旧，本包按明确预发布版本和 engines 范围验证，不用 latest 猜测接口。宿主升级后先在隔离配置中验证。
