# OpenSpec 指南

适用于使用 OpenSpec 进行规格驱动开发的 AI 编码助手的说明。

## TL;DR 快速清单

- 搜索现有工作：`openspec spec list --long`、`openspec list`（全文搜索时仅使用 `rg`）
- 确定范围：新增能力还是修改现有能力
- 选择唯一的 `change-id`：短横线命名法，动词开头（`add-`、`update-`、`remove-`、`refactor-`）
- 搭建脚手架：`proposal.md`、`tasks.md`、`design.md`（仅在需要时），以及受影响能力的规格增量
- 编写增量：使用 `## ADDED|MODIFIED|REMOVED|RENAMED Requirements`；每个需求至少包含一个 `#### Scenario:`
- 验证：运行 `openspec validate [change-id] --strict` 并修复问题
- 请求批准：在提案获批前不要开始实现

## 三阶段工作流

### 第 1 阶段：创建变更
在以下情况需要创建提案：
- 添加功能或特性
- 引入破坏性变更（API、架构）
- 修改架构或模式  
- 优化性能（会改变行为）
- 更新安全模式

触发条件（示例）：
- “帮我创建一个变更提案”
- “帮我规划一个变更”
- “帮我写一个提案”
- “我想创建一个规格提案”
- “我想创建一个规格”

宽松匹配指引：
- 包含以下任一词汇：`proposal`、`change`、`spec`
- 与以下任一动词组合：`create`、`plan`、`make`、`start`、`help`

以下情况可跳过提案：
- Bug 修复（恢复预期行为）
- 拼写、格式、注释
- 依赖更新（非破坏性）
- 配置修改
- 针对既有行为的测试

**流程**
1. 查看 `openspec/project.md`、`openspec list` 和 `openspec list --specs` 以理解当前上下文。
2. 选择一个动词开头且唯一的 `change-id`，并在 `openspec/changes/<id>/` 下搭建 `proposal.md`、`tasks.md`、可选的 `design.md`，以及规格增量。
3. 使用 `## ADDED|MODIFIED|REMOVED Requirements` 编写规格增量，每个需求至少包含一个 `#### Scenario:`.
4. 在分享提案前运行 `openspec validate <id> --strict` 并解决所有问题。

### 第 2 阶段：实现变更
将以下步骤视作 TODO，逐项完成。
1. **阅读 proposal.md** —— 理解要构建的内容
2. **阅读 design.md**（如存在）—— 了解技术决策
3. **阅读 tasks.md** —— 获取实现检查清单
4. **按顺序实现任务** —— 按顺序完成
5. **确认完成度** —— 在更新状态前确保 `tasks.md` 中每项都已完成
6. **更新清单** —— 全部完成后，将每个任务标记为 `- [x]`，以确保与实际一致
7. **审批闸门** —— 在提案审核通过前不要开始实现

### 第 3 阶段：归档变更
部署后创建独立 PR：
- 将 `changes/[name]/` 移动到 `changes/archive/YYYY-MM-DD-[name]/`
- 若能力有变化则更新 `specs/`
- 对仅限工具的变更使用 `openspec archive [change] --skip-specs --yes`
- 运行 `openspec validate --strict` 确认归档后的变更通过检查

## 在执行任何任务之前

**上下文检查清单：**
- [ ] 阅读 `specs/[capability]/spec.md` 中的相关规格
- [ ] 检查 `changes/` 中的待处理变更是否冲突
- [ ] 阅读 `openspec/project.md` 了解约定
- [ ] 运行 `openspec list` 查看在途变更
- [ ] 运行 `openspec list --specs` 查看现有能力

**在创建规格之前：**
- 始终确认该能力是否已存在
- 优先修改现有规格而非重复创建
- 使用 `openspec show [spec]` 查看当前状态
- 若请求含糊不清，在搭建脚手架前先提出 1–2 个澄清问题

