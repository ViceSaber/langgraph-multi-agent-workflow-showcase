# langgraph_showcase_design.md

## 项目定位

这个项目不是再造一个完整 OpenClaw，也不是做第二套大而全多 Agent 系统。

它的目标是：

**把你在 OpenClaw 中已经验证过的多 Agent 编排经验，提炼成一个更标准、更容易展示、更适合简历与面试表达的 LangGraph showcase。**

核心卖点不是"功能很多"，而是：

- 有状态工作流（stateful workflow）
- 多角色协作（supervisor / worker / reviewer / human approval）
- 条件分支与回退重试
- checkpoint / persistence / resume
- human-in-the-loop
- README 一眼能看懂

---

## 最推荐做的主题

### 主题：Supervisor / Worker / Reviewer / Human Approval 工作流

这是最适合你当前背景的一版。

用户输入一个任务，系统经过：

1. `supervisor`：理解请求，决定执行路线
2. `worker`：生成初稿或执行结果
3. `reviewer`：审查结果质量
4. `human_approval`：支持人工确认
5. `finalize`：输出最终结果

如果 reviewer 不通过，则回退到 worker 修订；如果人工驳回，则回到 supervisor 重新规划。

这版足够小，但能体现你真正有价值的能力：

- 状态设计
- 编排能力
- 审核闭环
- 可恢复执行
- 人工介入

---

## 项目名称建议

建议仓库名不要太空泛。

可选：

- `langgraph-multi-agent-workflow-showcase`
- `langgraph-review-loop-demo`
- `langgraph-supervisor-reviewer-demo`
- `stateful-agent-orchestration-demo`

最推荐：

**`langgraph-multi-agent-workflow-showcase`**

这个名字最稳，简历和 GitHub 上都好解释。

---

## 你应该控制的范围

### 只做 1 条主流程

不要一上来加：

- Telegram Bot
- 多模型 provider 切换
- 复杂额度治理
- 真正的外部任务队列
- watcher / watchdog
- 十几个 agent
- 一堆工具调用

这些东西会把 showcase 重新拖回工程泥潭。

这个项目只需要聚焦：

**"一个多角色、可审查、可中断、可恢复的 LangGraph 工作流"**

### 推荐规模

- 节点数：3 到 5 个
- State：1 个核心状态对象
- Checkpoint：1 套
- Demo 输入：2 到 3 个
- README：完整
- 测试：少量关键测试即可

---

## 推荐目录结构

```text
langgraph-multi-agent-workflow-showcase/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ main.py
├─ demo_inputs/
│  ├─ normal_task.txt
│  ├─ revision_task.txt
│  └─ human_review_task.txt
├─ app/
│  ├─ graph.py
│  ├─ state.py
│  ├─ config.py
│  ├─ prompts.py
│  ├─ checkpoint.py
│  ├─ routing.py
│  ├─ models.py
│  ├─ types.py
│  └─ utils.py
├─ app/nodes/
│  ├─ supervisor.py
│  ├─ worker.py
│  ├─ reviewer.py
│  ├─ human_approval.py
│  ├─ error_handler.py
│  └─ finalize.py
├─ app/tests/
│  ├─ test_routing.py
│  ├─ test_review_loop.py
│  └─ test_state_transitions.py
└─ docs/
   ├─ architecture.md
   ├─ state_machine.md
   └─ sample_run.md
```

这个结构的优点：

- 面试官一看就知道你不是乱写
- 状态、节点、路由分层清楚
- 后续如果要扩展 tool calling、RAG、memory，很自然

---

## 工作流设计

### 1. 核心状态 State

建议不要把 state 设计得太散。

可以先用一个结构化状态：

