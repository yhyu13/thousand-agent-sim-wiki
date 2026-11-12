# 08 · 技术底座：游戏人群、语言模型、MCP 与技能

> 结论先行：千人系统以前的游戏就做过，差的不是人数，是**决策从人手写的规则变成了会出错的语言模型**。现在的底座不是「一千个 MCP」，而是三层：确定性世界（本仓库 demo 已有）、少量被激活的语言模型（[01](01-landscape.md) 的焦点激活）、以及一个宿主把窄工具和窄技能接进来。规范里没有「父 skill」这种类型；专家团是编排方式，不是协议功能。本页 2026-11-12 起直抓原文，2026-11-13 补了 Liquibase、Alembic、Django 6.1 与 Rails 迁移指南。没打开的厂商页仍然不写成已核验。

## §1 电子游戏里的千人，和现在差在哪

Park 等人把自己的沙盒直接放在游戏谱系里：图注写的是 “reminiscent of The Sims”，摘要写 “inspired by The Sims”，25 个代理 [S01]。他们点明旧做法的成本：「traditional game environments would require scripting tens of characters' behavior manually」——情人节派对如果用传统游戏环境，得手工脚本几十个角色；生成式代理只给一个人一个种子意图 [S01]。

同一篇的相关工作把「过去四十年的可信代理」说清楚了，不是本 wiki 的转述：

- 规则路线：有限状态机和行为树是 “the brute force approach of human-authoring the agent's behavior”，而且 “still the most dominant approach today”；《质量效应》和《模拟人生》系列被点名为用这套规则做初级社交 [S01]。
- 作者自己的界限：手工行为 “cannot perform new procedures that were not hard-coded in their script”；开放世界里把交互的全部后果写全是 “untenable” [S01]。
- 学习路线：强化学习在《星际争霸》（AlphaStar）和 Dota 2（OpenAI Five）上超人类，但成功集中在 “adversarial games with readily definable rewards”，还没有解决开放世界里的可信代理 [S01]。
- 认知架构（SOAR、ICARUS）有短时/长时记忆和感知-规划-行动循环，但动作空间仍是手工过程，不能自己长出新行为 [S01]。

所以「千人」本身不是新的。本仓库的千人小镇就是游戏底座：1000 居民、街上最多 360 个行走代理、作息是种子纯函数、运行时零 LLM [S16]。它和 OASIS / AgentSociety 的差别已经写在 [01 §2](01-landscape.md)。

现在多出来的是决策程序：语言模型按自然语言记忆流生成行为，因此会检索失败、给记忆添油加醋、说话过度正式——这是论文自己列出的三种主要错误，不是本页的推测 [S01]。游戏规则写错是作者的 bug；语言模型写错是每一步都可能发生的采样。军规（校验、回滚、存档拒绝 NaN）是为第二种错误准备的，见 [03-stability.md](03-stability.md)。

行为树本身有一本 2017 年的导论可以核对，不必再等游戏网站 [S33]。Colledanchise 与 Ögren 写：行为树是在游戏业里为 NPC 的模块化长出来的；有限状态机的转移是单向跳转，要反应快就得加很多转移，加多了就难维护。行为树是有根的有向树，根按固定频率向下发 tick，子节点回 Running、Success 或 Failure。控制节点是 Sequence、Fallback、Parallel、Decorator，叶子是 Action 和 Condition。他们用吃豆人演示：先只管吃豆，再在「鬼靠近」时接上躲避，再在「鬼被吓到」时接上追击，旧树不用重接。这仍是人手写的切换结构。它解决的是规则怎么拼，不解决「没写过的手续从哪来」[S01][S33]。

## §2 过去、现在、以及不假装知道的未来

**过去（已核验的文献口径）。** 决策是编译好的策略：状态机、行为树、手工认知架构 [S01]。世界可以很大，行为的新颖性不超过作者写过的过程。

**现在（两篇 2024–2025 的规范，加上本 wiki 已有的模拟层）。** Anthropic 2024-12-19 把系统分成两类：workflow 是「LLM 和工具按预先写好的代码路径编排」；agent 是「LLM 动态决定自己的过程和工具」[S30]。他们把基本积木叫做 augmented LLM：检索、工具、记忆。文中把 MCP 当作接第三方工具的一种客户端实现，不是唯一实现 [S30]。

同一页在 2026 年的版头自己加了注：文中描述的工具景观 “has changed since December 2024”，并指向 Managed Agents 文档 [S30]。所以「现在的框架清单」会过期；过期的是产品名，不是 workflow / agent 这个分法本身。本页不把 2024 年列出的 Rivet、Vellum 当成 2026 年的推荐清单。