### 搜索指引
- 枚举规格：`openspec spec list --long`（脚本可用 `--json`）
- 枚举变更：`openspec list`（或 `openspec change list --json` —— 已弃用但仍可用）
- 查看详情：
  - 规格：`openspec show <spec-id> --type spec`（使用 `--json` 做筛选）
  - 变更：`openspec show <change-id> --json --deltas-only`
- 全文搜索（使用 ripgrep）：`rg -n "Requirement:|Scenario:" openspec/specs`

## 快速开始

### CLI 命令

```bash
# 核心命令
openspec list                  # 列出在途变更
openspec list --specs          # 列出所有规格
openspec show [item]           # 展示变更或规格
openspec diff [change]         # 展示规格差异
openspec validate [item]       # 验证变更或规格
openspec archive [change] [--yes|-y]      # 部署后归档（非交互式运行时加 --yes）

# 项目管理
openspec init [path]           # 初始化 OpenSpec
openspec update [path]         # 更新说明文件

# 交互模式
openspec show                  # 交互式选择
openspec validate              # 批量验证模式

# 调试
openspec show [change] --json --deltas-only
openspec validate [change] --strict
```

### 命令参数

- `--json` —— 机器可读输出
- `--type change|spec` —— 指定类型以避免歧义
- `--strict` —— 全量严格校验
- `--no-interactive` —— 禁用交互提示
- `--skip-specs` —— 归档时跳过规格更新
- `--yes`/`-y` —— 跳过确认提示（非交互式归档）

## 目录结构

```
openspec/
├── project.md              # 项目约定
├── specs/                  # 真实状态 —— 已构建内容
│   └── [capability]/       # 单一聚焦的能力
│       ├── spec.md         # 需求与场景
│       └── design.md       # 技术模式
├── changes/                # 提案 —— 计划变更
│   ├── [change-name]/
│   │   ├── proposal.md     # 原因、内容、影响
│   │   ├── tasks.md        # 实现检查清单
│   │   ├── design.md       # 技术决策（可选；见标准）
│   │   └── specs/          # 规格增量
│   │       └── [capability]/
│   │           └── spec.md # ADDED/MODIFIED/REMOVED
│   └── archive/            # 已完成变更
```

## 创建变更提案

### 决策树

```
新的请求？
├─ 修复 Bug 以恢复规格行为？ → 直接修复
├─ 拼写/格式/注释？ → 直接修复  
├─ 新功能/新能力？ → 创建提案
├─ 破坏性变更？ → 创建提案
├─ 架构变更？ → 创建提案
└─ 不确定？ → 创建提案（更安全）
```

### 提案结构

1. **创建目录：** `changes/[change-id]/`（短横线命名、动词开头、唯一）

2. **编写 proposal.md：**
```markdown
## Why
[1-2 句描述问题或机会]

## What Changes
- [变更列表]
- [将破坏性变更用 **BREAKING** 标注]

## Impact
- 受影响的规格：[能力列表]
- 受影响的代码：[关键文件/系统]
```

3. **创建规格增量：** `specs/[capability]/spec.md`
```markdown
## ADDED Requirements
### Requirement: New Feature
系统必须提供...

#### Scenario: Success case
- **WHEN** 用户执行操作
- **THEN** 预期结果

## MODIFIED Requirements
### Requirement: Existing Feature
[完整的已修改需求]

## REMOVED Requirements
### Requirement: Old Feature
**Reason**: [移除原因]
**Migration**: [迁移方式]
```
若影响多个能力，则在 `changes/[change-id]/specs/<capability>/spec.md` 下分别创建多个增量文件——每个能力一个。

4. **创建 tasks.md：**
```markdown
## 1. Implementation
- [ ] 1.1 创建数据库结构
- [ ] 1.2 实现 API 端点
- [ ] 1.3 添加前端组件
- [ ] 1.4 编写测试
```