```python
from typing import Literal, Optional, List, TypedDict

class WorkflowState(TypedDict, total=False):
    task_id: str
    user_request: str
    plan: str
    draft: str
    review_feedback: str
    review_score: float  # 1-10 量化评分，低于阈值触发回退
    final_output: str
    status: Literal[
        "RECEIVED",
        "PLANNED",
        "DRAFTED",
        "REVIEW_PASSED",
        "REVIEW_FAILED",
        "WAITING_HUMAN",
        "APPROVED",
        "REJECTED",
        "FINALIZED",
        "FAILED"
    ]
    revision_count: int
    max_revisions: int
    human_decision: Optional[Literal["approve", "reject"]]
    human_rejection_reason: Optional[str]  # 人工驳回原因，supervisor 重规划时参考
    execution_log: List[dict]  # 每个节点的执行摘要：{node, input_summary, output_summary, duration_ms}
    error_info: Optional[str]  # 节点执行失败时的错误信息
```

### 2. 状态设计原则

你要让状态满足这几个要求：

- 能看出当前走到哪一步
- 能支持 reviewer 驳回回流
- 能支持人工 approve / reject
- 能支持中断恢复
- 能在 README 中画出状态机
- **量化审查指标**：`review_score` 让回退有据可依，而非纯主观判断
- **执行可追溯**：`execution_log` 记录每个节点的输入输出摘要和耗时，方便调试和展示
- **错误可捕获**：`error_info` + `FAILED` 状态，让异常路径也有终态收敛

### 3. 不要一开始就引入太复杂字段

先不要加：

- 多模型成本统计
- 多 worker 并行分支
- agent 心跳
- task ledger 外部数据库 schema

showcase 要的是清晰，不是复杂。

### 4. 关键新增字段说明

| 字段 | 用途 | 为什么需要 |
|---|---|---|
| `review_score` (float) | reviewer 输出 1-10 量化评分 | 比 pass/fail 更细粒度，可设阈值（如 <7 回退），面试能讲"量化退出条件" |
| `human_rejection_reason` (str) | 人工驳回时填写原因 | supervisor 重规划时参考，避免第二轮规划出同样方案 |
| `execution_log` (List[dict]) | 每个节点的 {node, input_summary, output_summary, duration_ms} | 调试 + 展示 + 可观测性，README 里可以贴出来 |
| `error_info` (str) | 节点失败时的错误信息 | 让 FAILED 终态有意义，human approval 可以看到失败原因并决定是否重试 |
| `FAILED` status | 新增终态 | 超过 max_revisions 或 worker/reviewer 执行异常时的兜底状态 |

---

## 节点设计

## `supervisor`

### 职责

- 接收用户请求
- 生成简短执行计划
- 设置初始状态
- 决定进入 worker

### 输入

- `user_request`

### 输出

- `plan`
- `status = "PLANNED"`

### 示例输出

- 提取任务目标
- 说明交付格式
- 明确是否需要 review loop

### 注意点

不要把 supervisor 写成"大模型神脑"。
它只负责：

- 把任务结构化
- 不负责最终产出

---

## `worker`

### 职责

- 基于 `plan` 和 `user_request` 生成 draft
- 执行主要内容生产

### 输入

- `user_request`
- `plan`
- `review_feedback`（如果是返工轮次）

### 输出

- `draft`
- `status = "DRAFTED"`

### 注意点

worker 要支持两种模式：

1. 初次生成
2. 根据 reviewer feedback 修订

这正是面试中能讲出"有闭环"的关键。

---

## `reviewer`

### 职责

- 审查 draft 是否满足质量要求
- 生成审查结论
- 决定通过还是回退

### 输入

- `user_request`
- `plan`
- `draft`

### 输出

- `review_feedback`
- `status = "REVIEW_PASSED"` 或 `"REVIEW_FAILED"`

### 建议输出结构

reviewer 最好输出结构化结果，**包含量化评分**：

```json
{
  "decision": "pass",
  "score": 8,
  "issues": [],
  "summary": "Draft is acceptable and can proceed to human approval."
}
```

或

```json
{
  "decision": "fail",
  "score": 4,
  "issues": [
    "Missing concrete examples",
    "Output format does not match requested structure"
  ],
  "summary": "Revise the draft before finalization."
}
```

