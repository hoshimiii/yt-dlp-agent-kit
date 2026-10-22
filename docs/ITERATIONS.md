# 五轮用户测试与优化记录

本次基线为 v0.1.0（主分支 `6b9aa0e`），工作分支为
`feat/v0.2.0-iterations`。每轮使用上一轮验收后的代码，保留独立 Git
提交；既有发布标签不移动。测试仅使用隔离本地状态与确定性传输样本。

Astra（`gpt-6-astra`，high）扮演用户并实际测试；Sol 架构师独立评审
接口、安全边界和兼容性；root 记录需求、提出方案并负责集成验收。
模型角色模拟不等于真实用户访谈或完整宿主登录测试。

每轮必须完成：使用并记录问题 → 提出最小方案 → 用户测试与架构师
共同评审 → 实现和针对性回归 → Astra 复测 → Git 检查点。
未完成的阶段不记为通过，不为凑轮次预先批准功能。

推送门槛：5 轮先在本地完成；root 检查实际 diff，完整测试、架构审核及
构建包验证通过后统一推送。GitHub 不再作为外网站点故障的反复调试入口。

| 轮次 | 需求与方案 | 联合评审 | 实现及复测 | Git 检查点 |
|---|---|---|---|---|
| 1 | 正常资源竞争不应消耗尚未执行的下载审批 | 双方通过 | 独立复测通过；36 Python + 4 DSH | `bbfe7b3` |
| 2 | 重复审批不应误报配置/权限故障 | 双方通过 | Astra 真实 CLI 复测通过；40 Python | `c0dc3c2` |
| 3 | 不支持的人工字幕不应遮蔽可用自动字幕 | 双方通过 | 独立复测通过；44 Python | `25070dd` |
| 4 | 缺失配置统一诊断，MCP 不泄露原始本地路径 | 双方通过 | 三入口独立复测通过；48 Python + 5 DSH | `1c9e29d` |
| 5 | 操作者 show-plan 显示可信大小上限与下载开关 | 双方通过 | 独立 CLI 复测通过；50 Python | `7cec9d1` |

## R1：执行槽位忙时保留审批

**观察**：Astra 使用真实 CLI、stdio MCP 和发布包 DSH bridge 创建离线
计划；在无网络核心 fixture 中占用全局 worker，再提交已审批下载。
结果为 busy，runner 调用为 0，但 approved 已被移到 consumed；槽位释放
后既不能下载，也不能重新审批。证据在忽略目录
`.cache/astra-ux/round1/evidence.json`，不作为在线下载验收。

**需求**：正常并发竞争未被接纳执行时保留现有审批，槽位空闲后可重试；
真正进入执行仍须在任何网络访问前消耗审批，失败后不能补回。

**最小方案**：保留“计划锁 → 全局 worker 锁”的统一顺序；校验审批后，
先进入既有 `work()`，成功取得槽位后才移动审批并开始下载准备。
全局 busy 使用独立受控提示，说明尚未开始并等待空闲；不自动删除锁、
不排队、不恢复消费过的审批。同步 Skill 与手册的忙时重试边界。

**验收**：占用槽位时不调用 runner、不创建最终输出且审批保留；释放后
同一计划成功一次；执行失败仍消费审批；计划并发消费和全局单 worker
测试继续通过。过期、策略变化和审批不匹配继续拒绝。

**联合评审**：Astra APPROVE；Sol APPROVE_WITH_CONDITIONS。实现还须在
成功取得槽位后、消费审批前重查到期时间；缺失/不匹配审批须在创建 job
之前拒绝；区分计划忙与全局忙，不把 runner/输出错误改写为 busy。
Astra 要求不续期、不循环重试、不自动删除遗留锁。已纳入方案与回归。

**实现与验收**：已落实方案，增加 busy 保留审批/同计划单次成功、入场
恰好过期的清理、计划与全局锁区分三项回归。Sol 检查实际 diff 并独立运行
18 项 service 测试后 ACCEPT。Astra 独立脚本确认审批和计划在 busy 时逐
字节不变、释放后只执行一次、runner 失败仍消费、到期不续期且锁/job 清理
正确，结果 PASS，证据为 `.cache/astra-ux/round1/retest-evidence.json`。
root 集成检查为 36 项 Python 与 4 项 DSH 测试通过。

## R2：有效审批幂等确认

**观察**：Astra 在 `bbfe7b3` 使用真实 CLI 连续审批同一有效计划。
第一次成功，第二次返回泛化配置/权限错误；但文件逐字节未变，原审批
仍能被无网络 fixture 消费。根因为排他创建现有 approved 文件抛出
FileExistsError，而非实际配置/权限失败。证据为
`.cache/astra-ux/round2/evidence.json`。

**需求**：重复确认完全匹配的有效审批时幂等成功，使用既有 `approved`
与 `expires_at` 返回结构；不新增 Agent 工具或审批恢复功能。