MCP 规范 2025-06-18 规定的是另一层：宿主、客户端、服务器 [S28]。

- 服务器向客户端提供三类东西：Resources（上下文和数据）、Prompts（给用户的模板）、Tools（给模型执行的函数）[S28]。
- 一个宿主可以有多个客户端；每个客户端与一个服务器是 1:1 的有状态会话 [S28]。
- 服务器之间应当隔离：服务器 “should not be able to read the whole conversation, nor see into other servers”；跨服务器的交互由宿主控制 [S28]。
- 服务器应当好组合：每个服务器只做一块窄能力，多个服务器由共享协议拼起来 [S28]。
- 工具是任意代码执行，描述文字默认不可信；宿主在调用前要征得用户同意 [S28]。

**2026-04 的托管运行时（已核验，不是预测）。** Anthropic 2026-04-08 的 Managed Agents 把长期运行的代理拆成三个可替换接口：session（发生过的一切的只追加日志）、harness（调用模型并把工具调用路由出去的循环）、sandbox（跑代码、改文件的执行环境）[S32]。他们把「脑」（模型和 harness）和「手」（sandbox 与工具）以及 session 拆开。手的统一形状是 `execute(name, input) → string`，任何自定义工具和任何 MCP 服务器都走这个形状；凭证放在 sandbox 外面的保险库，MCP 经会话代理去取，harness 本身看不到凭证 [S32]。

这和通宵模拟是同一类问题，不是同一套产品：容器死了，harness 收到的是一次工具错误，可以用 `provision({resources})` 换一只新的手；harness 自己死了，因为日志在外面，新的 harness 用 `wake(sessionId)` 从最后一条事件续上 [S32]。本仓库的检查点是模拟世界的 session，不是这家托管服务。文中给出的延迟数字只属于他们自己的改造：p50 首 token 大约降 60%，p95 降超过 90% [S32]。不要把这个百分比套到千人小镇上。

他们明确不假定脑和手的数量或位置 [S32]。所以「未来底座」如果要有一个已发表的说法，就是接口稳定、实现可换，而不是再发明一种居民运行时。MCP 规范里的向后兼容 [S28] 和技能的按需加载 [S29] 是同一方向上的约束，不是另一层产品。

**跨会话不崩（2025-11-26，编码代理，不是居民模拟）。** 另一篇把「每次新会话都失忆」写成长期运行的核心困难 [S34]。没有外置工件时，失败有两种：一次做太多，上下文在半截功能处耗尽，下一班只能猜；或者后一班看见已经有进度，就宣布整个项目做完。他们的对策是两段提示、同一套工具：第一班写 `init.sh`、进度文件、初始 git 提交，以及一份功能清单，每条先标失败；以后每班只做一条，结束时提交并写进度。功能清单用 JSON，因为模型比改 Markdown 更不容易整文件覆盖；指示写明不许删测试，只许改 `passes` 字段。开班先读进度和 git 日志，先跑一遍基本端到端测试，坏了先修，再做新功能。文中的端到端测试走的是 Puppeteer MCP [S34]。

脚注写明：所谓两个代理，只是第一句用户提示不同；系统提示、工具和 harness 相同 [S34]。文末把「一个通用代理，还是测试、质检、清理各用一个专门代理」留成未决问题，并且说这套演示是为全栈网页优化的，科研和金融只是以后也许能搬过去的方向 [S34]。所以专家团仍然不是已被这篇证明的必要结构。对本仓库，对应物是检查点、早晨报告和「不许删回归测试」，不是再雇一千个会话。

## §3 大量代理要的 MCP 和 skill，不是人均一套

千人居民是模拟实体，不是一千个 MCP 服务器。规范里的服务器是窄的、互相看不见对话的 [S28]。2026-04 的托管运行时把这一点说成「多只手」：每只手都是 `execute(name, input) → string`，MCP 服务器只是其中一种手，脑可以把手交给另一个脑，但凭证不进 sandbox [S32]。若给每个居民起一个服务器，就违反「服务器应聚焦、由宿主编排」这条设计原则，也会把同意和隔离做成一千份 [S28]。

和本仓库对齐的切法（**建议，待评审**，不是规范条款）：

| 层 | 谁来做 | 要不要 MCP / skill |
| --- | --- | --- |
| 世界时钟、种子作息、焦点抽样 | 确定性代码（demo 已有） | 不要。这是 workflow 的代码路径 [S30] |
| 被激活的社交 / 反思 / 对象补丁 | 少量 LLM 调用 | 要技能：规定输出必须是可校验补丁，失败就回滚 |
| 检查点、账本、内容闸门 | 窄服务器 | 可以是 MCP tools。模型只能调用已声明的函数 [S28] |
| 通宵操作员（看早晨报告、决定续跑） | 一个宿主 | 技能是操作规程，不是居民人设 |