### 评分阈值设计

- `score >= 7` → pass
- `score < 7` → fail，触发 revision 回路
- 阈值可在 `config.py` 中配置，方便调参

### 审查维度

reviewer 从以下维度打分并给出反馈：

1. **完整性**（1-10）：是否覆盖了 plan 中的所有要求
2. **格式一致性**（1-10）：输出结构是否符合约定格式
3. **可执行性**（1-10）：内容是否具体可执行，而非泛泛而谈
4. **最终 score** = 三个维度的加权平均（或取最低分，展示时选一种）

### 为什么 reviewer 很关键

因为它能把你的 showcase 从"普通链式调用"升级成"带反馈闭环的 agent workflow"。加上量化评分后，revision 回路有了**可解释的退出条件**，比纯 LLM 主观 pass/fail 更工程化。

---

## `human_approval`

### 职责

- 在 reviewer 通过后暂停执行
- 等待人工 approve / reject
- **reject 时记录原因**，供 supervisor 重规划参考

### 输入

- `draft`
- `review_feedback`
- `review_score`

### 输出

- `human_decision`
- `human_rejection_reason`（仅 reject 时填写）
- `status = "APPROVED"` 或 `"REJECTED"`

### 关键设计：reject 后 supervisor 重规划

当人工 reject 时，`human_rejection_reason` 会写入 state。supervisor 重规划时能看到：

- 原始 user_request
- 上次 plan
- rejection reason

这样 supervisor 能生成**不同的方案**，而不是重复上一次规划。

```python
# supervisor 重规划时的 prompt 注入
f"""
Original request: {state['user_request']}
Previous plan (rejected by human): {state['plan']}
Rejection reason: {state['human_rejection_reason']}

Please create a DIFFERENT approach to fulfill the request.
"""
```

### 价值

这个节点很适合展示 LangGraph 的 human-in-the-loop 能力。

你可以在 README 里写清楚：

- graph 运行到这里会 interrupt
- 人工写入 decision 后再 resume
- reject 时需提供原因，确保重规划不重复

这会非常像真实业务系统，而不是 demo 玩具。

---

## `finalize`

### 职责

- 基于当前最佳 draft 产出 final_output
- 写入终态

### 输出

- `final_output`
- `status = "FINALIZED"`

### 注意点

finalize 不应该承担复杂逻辑。

它只是：

- 封装最终输出
- 做最后格式整理

---

## `error_handler`

### 职责

- 捕获 worker / reviewer 执行异常（LLM 超时、API 报错、格式解析失败等）
- 判断是否可恢复
- 可恢复→回 supervisor 重规划，不可恢复→FAILED 终态

### 输入

- `error_info`
- `revision_count`
- `max_revisions`

### 输出

- 可恢复：清空 `error_info`，`revision_count += 1`，转 supervisor
- 不可恢复：`status = "FAILED"`，保留 `error_info` 供人工查看

### 可恢复 vs 不可恢复的判断标准

- **可恢复**：LLM 超时、rate limit、JSON 解析失败 → 重试有概率成功
- **不可恢复**：prompt injection 检测触发、API key 无效、连续 3 次同类错误 → 需人工介入

### 为什么需要 error_handler

没有错误处理的 agent workflow 在面试中会被追问"如果 API 挂了怎么办"。一个简单的 error_handler + FAILED 终态，就能体现你的**异常路径设计意识**。

---

## 边与路由设计

推荐路由：

```text
START
  ↓
supervisor
  ↓
worker
  ├─ 成功 → reviewer
  └─ 失败 → error_handler

reviewer
  ├─ pass → human_approval
  ├─ fail → worker（revision_count < max）
  └─ fail + 超限 → human_approval（标注"revision 超限，请人工决定"）

human_approval
  ├─ approve → finalize
  └─ reject → supervisor（携带 rejection_reason）

error_handler
  ├─ 可恢复 → supervisor（重规划，计入 revision_count）
  └─ 不可恢复 → FAILED 终态

finalize
  ↓
END
```