5. **在需要时创建 design.md：**
满足以下任一情况则创建 `design.md`，否则省略：
- 跨多个服务/模块的变更或新的架构模式
- 新的外部依赖或重要的数据模型变更
- 涉及安全、性能或迁移复杂度
- 在编码前需要技术决策以化解不确定性

最简 `design.md` 模板：
```markdown
## Context
[背景、约束、干系人]

## Goals / Non-Goals
- Goals: [...]
- Non-Goals: [...]

## Decisions
- 决策：[内容与原因]
- 备选方案：[选项 + 理由]

## Risks / Trade-offs
- [风险] → 缓解措施

## Migration Plan
[步骤、回滚方案]

## Open Questions
- [...]
```

## 规格文件格式

### 关键：场景格式

**正确**（使用 #### 作为标题）：
```markdown
#### Scenario: User login success
- **WHEN** valid credentials provided
- **THEN** return JWT token
```

**错误**（不要使用项目符号或加粗）：
```markdown
- **Scenario: User login**  ❌
**Scenario**: User login     ❌
### Scenario: User login      ❌
```

每个需求必须至少包含一个场景。

### 需求措辞
- 使用 SHALL/MUST 表达强制性需求（除非有意使用 should/may 表示非强制性）

### 增量操作

- `## ADDED Requirements` —— 新增能力
- `## MODIFIED Requirements` —— 修改行为
- `## REMOVED Requirements` —— 移除功能
- `## RENAMED Requirements` —— 重命名

标题匹配基于 `trim(header)` —— 忽略空白。

#### 何时使用 ADDED 与 MODIFIED
- ADDED：引入可独立存在的新能力或子能力。若变更是正交的（例如新增“命令面板配置”），优先使用 ADDED，而不是改动现有需求语义。
- MODIFIED：更改现有需求的行为、范围或验收标准。始终粘贴完整的更新后需求内容（标题 + 所有场景）。归档时，工具会用你提供的内容替换整个需求；部分增量会导致旧信息丢失。
- RENAMED：仅修改名称时使用。若同时修改行为，需在 RENAMED（名称）之外，针对新名称再添加 MODIFIED（内容）。

常见陷阱：使用 MODIFIED 添加新关注点但未包含原始文本，这会在归档时造成信息丢失。如果并未明确修改现有需求，应在 ADDED 下新增一个需求。

正确编写 MODIFIED 需求的步骤：
1) 在 `openspec/specs/<capability>/spec.md` 中定位现有需求。
2) 将整个需求块（从 `### Requirement: ...` 到所有场景）复制下来。
3) 粘贴到 `## MODIFIED Requirements` 下并编辑以反映新行为。
4) 确保标题文本完全匹配（忽略空白），并至少保留一个 `#### Scenario:`。

RENAMED 示例：
```markdown
## RENAMED Requirements
- FROM: `### Requirement: Login`
- TO: `### Requirement: User Authentication`
```

## 故障排查

### 常见错误

**“Change must have at least one delta”**
- 检查 `changes/[name]/specs/` 下是否存在 .md 文件
- 确认文件中包含操作前缀（## ADDED Requirements）

**“Requirement must have at least one scenario”**
- 确保场景使用 `#### Scenario:` 格式（4 个井号）
- 不要使用项目符号或加粗形式表示场景标题

**场景解析静默失败**
- 必须严格遵守 `#### Scenario: Name` 格式
- 使用 `openspec show [change] --json --deltas-only` 进行调试

### 验证技巧

```bash
# 始终使用严格模式进行全面检查
openspec validate [change] --strict

# 调试增量解析
openspec show [change] --json | jq '.deltas'

# 检查特定需求
openspec show [spec] --json -r 1
```

## 快乐路径脚本