技能规范把加载分成三档，这是规模上真正的约束 [S29]：

- 元数据（name + description）启动时全加载，约 100 tokens。
- 正文在技能被选中后加载，建议少于 5000 tokens，SKILL.md 少于 500 行。
- `scripts/`、`references/`、`assets/` 只在用到时读。文件引用从 SKILL.md 算只宜一层，避免深链 [S29]。

因此「一千个居民技能」在启动时就会把元数据打满。居民差异应放在世界状态和记忆流里 [S01]，技能只保留操作员和少数认知动作的规程。

`allowed-tools` 字段是实验性的，各实现支持不一致 [S29]。不要把它当成已冻结的权限系统。

## §4 父 skill 和子 skill：规范没有这个类型

Agent Skills 规范定义的是一个目录加一份 SKILL.md，可选脚本和参考文件 [S29]。它没有父技能、子技能或专家团对象。

能组合，靠的是两条已写明的机制，外加一条编排模式：

1. **一个技能内部的参考文件。** 大规程把细节放进 `references/`，正文写清何时去读。这是渐进披露，不是子代理 [S29]。
2. **多个技能并列。** 最佳实践把技能比作函数：要覆盖一块完整工作，以便和其他技能组合。太窄，一个任务得加载好几个技能，指令会冲突；太宽，又无法精确触发 [S29]。
3. **编排器-工人。** 中心 LLM 临时拆任务、交给工人 LLM、再合成。Anthropic 写明这适合「事先不知道要改哪些文件」的工作，和「子任务预先写死」的并行不同 [S30]。专家团如果要做，形态是这个 workflow，主持人是宿主，不是一个会看见所有服务器内部状态的超级技能 [S28][S30]。

本仓库的 critic 循环更接近同一篇文章里的 evaluator-optimizer：一个产生、一个按明确标准打回 [S30]。那是研究流程，不是千人模拟里的居民社会。

**建议的切法（待评审）：** 一个路由技能，正文是一张表——什么信号去读哪一份一层引用，或让宿主启用哪一个并列技能。不要做「父技能再引用子技能、子技能再引用孙技能」的链，规范明确不鼓励深链 [S29]。居民人设继续放在模拟状态里。仓库里的两份演示是并列的：`demos/skills/overnight-operator` 只负责换班勾选，正文只读自己的 `references/grade.md`；`demos/skills/hash-guard` 只核对默认同种子哈希，没有下一层文件。两份正文互不读取对方的文件。

2026-03-24 的长时应用 harness 把「要不要拆人」说得更具体，也更会过期 [S35]。作者 Prithvi Rajasekaran 用了规划、生成、评判三个角色。评判者用 Playwright MCP 去点正在跑的应用；开做之前双方用文件谈一份 sprint 合同。同一句复古游戏编辑器提示，单代理跑了 20 分钟、花费 $9，完整 harness 跑了 6 小时、花费 $200。后一个数字音频工作站例子，表上合计 3 小时 50 分、$124.70。Sprint 3 单独就有 27 条验收。他同时写明：代理给自己的作业打分时会把明显的差评说成没事；把评判拆出去比让生成者批评自己更容易调。另一件会过期的脚手架是上下文重置：Sonnet 4.5 会在觉得窗口快满时提前收工（文中称 context anxiety），压缩摘要留在原会话里治不好这个，所以当时要清空窗口并交出接班记录；Opus 4.5 基本不再这样，他就把重置从 harness 里拿掉。Opus 4.6 之后他又去掉按 sprint 拆分，评判只在任务超出模型自己能稳定做完的范围时才值得花钱。所以三个角色不是千人小镇的必选项。模型一换，就该拆掉不再承重的架子 [S35]。

再早一个月，另一篇把「并行专家」做到了 16 个编码代理，而且明确没有编排器 [S36]。Nicholas Carlini，2026-02-05：16 个 Claude 实例各在自己的容器里克隆同一份 git 仓库，做完再推回上游。抢任务靠在 `current_tasks/` 写一个锁文件；两个人抢同一个任务时，git 同步会逼第二个换任务。他写明：没有别的通信方式，也没有一个编排代理。角色是事后加上的，例如专人并重复代码、专人看编译出的代码效不效率、专人写文档。