### 这条图的价值

它已经覆盖了：

- 正常流转
- reviewer 反馈回路（带量化评分阈值）
- reviewer 超限兜底（转人工决策）
- human rejection 回路（携带原因，避免重复规划）
- 错误处理路径（可恢复→重规划，不可恢复→FAILED）
- 最终 closeout
- FAILED 终态收敛

这已经足够展示你对 orchestration 的理解，而且比纯 happy path 更像真实工程。

---

## 修订次数控制

一定要加一个很简单的保护：

- `revision_count`
- `max_revisions`

规则：

- reviewer fail 一次，`revision_count += 1`
- worker 执行失败走 error_handler 重规划时，`revision_count += 1`
- 如果达到 `max_revisions`，则不再回 worker，直接进入 human_approval（标注"revision 超限，请人工决定是否接受当前 draft 或终止"）
- 人工 reject 后回到 supervisor，也计入 `revision_count`（防止 supervisor 反复产出同样方案）

这点很重要，因为它能体现你有：

- 防死循环意识
- agent workflow 护栏意识
- 量化退出条件

这比单纯"能跑起来"更像工程师作品。

---

## checkpoint / persistence 怎么做

这部分是 LangGraph showcase 的核心加分点之一。

### 最简单做法

**推荐存储后端：SQLite**

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 初始化
checkpointer = SqliteSaver.from_conn_string("./data/checkpoints.db")
```

为什么选 SQLite：
- 零配置，不需要额外服务
- 单文件，方便演示和分发
- LangGraph 官方支持
- 足够 showcase 用途（面试不会追问"为什么不用 Redis"）

原则：

- 每个线程/任务有独立 `thread_id`
- graph 每执行一段就 checkpoint
- 中断后可以 resume
- checkpoints.db 纳入 .gitignore，但 .env.example 里标注路径

### 你在 README 里要强调的点

- graph execution is resumable
- state is persisted between steps
- human approval can happen after interruption
- failed or paused runs can continue from checkpoint

### 面试里的说法

"我没有只做普通链式调用，而是用 LangGraph 的 checkpoint / resumable execution 做成了一个可暂停、可恢复的 stateful workflow。"

这句话会很有力量。

---

## 是否需要数据库

### 建议

**第一版不要自己再手搓完整 SQLite task ledger。**

因为你已经在 OpenClaw 那套里证明过你会做 ledger 了。

这里更应该突出的是：

- LangGraph state
- LangGraph checkpoint
- graph routing
- human interrupt

### 什么时候再补数据库

如果你后续想做 v2，可以再加：

- SQLite run history
- execution logs
- audit trail
- task metadata

但第一版不要急着加。

---

## 模型层设计

### 建议

模型层尽量薄：

- 一个 `models.py`
- 一个统一 `call_llm()` 封装
- 节点里只写 prompt 输入输出

### 为什么

因为这个项目的重点是 orchestration，不是模型接入炫技。

不要把 showcase 变成：

- 支持 8 个 provider
- fallback 3 层
- 各种 token 计费统计

那会喧宾夺主。

---

## 提示词设计建议

### supervisor prompt

目标：

- 提炼用户意图
- 生成简短 plan
- 约束 worker 输出结构

### worker prompt

目标：

- 按 plan 生产可审查 draft
- 如果有 reviewer feedback，则按问题修订

### reviewer prompt

目标：

- 从完整性、格式一致性、可执行性三方面审查
- 输出结构化 decision

### human approval

这里不用 prompt 很复杂。

只要支持：

- approve
- reject
- optional reason

---

## 运行方式建议

### CLI 即可

先不要做 Web UI。

推荐：

```bash
python main.py --input demo_inputs/normal_task.txt
python main.py --input demo_inputs/revision_task.txt
python main.py --resume <thread_id>
```

这就够了。

### 为什么 CLI 更适合第一版

- 简单
- 好调试
- README 容易展示
- 不会被 UI 分散注意力

---

## Demo 场景建议

至少准备 3 个 demo：

### demo 1：正常通过

路径：

`supervisor -> worker -> reviewer(pass, score=8) -> human approve -> finalize`

### demo 2：reviewer 驳回后修订

路径：

`supervisor -> worker -> reviewer(fail, score=4) -> worker(修订) -> reviewer(pass, score=7) -> human approve -> finalize`

### demo 3：人工拒绝后重规划

路径：

`supervisor -> worker -> reviewer(pass) -> human reject(reason="方向不对") -> supervisor(参考 rejection reason 重规划) -> worker -> reviewer(pass) -> human approve -> finalize`

### demo 4：worker 执行失败 + error_handler 恢复

路径：

`supervisor -> worker(超时) -> error_handler(可恢复) -> supervisor(重规划) -> worker -> reviewer(pass) -> human approve -> finalize`

这 4 个 demo 足够说明：

- 条件分支
- 回路（带量化评分阈值）
- interrupt / resume
- 错误恢复路径
- 人工驳回后的差异化重规划
- 状态可追踪（execution_log）

---

## 最该写清楚的 README 结构

你的 README 一定要强。

推荐这样写：

### 1. 项目简介

一句话：

> A LangGraph showcase for stateful multi-agent orchestration with review loops, quantified scoring, error handling, human approval, and resumable execution.

### 2. Why this project

说明它不是聊天机器人，而是：

- stateful workflow
- review loop
- human-in-the-loop
- resumable execution

### 3. Architecture

画图：

```text
User Request
   ↓