**最小方案**：在既有计划锁内先拒绝 consumed、再次核对有效期；若
approved 已存在，使用有界安全 JSON 读取，仅当其内容精确匹配当前
计划摘要时返回既有成功结构。不存在时仍排他创建；不重写文件、不续期。
损坏、不匹配、过期、策略变化、下载关闭继续拒绝。

**验收**：真实 CLI 首次/重复审批均成功且文件不变，之后只能下载一次；
异常审批不能被覆盖，审批无 worker/网络副作用，模型入口仍不能审批；
并发计划锁继续生效。到期跨越锁边界时也不返回有效审批成功。

**联合评审**：Astra 与 Sol 均 APPROVE。Sol 明确补充：已有有效审批为
只读文件时也应成功确认；审批不得进入 work()/调用 runner。原记录缺失
才排他创建，异常记录不覆盖，重复成功不产生第二次下载许可。

**实现与验收**：原审批有界读取且摘要精确匹配才确认，缺失才排他创建；
计划锁内增加到期复查。Sol 检查 diff 并独立运行 22 项 service 测试后
ACCEPT。Astra 真实 CLI 两次结果相同，第二次使用 Windows 只读审批文件
仍成功，文件字节、只读属性和期限不变；异常、消费、策略变化、关闭下载
均拒绝，模型不能审批，无 job/网络副作用，结论 PASS。证据为
`.cache/astra-ux/round2/retest-evidence.json`。root 40 项 Python 集成测试通过。

## R3：字幕按支持格式选择人工/自动轨道

**观察**：Astra 在 `c0dc3c2` 用真实 worker/yt-dlp 与确定性提取、HTTP
替身测试，禁止真实 socket/DNS。同一语言人工仅 json3、自动有 vtt 时，
metadata 报告该语言，但字幕读取拒绝；删除人工列表后自动 VTT 可成功。
根因为先按人工列表非空决定来源，再筛选支持格式。证据为
`.cache/astra-ux/round3/evidence.json`。

**需求与方案**：按人工列表、自动列表顺序，选择同一明确语言的第一个
VTT/SRT。只改变选择阶段；选定后仍执行原 URL、字节、文本与数据边界
检查。无支持格式则拒绝；选定轨道被拒绝或失败时不转向自动轨道。
不新增格式转换、转写、语言猜测、工具参数或网络重试。

**验收**：不支持人工 + 支持自动成功且只请求自动一次；两者支持时人工
优先；两者均不支持不请求；选中人工的非法 URL、访问错误、超限失败
不触发自动请求。保留转义、截断与不可信数据封装的既有检查。

**联合评审**：Astra 与 Sol 均 APPROVE。双方确认仅按格式决定候选轨道，
选定后的任何安全拒绝/网络/大小错误均不能触发自动替代请求。

**实现与验收**：生产逻辑仅调整 4 行轨道选择。Sol 检查实际 diff 并
独立运行 13 项 worker 测试后 ACCEPT；Astra 独立复测自动 VTT/SRT、人工
优先、均不支持、非法 URL、模拟 403、超限以及转义/截断，全部 PASS，
请求次数与选定轨道一致。证据为
`.cache/astra-ux/round3/retest-evidence.json`。root 简化了测试中的嵌套
条件和重复 guard 安装，44 项 Python 集成测试通过；本轮不推送。

## R4：配置缺失受控诊断与 MCP 初始化错误边界

**观察**：Astra 在 `25070dd` 使用 CLI、真实 stdio MCP 和 DSH bridge，
指定不存在的隔离配置路径并调用离线计划工具。CLI/DSH 为模糊本地故障，
MCP 把含完整路径的 FileNotFoundError 返回工具正文。根因为 Policy.load
未映射缺失错误，且 MCP Service 构造在 try 之外。证据为
`.cache/astra-ux/round4/evidence.json` 与 `dsh-evidence.json`。

**最小方案**：Policy.load 对明确配置的 FileNotFoundError 映射为固定
受控提示，要求操作者检查 YTAGENT_CONFIG/configPath，不包含实际路径、
原异常或配置内容。MCP 将 Service 构造放入既有 try，初始化的其他失败
也走原有安全错误分支。保留 CLI JSON/非零退出码、MCP isError 与 DSH
错误契约；不新增诊断工具，不回退默认配置，不创建计划/启动 worker。

**验收**：三个真实入口在缺失配置时语义一致，正文不含路径标记/异常
类型/原始内容；修正配置后离线计划恢复；未指定配置默认行为保留。
MCP 的其他初始化异常也不得越出受控边界。测试不进行外网访问。

**联合评审**：Astra 与 Sol 均 APPROVE。Sol 强调不在底层 read_json
全局映射文件错误，保留计划/审批文件的不同含义；验证 MCP 非 Rejected
初始化异常、四工具发现、无 worker/输出副作用。纳入实现与回归。