```bash
# 1) 探索当前状态
openspec spec list --long
openspec list
# 可选全文搜索：
# rg -n "Requirement:|Scenario:" openspec/specs
# rg -n "^#|Requirement:" openspec/changes

# 2) 选择变更 ID 并搭建脚手架
CHANGE=add-two-factor-auth
mkdir -p openspec/changes/$CHANGE/{specs/auth}
printf "## Why\n...\n\n## What Changes\n- ...\n\n## Impact\n- ...\n" > openspec/changes/$CHANGE/proposal.md
printf "## 1. Implementation\n- [ ] 1.1 ...\n" > openspec/changes/$CHANGE/tasks.md

# 3) 添加增量（示例）
cat > openspec/changes/$CHANGE/specs/auth/spec.md << 'EOF'
## ADDED Requirements
### Requirement: Two-Factor Authentication
Users MUST provide a second factor during login.

#### Scenario: OTP required
- **WHEN** valid credentials are provided
- **THEN** an OTP challenge is required
EOF

# 4) 验证
openspec validate $CHANGE --strict
```

## 多能力示例

```
openspec/changes/add-2fa-notify/
├── proposal.md
├── tasks.md
└── specs/
    ├── auth/
    │   └── spec.md   # ADDED: Two-Factor Authentication
    └── notifications/
        └── spec.md   # ADDED: OTP email notification
```

auth/spec.md
```markdown
## ADDED Requirements
### Requirement: Two-Factor Authentication
...
```

notifications/spec.md
```markdown
## ADDED Requirements
### Requirement: OTP Email Notification
...
```

## 最佳实践

### 简单优先
- 默认新增代码 <100 行
- 在被证明不足之前，采用单文件实现
- 无明确理由时避免引入框架
- 选择朴素且经过验证的模式

### 复杂度触发条件
仅在出现以下情况时引入复杂度：
- 有性能数据证明当前方案过慢
- 有明确规模需求（>1000 用户、>100MB 数据）
- 存在多个经过验证的用例需要抽象

### 明确引用
- 代码位置使用 `file.ts:42` 格式
- 规格引用使用 `specs/auth/spec.md`
- 链接相关变更和 PR

### 能力命名
- 使用动词-名词组合：`user-auth`、`payment-capture`
- 每个能力仅聚焦一个目的
- 遵循“10 分钟理解”原则
- 若描述需要出现 “AND”，则拆分能力

### 变更 ID 命名
- 使用简短且描述性的短横线命名：`add-two-factor-auth`
- 优先使用动词前缀：`add-`、`update-`、`remove-`、`refactor-`
- 确保唯一；如已被占用，追加 `-2`、`-3` 等

## 工具选择指南

| 任务 | 工具 | 原因 |
|------|------|-----|
| 按模式查找文件 | Glob | 快速模式匹配 |
| 搜索代码内容 | Grep | 优化的正则搜索 |
| 阅读特定文件 | Read | 直接访问文件 |
| 探索未知范围 | Task | 多步骤调查 |

## 错误恢复

### 变更冲突
1. 运行 `openspec list` 查看在途变更
2. 检查是否存在规格重叠
3. 与变更负责人沟通
4. 考虑合并提案

### 验证失败
1. 使用 `--strict` 参数运行
2. 查看 JSON 输出获取详情
3. 确认规格文件格式
4. 确保场景格式正确

### 缺失上下文
1. 优先阅读 project.md
2. 检查相关规格
3. 查阅近期归档
4. 及时寻求澄清

## 快速参考

### 阶段指示
- `changes/` —— 提案，尚未构建
- `specs/` —— 已构建并部署
- `archive/` —— 已完成的变更

### 文件用途
- `proposal.md` —— 原因与内容
- `tasks.md` —— 实现步骤
- `design.md` —— 技术决策
- `spec.md` —— 需求与行为

### CLI 速查
```bash
openspec list              # 正在进行的有哪些？
openspec show [item]       # 查看详情
openspec diff [change]     # 有哪些差异？
openspec validate --strict # 是否正确？
openspec archive [change] [--yes|-y]  # 标记完成（自动化时加 --yes）
```

请记住：规格是真相。变更是提案。保持两者同步。