Supervisor ←──────────────┐
   ↓                      │
Worker ──(失败)──→ Error Handler ──(可恢复)──┘
   ↓
Reviewer
  ↙     ↘
Revise   Human Approval ←──(超限)
           ↓
        Finalize
          ↓
         END
```

### 4. State schema

说明关键字段：

- task_id
- user_request
- plan
- draft
- review_feedback
- revision_count
- status
- human_decision
- final_output
- review_score
- execution_log
- error_info

### 5. Key features

- LangGraph-based orchestration with supervisor / worker / reviewer / error_handler / human approval
- Structured workflow state with execution log for observability
- Quantified review scoring (1-10) with configurable pass threshold
- Conditional routing: review loop, error recovery, human rejection re-routing
- Human approval interrupt with rejection reason for differentiated re-planning
- Revision limit guardrail to prevent infinite loops
- Error handler with recoverable vs non-recoverable classification
- SQLite-backed checkpoint persistence for resumable execution

### 6. How to run

写清楚安装和命令。

### 7. Sample execution

展示 1 到 2 次运行日志。

### 8. What this demonstrates

强调：

- orchestration thinking
- state machine design
- reliability guardrails
- human oversight

---

## 你在 README 里别乱吹的点

不要写成：

- fully production-ready enterprise framework
- autonomous general multi-agent platform
- scalable distributed AI operating system

太大了，像吹牛。

更好的表述：

- focused showcase
- architecture demo
- workflow orchestration example
- resumable multi-agent pipeline

这会显得专业很多。

---

## 简历里怎么写这段项目

### 项目名称

**LangGraph 多 Agent 有状态工作流 Showcase（个人项目）**

### 项目描述

基于 LangGraph 构建可恢复的多 Agent 工作流样板，围绕 supervisor / worker / reviewer / error_handler / human approval 角色，完成任务拆解、草稿生成、量化审查、错误恢复、人工确认与最终交付闭环，用于展示 stateful agent orchestration、review loop、error handling 与 human-in-the-loop 能力。

### 核心工作（可直接上简历）

- 基于 LangGraph 设计并实现 supervisor / worker / reviewer / error_handler 多角色工作流，支持条件路由、量化审查回退、错误恢复与终态收敛
- 抽象统一工作流状态，覆盖任务计划、草稿、审查评分、执行日志、错误信息与人工决策，提升执行链路可观测性
- 实现 reviewer 量化评分机制（1-10，可配置阈值），使 revision 回路具备可解释的退出条件
- 实现 human approval interrupt 与 checkpoint/resume 机制，使长流程任务支持中断、人工介入与恢复执行；reject 时携带原因确保 supervisor 差异化重规划
- 设计 error_handler 节点区分可恢复/不可恢复错误，结合 revision_count 护栏避免无限重试
- 通过 README、状态机图与 4 组样例运行日志，将多 Agent orchestration 经验沉淀为可展示、可复用的工程化项目样板

### 技术栈

LangGraph / Python / LLM API / State Machine / Workflow Orchestration / Checkpoint Persistence / Error Handling

---

## 面试里怎么讲

你可以这样讲：

"我之前在 OpenClaw 里做过比较重的多 Agent 实战，里面涉及 coordinator、reviewer、状态跟踪、通知和恢复。后来我没有再重复造一套大系统，而是把里面最有代表性的编排问题抽出来，用 LangGraph 做了一个更聚焦的 showcase。这个项目重点不是功能堆砌，而是把 state、routing、量化 review loop、error recovery、human approval 和 resumable execution 讲清楚，也方便团队快速理解我对 agent orchestration 的抽象能力。"

这段话很好，因为它同时体现：

- 你不是只会用现成框架
- 你也不是为了学框架而重复造轮子
- 你知道什么叫"提炼核心问题"

---

## 第一版开发顺序

建议按这个顺序做：

### 第 1 步

搭出最小 State 和 Graph：

- supervisor
- worker
- reviewer
- finalize

先不加 human approval 和 error_handler。

### 第 2 步

加 reviewer fail → worker 回路 + 量化评分（review_score + 阈值）。

### 第 3 步

加 `revision_count` 与 `max_revisions` 护栏 + FAILED 终态。

### 第 4 步

加 `human_approval` interrupt（reject 时记录原因）。

### 第 5 步

加 `error_handler`（可恢复→supervisor，不可恢复→FAILED）。

### 第 6 步

加 checkpoint / resume（SQLite 后端）。

### 第 7 步

补 execution_log 记录。

### 第 8 步

补 README、4 组 sample run、状态机图、architecture.md。

### 第 6 步

补 README、sample run、状态机图。

这个顺序最稳。

---

## 你应该避免的坑

### 坑 1：一开始就做太复杂

会让你重新回到 OpenClaw 那种修修补补的状态。

### 坑 2：把 showcase 做成 provider/router 展示项目

重点会偏掉。

### 坑 3：状态设计过于松散

如果 state 没设计好，整个 LangGraph 项目会显得像普通脚本。

### 坑 4：没有护栏

没有 revision limit、没有终态收敛，面试官会觉得你不够工程化。

### 坑 5：README 太弱

这个项目的价值有一半来自"能不能被快速理解"。README 弱，价值直接打折。

---

## 最终你应该交付成什么样

一个合格版本，应该满足：

- 仓库 1 分钟内能看懂是做什么的
- 架构图清楚
- 有状态机（含 FAILED 终态）
- 有 review loop（带量化评分）
- 有 human approval（reject 携带原因）
- 有 error handler（可恢复/不可恢复）
- 有 checkpoint/resume（SQLite 后端）
- 有 execution_log 可观测性
- 有 4 个 sample runs（正常/修订/人工拒绝/错误恢复）
- 简历里能浓缩成 5 到 6 条亮点

只要做到这些，它就已经是一个很合格的 LangGraph showcase。

---

## 最后的建议

这项目的正确姿势不是：

**"我再搞一个超复杂多 Agent 系统。"**

而是：

**"我把自己已经踩过坑、做过实战的多 Agent 编排经验，提炼成一个更标准、更容易展示的 LangGraph 工程样板。"**

这才是它最值钱的地方。
