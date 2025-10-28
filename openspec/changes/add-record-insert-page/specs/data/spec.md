## ADDED Requirements
### Requirement: Salesforce Record Insert Page
数据模块 MUST 提供一个创建记录页面，供登录用户通过图形界面选择 SObject、决定插入模式（单一记录或文件上传），并引导完成记录创建。

#### Scenario: Navigate from data workspace
- **WHEN** 用户登录后进入数据操作首页或主导航
- **THEN** 系统提供明显入口打开“创建记录”页面
- **AND** 页面展示 SObject 下拉菜单、模式选择下拉菜单（默认选中“单一记录”）以及“下一步”按钮
- **AND** 页面不需要用户通过文本框输入对象名称

#### Scenario: Load object options on page load
- **GIVEN** 用户拥有有效的 Salesforce 会话
- **WHEN** “创建记录”页面加载
- **THEN** 系统 MUST 调用 Salesforce 对象列表接口（例如 `describeGlobal`）
- **AND** 使用返回结果填充 SObject 下拉菜单，选项包含对象的 API 名称和可读标签
- **AND** 如果接口失败，页面 MUST 显示错误提示并允许用户重试或手动刷新

#### Scenario: Toggle mode specific UI
- **GIVEN** “创建记录”页面展示模式选择下拉菜单
- **WHEN** 用户选择“文件上传”
- **THEN** 页面 MUST 显示文件上传控件（支持所需格式说明）
- **AND** 当用户切换回“单一记录”时隐藏文件上传控件，以避免干扰单记录流程

#### Scenario: Proceed with single record flow
- **GIVEN** 用户在“创建记录”页面选择 SObject 并保持模式为“单一记录”
- **WHEN** 用户点击“下一步”
- **THEN** 系统 MUST 展示字段录入 DataTable，列为 `Field`、`Value`、`Smart Lookup`
- **AND** `Value` 列中的每一行 MUST 提供文本输入框以录入字段值
- **AND** 页面 MUST 提供 `Insert` 按钮以提交当前行集合
- **AND** 成功提交后展示带有新记录 Id 的成功消息
- **AND** 将此次操作写入 `DataOperation`，包含 SObject、字段数量、成功数量

#### Scenario: Proceed with file upload flow
- **GIVEN** 用户在“创建记录”页面选择 SObject 并将模式切换为“文件上传”
- **WHEN** 用户点击“下一步”并选择有效文件
- **THEN** 系统 MUST 展示字段映射 DataTable，列为 `Field`（Salesforce 字段）、`CSV Field`、`Smart Lookup`
- **AND** `CSV Field` 列中的每一行 MUST 使用下拉菜单列出上传 CSV 的列名，供用户指定字段映射
- **AND** 文件选择控件 MUST 只接受 CSV 文件（通过文件类型过滤和校验）
- **AND** 用户确认映射后，系统 MUST 调用文件上传流程创建记录
- **AND** 成功后展示包含处理结果的反馈信息
- **AND** 将此次操作写入 `DataOperation`，记录成功与失败数量

#### Scenario: Access via navigation bar
- **GIVEN** 用户已通过应用导航栏看到 `Insert` 链接
- **WHEN** 用户点击 `Insert`
- **THEN** 系统 MUST 将用户导航到“创建记录”页面
- **AND** 页面加载时保持当前 Salesforce 会话上下文

#### Scenario: Insert failure handling
- **GIVEN** Salesforce 返回错误（例如缺少必填字段或权限不足）
- **WHEN** 用户提交表单
- **THEN** 页面必须保留用户填写的字段
- **AND** 显示可读的错误提示以及 Salesforce 返回的详细错误
- **AND** 在 `DataOperation` 中记录失败详情
