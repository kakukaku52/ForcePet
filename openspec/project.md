# Project Context

## Purpose
ForcePet（又名 Django Workbench）是一个面向 Salesforce 开发者的工作台，目标是复刻并增强原始 PHP Workbench 的体验。项目提供统一的 Web 界面，帮助开发者完成 SOQL/SOSL 查询、数据批处理、元数据部署、Apex 执行、流式订阅等常见任务，同时内建会话管理、查询历史和环境切换能力。

## Tech Stack
- Python 3.11+、Django 4.2（主框架）与 Django REST Framework 3.14（API 层）
- Celery 5.3 + Redis（长耗时任务、批处理队列与缓存）
- PostgreSQL 13+ 作为生产数据库，开发场景默认回退到 SQLite
- simple-salesforce、Zeep (SOAP)、requests、lxml 等库用于对接 Salesforce REST/SOAP/Bulk/Metadata/Streaming API
- Django 模板系统 + Bootstrap 5 + jQuery + 定制化 JavaScript（`static/js/workbench.js`）构建前端交互
- python-dotenv 管理环境变量，Whitenoise 提供静态资源服务，Gunicorn 用于部署

## Project Conventions

### Code Style
- Python 代码遵循 PEP 8，使用 4 空格缩进，函数和类保持职责单一；引入外部服务时补充模块级 docstring 说明用途
- 推荐使用 `black`/`isort`（如已安装）在提交前格式化；保持字符串使用单引号，与现有代码保持一致
- JavaScript 采用 ES5 兼容语法以便在旧浏览器环境工作，依赖 jQuery/Bootstrap；公共交互逻辑集中在 `static/js/workbench.js`
- 模板命名遵循 `<app>/<feature>.html`，模板块使用 snake_case，避免在模板中编写复杂业务逻辑

### Architecture Patterns
- 采用 Django 多应用拆分架构：`authentication/`、`query/`、`data/`、`metadata/`、`apex/`、`bulk/`、`rest_explorer/`、`streaming/` 等 app 对应 Salesforce 的不同能力域
- `authentication.middleware.SalesforceSessionMiddleware` 负责在请求上下文中加载/验证 Salesforce 会话，`SalesforceClient` 作为统一的后端集成层封装所有 API 调用
- 长耗时或异步任务（如 Bulk API、Metadata 部署）必须封装为 Celery 任务，并通过 `AsyncJob` 模型跟踪状态
- 配置通过 `.env` 注入，`workbench_project/settings.py` 会在 Redis 不可用时回退到数据库缓存，确保开发环境可运行
- 前端侧强调渐进增强：服务端渲染页面 + JavaScript 增强，复杂编辑器（SOQL、Apex）通过动态初始化

### Testing Strategy
- 使用 Django 内置测试框架运行（`python manage.py test`），推荐基于 `TestCase`/`APITestCase` 为每个 app 覆盖视图与服务层；对 Celery 任务可通过 `CELERY_TASK_ALWAYS_EAGER=True` 在单元测试中同步执行
- 与 Salesforce 的交互必须通过 `responses`/`requests-mock` 等工具模拟，严禁在测试中直接访问外部 API
- 针对关键用户流程（登录、查询、批处理）优先编写集成测试；对于模板渲染和 JavaScript 可补充最小化快照或 Selenium/Playwright 脚本（可选）
- 若使用 pytest，可在本地安装扩展包，但需要保证 `manage.py test` 仍然通过

### Git Workflow
- `main` 分支保持可部署状态；为每个 OpenSpec 变更创建 `feature/<change-id>` 或 `chore/<change-id>` 分支，命名中包含动词式 change-id
- 提交信息使用祈使句，首行包含相关 change-id（例如 `Add query history export (change: add-query-export)`），确保与规格追踪对应
- 在提交前运行必要的迁移、测试与格式化检查；推送后通过 Pull Request 发起代码评审，优先保持单一职责、小批量变更
- 若需要同步上游更新，首选 rebase 而非 merge，保持线性历史

## Domain Context
项目服务于 Salesforce 平台开发者，核心场景包括：
- 多种认证方式（OAuth、用户名/密码、定制域），支持生产、Sandbox 和自定义域，默认 API 版本为 62.0
- SOQL/SOSL 查询与历史管理、结果导出、性能指标追踪
- 数据操作（Insert/Update/Upsert/Delete/Undelete）与 CSV 批量处理
- 元数据浏览、检索、部署，配合 `metadata` app 的工具化接口
- Apex 代码执行、测试运行以及调试日志查看
- Bulk API 任务调度、异步进度展示
- REST Explorer 与 Streaming API 推送订阅
所有 Salesforce 令牌使用 `cryptography.Fernet` 加密持久化，`AsyncJob` 模型记录后台任务状态，日志写入 `logs/workbench.log`。

## Important Constraints
- 必须确保访问令牌、刷新令牌加密存储，防止明文写入数据库或日志；日志中避免记录 Salesforce 返回的敏感字段
- 任何与 Salesforce 的请求都要考虑速率限制与批量大小，长耗时操作应落到 Celery，避免阻塞同步请求
- 应用需在 Redis 不可用时保持可运行（自动回退到数据库缓存）；部署环境需显式配置数据库和 Redis
- 前端依赖 Bootstrap/jQuery，任何新增交互需兼容现有初始化流程，谨慎引入额外框架以控制静态资源体积
- 提交前确认 `openspec validate --strict` 与数据库迁移一致，避免出现未跟踪的迁移或破坏性变更

## External Dependencies
- Salesforce 平台：REST、SOAP、Bulk、Metadata、Tooling、Streaming 等 API 以及预配置的 Connected App（需要 Consumer Key/Secret 与回调地址）
- Redis：作为 Celery broker/结果存储及首选缓存层
- PostgreSQL：生产环境数据库（开发可回退到随仓库附带的 SQLite）
- 外部邮件/日志聚合（可选）：可根据部署环境对接企业级监控与告警平台
