## Why
Data 模块当前的“Insert”能力仅支持通过 JSON/CSV 批量提交，缺少面向业务用户的单记录录入界面。实现一个直观的页面，方便在无需准备批量文件的情况下快速创建 Salesforce 记录。

## What Changes
- 新增“创建记录”页面，包含 SObject 下拉菜单与“单一记录 / 文件上传”模式切换
- 页面加载时自动拉取当前 Salesforce 实例可用对象列表填充下拉选项
- 根据模式切换展示单一记录步骤或文件上传 UI，并通过“下一步”按钮驱动流程
- 将页面挂载到数据操作导航，并复用现有 `SalesforceClient` 执行插入
- 在成功与失败时给出可读反馈，并记录操作结果

## Impact
- 受影响的规格：data
- 受影响的代码：`data/views.py`、`data/forms.py`、`data/urls.py`、`templates/data/*.html`、可能更新 `templates/base.html`