这套东西的账单和成绩都很大，但不能当成小镇的成本：将近 2000 次 Claude Code 会话、约两周、输入 20 亿 token、输出 1.4 亿 token、API 花费不到 $20,000，产出约 10 万行 Rust，能编 Linux 6.9 的 x86、ARM 和 RISC-V [S36]。测试套到 99% 以后，编内核仍会卡死：内核是一件大事，16 个代理撞上同一个 bug，改完互相覆盖。解决办法是拿 GCC 当已知正确的对照，让每个代理只重编不同的文件。测试若不准，代理会把错误问题做完。日志不能刷几千字节进上下文；还要有 `--fast`，只跑 1% 或 10% 的确定抽样，否则它会把几小时耗在测试上 [S36]。

16 个编码代理加 git 锁，仍然不是 1000 个居民。居民社会要的是焦点激活和确定性世界，见 [01-landscape.md](01-landscape.md)。$20,000 这笔同样不要加进千人一夜的公式，见 [04-roi.md](04-roi.md)。

仓库 README 不能把博客的数字再证实一遍，反而多了一层不可靠 [S36]。`anthropics/claudes-c-compiler` 的 README 没有写 16 个代理，也没有写 $20,000。人类只写了一段：除此以外，仓库里的代码和文档都是 Claude Opus 4.6 写的；人写过测试，但没有交互式结对调试；「I do not recommend you use this code! None of it has been validated for correctness」；「The docs may be wrong and make claims that are false」。因此 README 里「默认可单独产出 ELF、可当 GCC 替代、PostgreSQL 237 项回归全过」这些句子，不能当成已核验能力。博客则说演示视频仍用 GCC 的汇编器和链接器，16 位实模式会调用 GCC。两处不一致时，代理数和花费以博客为准，仓库能力先停在人类那句警告上。本轮没有编译这个仓库。

## §5 迁移系统的工具长什么样

这里的「迁移」有两件不同的事，不要合成一个产品。

**状态迁移。** 把一份旧检查点或旧库表变成新形状。技能最佳实践把这种操作当成脆弱序列，例子是原样执行 `python scripts/migrate.py --verify --backup`，并写明不要改命令、不要加旗标 [S29]。工具本身是带校验的脚本；技能只负责让代理不要临场发挥。本仓库已有的 `schema_version` 就是这种迁移的模拟侧版本号，见 [02-architecture.md](02-architecture.md)。

**规程迁移。** 把跑通一次的做法收成技能：从真实任务里抽出步骤和被纠正过的地方，或从运行手册、事故记录、补丁历史里综合，而不是让模型凭空写一份「最佳实践」[S29]。本 wiki 的 01–07 就是这种原材料；08 不把它们自动收成技能文件。

商业迁移器的形状，以 Flyway 文档为准（上一轮入门 URL 404，这一轮改抓概念页）[S31]：迁移是放进版本库的增量脚本，记录表结构和数据的变化；同一批脚本按同一顺序在每个环境执行。Migrate 扫描文件，和库里已经应用过的迁移比较，有差距才补上，因此重复执行是幂等的。schema history 表记下何时、由谁应用。默认每份脚本包在一个事务里；数据库报错就标失败，并在可能时自动回滚。

同一形状在另外两份官方页上重复出现，不是 Flyway 一家的说法。

Liquibase Secure 5.1 的 changeset 页（Last updated: August 12, 2026）把 changeset 叫做基本变更单元，全部放在 Changelog 里。一条由 author、id 和 changelog 文件路径唯一标识；id 只是标识，不决定执行顺序，也不必是整数。建议一条只做一种变更，免得半截自动提交把库留在意料之外的状态。默认整条放进一个事务。已经跑过的不再跑，除非标明 runAlways 或 runOnChange。格式可以是 SQL、XML、YAML 或 JSON [S37]。导航里还能看到别的文档版本；本页只核过这一份 Secure 5.1。

Alembic 1.20.1 教程把迁移写成随应用源码一起维护的脚本目录。`versions/` 里的文件不用递增整数，顺序写在脚本自己的 `down_revision` 上。每份脚本有 `upgrade()` 和 `downgrade()`。`alembic upgrade head` 会先看库里有没有 `alembic_version` 表，没有就建；再从表里读当前版本，算出到目标版本的路径，按文件调用 `upgrade()`。教程里的日志写着 “Will assume transactional DDL”。`downgrade base` 则按 `downgrade()` 退回起点 [S38]。