**实现与验收**：Policy.load 映射缺失文件，MCP 构造放入 try。Sol 检查
diff 并独立运行 35 项相关测试后 ACCEPT。Astra 验证真实 CLI、stdio MCP
与 DSH bridge 缺失诊断一致且不含路径标记，配置修正后同一 MCP 会话
与另外两个入口都恢复离线计划，默认下载关闭、工具仍四个；其他 MCP
初始化异常受控，结论 PASS。证据为
`.cache/astra-ux/round4/retest-evidence.json`。root 实际审阅差异，48 项
Python 测试通过，新的 CLI 用 -I 单独复核通过，5 项 DSH 与资产同步通过。

## R5：操作者独立核对计划限制

**观察**：Astra 在 `1c9e29d` 用真实 CLI 创建下载关闭/1 MiB 和下载开启/
2 MiB 的离线计划。创建结果含 max_bytes/downloads_enabled，show-plan
却均缺失，仅有不可直接阅读的策略摘要；改变策略时旧计划已正确拒绝。
证据为 `.cache/astra-ux/round5/evidence.json`。

**最小方案**：仅在现有 CLI show-plan 分支通过 read_plan 全部校验后，
为返回的计划副本补充 self.policy 对应的 max_bytes 与 downloads_enabled。
保留原字段/JSON/退出码，不修改磁盘计划或 read_plan 的严格字段契约，
不新增 Service 抽象、模型工具、完整状态管理或审批副作用。

**验收**：真实 CLI 在两种策略下显示与创建计划一致的值，文件/期限/
审批不变，无 worker/网络；过期、策略变更、损坏/额外字段继续拒绝。
开启下载的显示不代表已审批，也不赋予重复消费许可，手册明确说明。

**联合评审**：Astra 与 Sol 均 APPROVE。共同确认字段只来自通过策略
摘要匹配的当前策略快照，返回副本保持磁盘、摘要和严格字段验证不变；
下载开关仅表示策略状态，人工审批继续独立执行。

**实现与验收**：CLI 返回副本新增两项已校验策略信息，磁盘契约与工具
不变。Sol 审阅 diff 并独立运行 25 项 service 测试后 ACCEPT。Astra 真实
CLI 验证两种策略数值一致、原字段/期限/已有审批均不变，伪造策略字段、
过期、损坏、策略变化全部拒绝，开启但未审批不能进入工作槽位，结论
PASS。证据为 `.cache/astra-ux/round5/retest-evidence.json`。root 审阅
差异并运行 50 项 Python 集成测试通过；完整发布质量检查另行执行。

## 最终版本与推送门槛

目标版本 v0.2.0；原 v0.1.0 标签不移动。Python 包、uv 锁、两个客户端
清单、DSH 包及 npm 锁的版本一致性由新增回归检查，MCP 握手使用共用
版本常量。依赖版本没有随版本号调整而漂移。

| 本地质量检查 | 当前证据 |
|---|---|
| root 审阅各轮实际差异 | 5 轮均完成，未以代理结论替代实际检查 |
| 新 Sol 独立审阅组合变更 | ACCEPT，无具体 P1/P2 阻断；跨 Service 审批/忙/失败/重放检查通过 |
| Windows 源码与最终 wheel | 各 51 项 Python 通过；最终 wheel 的 5 项 DSH 通过 |
| Linux R4 快照 wheel | 48 项 Python、5 项 DSH 通过；不能替代最终包验收 |
| Linux 最终 v0.2.0 wheel | 51 项 Python、5 项 DSH、依赖一致性通过 |
| 依赖审计 | 哈希锁定 Python 依赖无已知漏洞；npm 全量审计 0 漏洞 |
| Skill、资产、Claude 两份清单、Python 编译 | 通过 |
| 最终包用户验收 | Astra PASS，最终 wheel/DSH 原字节跨入口流程与重放拒绝通过 |
| 源码包/哈希核对 | wheel/源码/DSH 内容与构建源核对通过，排除本地缓存/状态，生成 SHA-256 |

所有本地门槛均已通过后才进行统一推送。WSL 一度报告宿主资源不足；
本项目测试进程结束、可用资源改善后，同目标的一次重试通过最终 Linux
验收，未修改系统配置或关闭用户其他程序。没有再次触发外网站点测试。

**发布验收**：v0.2.0 指向 `d7bd2fa`，主分支
[CI 39812544729](https://github.com/hoshimiii/yt-dlp-agent-kit/actions/runs/39812544729)
与迭代分支
[CI 39812544410](https://github.com/hoshimiii/yt-dlp-agent-kit/actions/runs/39812544410)
的 Windows/Linux 检查全部通过。发布附件重新下载后，与本地已验收的
wheel、源码包、DSH tarball 逐字节一致，SHA-256 一致。原 v0.1.0 保留。
