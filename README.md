# yt-dlp Agent Kit

一套共用核心的公共视频工具和 Skill：**DeepSeek Harness 原生插件、Codex 插件、Claude Code 插件**。提供视频信息、已有字幕和受控下载，无需依赖第三方 yt-dlp MCP。

| 客户端 | 接入形式 |
|---|---|
| DeepSeek Harness / DSH | 原生 Cordis bundle，注册工具和打包 Skill |
| Codex | 本地插件 / 独立 Skill + stdio MCP |
| Claude Code | 原生插件 / 独立 Skill + stdio MCP |
| 其他 Agent / 程序 | stdio MCP、JSON CLI 或 Python `Service` |

四种入口共用参数契约、URL/路径验证、资源限制和审批。默认关闭媒体下载；启用后每个计划仍需操作者在 Agent 工具之外审批。无安装钩子、无 HTTP 监听端口。

## 快速开始

要求 Python 3.11+、[uv](https://docs.astral.sh/uv/)；DSH 插件另需 Node.js 22+ 和 DSH `0.2.1-rc.2` 兼容版本。运行时禁用 FFmpeg、JS 运行时、外部下载器和 yt-dlp 插件，无需安装它们。

```powershell
git clone https://github.com/hoshimiii/yt-dlp-agent-kit.git
cd yt-dlp-agent-kit
uv sync --frozen
'{"tool":"video_info","arguments":{"url":"https://www.youtube.com/watch?v=BaW_jenozKc"}}' | uv run --frozen yt-agent call
```

通过 stdin 传 JSON，避免把链接拼成 shell 命令。示例不表示目标网站在当前网络和安全限制下必定可用。安装各客户端、配置与审批见 **[使用说明书](docs/MANUAL.zh-CN.md)**。

## 工具

| 工具 | 输入 | 结果 / 副作用 |
|---|---|---|
| `video_info` | `url` | 有界元数据和字幕语言 |
| `video_subtitles` | `url`, `lang="en"` | 一个已有 VTT/SRT 轨道；明确标记文本截断 |
| `video_plan_download` | `url`, `kind="video"` | 本地创建 15 分钟计划；不下载、不审批 |
| `video_download` | `identifier` | 消耗匹配审批并下载，返回实际位置和大小 |

默认接受 YouTube、Bilibili、Vimeo 单视频链接；操作者可增加明确域名。支持范围是 yt-dlp 能力与本包安全限制的交集：视频仅单文件直连 HTTPS、最高 720p；不处理播放列表、直播、DASH/HLS 合并、DRM、登录 Cookie、转码或语音识别。音频优先选音频轨道，否则保留兼容合并媒体，可能仍含视频，不承诺 MP3。

## 项目树

```text
yt-dlp-agent-kit/
├── README.md / LICENSE / SECURITY.md
├── AGENTS.md / CONTEXT.md            # 维护规则与当前验收状态
├── pyproject.toml / uv.lock          # Python 包与锁定依赖
├── .mcp.json                        # 共用 stdio MCP 启动声明
├── .codex-plugin/plugin.json        # Codex 兼容插件清单
├── .agents/plugins/marketplace.json
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── src/yt_agent/
│   ├── policy.py                    # 配置、URL/IP、路径、数据边界
│   ├── service.py                   # 审批、锁、worker 监管
│   ├── worker.py                    # 独立进程中的 yt-dlp
│   ├── cli.py                       # JSON CLI、本地审批
│   ├── mcp_server.py                # stdio MCP
│   └── tools.json                   # 共用工具契约
├── skills/yt-media/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── adapters/dsh/
│   ├── package.json / package-lock.json
│   ├── cordis.patch.yml             # 可安装 DSH bundle
│   ├── index.js / bridge.js         # 原生注册、无 shell 桥接
│   ├── tools.json / skills/         # 共用源的同步副本，测试防漂移
│   └── test/plugin.test.js
├── docs/
│   ├── MANUAL.zh-CN.md              # 安装、使用、运维
│   ├── SECURITY-DESIGN.md           # 威胁、防护、剩余风险
│   └── VERIFICATION.md              # 验证记录与限制
├── scripts/
│   ├── sync_dsh_assets.py
│   └── smoke_live.py                # 显式外网样本测试
├── tests/                           # 核心、安全、MCP 集成
└── .github/workflows/ci.yml          # Windows / Linux 验证
```

`.venv/`、`.cache/`、`node_modules/`、本地配置、状态和媒体不进入 Git。

## 验证

```powershell
uv run --frozen python -m unittest discover -s tests -v
npm ci --ignore-scripts --prefix adapters/dsh
$env:YTAGENT_TEST_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
npm test --prefix adapters/dsh
uv run --frozen python scripts/sync_dsh_assets.py --check
```

Linux/macOS 的 Python 路径改为 `.venv/bin/python`。详见 [验证记录](docs/VERIFICATION.md)。

**不承诺零 Bug 或百分之百防提示词注入。** 限制由代码执行，但 Skill 和 MCP 提示不能约束拥有任意 shell/文件权限的 Agent；强隔离需要宿主权限、独立账户或容器。见 [安全设计](docs/SECURITY-DESIGN.md)。

MIT 许可；第三方组件保留各自许可。与 DeepSeek、OpenAI、Anthropic 及视频站点无官方合作关系。仅处理你有权访问和保存的内容。