Django 6.1 的迁移主题页不能并进上一句。原文把迁移定义成把模型改动传播进数据库 schema，并把它比作 schema 的版本控制：makemigrations 打成迁移文件（analogous to commits），migrate 应用到库。文件放在各应用的 “migrations” 目录里，随代码提交。事务不是每种库都有：支持 DDL 事务的只有 SQLite 和 PostgreSQL，默认全部操作放进一个事务；MySQL 和 Oracle 不支持，操作不包事务。MySQL 上 schema 变更没有事务，失败了要手工拆开再试，“it’s impossible to roll back to an earlier point.” 文件名里的数字只给人看，顺序靠文件里的 dependencies。回退是再跑 `migrate books 0002`，或 `migrate books zero`；不可逆操作抛 `IrreversibleError`。`--fake-initial` 只在初始迁移、表已经存在时把那份迁移标成已经应用，不是「扫描历史表、跳过一切已跑过的脚本」。压扁迁移时页上出现 “Django’s migrations table”，但没有写出表名，也没有 Flyway 那种比对后补齐的步骤 [S39]。

Rails 当前迁移指南更接近前三家，但仍不能整句搬过去。示例类写成 `ActiveRecord::Migration[8.1]`，文中 API 链到 v8.1.4.1；版本选择器里的 Edge、8.0、7.2 等旧版页没有另开。文件放在 `db/migrate`，名字带 UTC 时间戳，顺序靠这个时间戳，不靠 Django 的 dependencies。`db:migrate` 只跑还没跑过的 `change` 或 `up`。跑完往 `schema_migrations` 的 `version` 列插入版本号。已经跑过的文件再改、再 migrate，指南写 “Rails thinks it has already run the migration and so will do nothing”。事务没有点名数据库：支持 DDL 事务的库里，每份迁移包在一个事务里；不支持的库，失败后已经成功的部分不会退回，“You will have to rollback the changes manually.” `disable_ddl_transaction!` 可以关掉这层自动事务。`change_column` 被写成 irreversible；down 里可以抛 `ActiveRecord::IrreversibleMigration`。指南同时有两句：数据库仍是真相来源；`db/schema.rb` 或 `db/structure.sql` 是重建那份库的权威快照。两句都留着，不并成一句。正文没有 MCP、skill 或专家团 [S40]。

这些工具有没有 MCP、skill、专家团？分开答：

- **MCP：** 规范只规定服务器可以暴露 tools [S28]。Flyway 概念页、Liquibase 这份 changeset 页、Alembic 1.20.1 教程全文、Django 6.1 迁移主题页正文，以及 Rails 当前迁移指南正文，都没有 MCP、skill 或专家团 [S31][S37][S38][S39][S40]。所以「官方文档自带 MCP」在这五页上不成立。Django 页脚赞助广告写着 “Seer an AI agent for debugging”，那不是迁移步骤。有人另写一个服务器去调用它们，那是包装，不是产品本身。没打开的厂商页仍然不外推。
- **Skill：** 有，但是技能规范里的写法，不是 Flyway 的插件名。脆弱迁移被写成不可改旗标的固定命令 [S29]。Flyway 自己的门是另一套：出错回滚、部署前可以做 dry run 和漂移检查 [S31]。
- **专家团：** 迁移脚本不需要专家团。需要的是「能不能执行」——先比对已应用的版本，再按序补齐。那是脚本和历史表，不是一组互相看不见的服务器在讨论 [S28][S30][S31][S37][S38][S40]。Django 6.1 这篇正文同样没有描述专家团 [S39]。上一句的「先比对再补齐」覆盖 Flyway、Liquibase、Alembic 和 Rails，不套到 Django。

## §6 本轮边界

- 直抓成功：MCP 规范 2025-06-18 [S28]；Agent Skills [S29]；《Building effective agents》[S30]；Managed Agents（2026-04-08）[S32]；长期运行 harness（2025-11-26）[S34]；长时应用 harness（2026-03-24）[S35]；16 代理并行写编译器（2026-02-05）[S36]；行为树导论 arXiv:1709.00084 [S33]；Generative Agents HTML [S01]；Flyway 概念页 [S31]；Liquibase Secure 5.1 changeset 页 [S37]；Alembic 1.20.1 教程 [S38]；Django 6.1 迁移主题页 [S39]；Rails 当前迁移指南 [S40]。
- `www.gamedeveloper.com` 与英文维基行为树页仍打不开。行为树的定义改以 [S33] 为准，不再等那两个站。
- demo 代码、测试计数、哈希均未改。

## 参见

- [01-landscape.md](01-landscape.md) §2 两条千人路线
- [02-architecture.md](02-architecture.md) 世界层 / 认知层怎么拼
- [03-stability.md](03-stability.md) 语言模型会写坏时怎么停
- [05-overnight-runbook.md](05-overnight-runbook.md) §7 把跨会话规矩写成操作员换班，不假装 demo 已有进度文件
