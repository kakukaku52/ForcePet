## Why

Data 模块当前的“Insert”能力仅支持通过 JSON/CSV 批量提交，缺少面向业务用户的单记录录入界面。实现一个直观的页面，方便在无需准备批量文件的情况下快速创建 Salesforce 记录。
页面的下拉菜单如果选项太多的话，用户不容易找到想要的名称，需要在下拉菜单添加一个可以搜索的功能。

## What Changes

- 新增“创建记录”页面，包含 SObject 下拉菜单与“单一记录 / 文件上传”模式切换
- 页面加载时自动拉取当前 Salesforce 实例可用对象列表填充下拉选项
- 根据模式切换展示单一记录步骤或文件上传 UI，并通过“下一步”按钮驱动流程
- 将页面挂载到数据操作导航，并复用现有 `SalesforceClient` 执行插入
- 在成功与失败时给出可读反馈，并记录操作结果
- Add searchable object dropdown on the Insert page so users can quickly locate targets
- 调整“下一步”流程，隐藏选择控件并提供返回按钮，以向导式体验完成单记录/文件上传步骤
- 为单记录字段表和 CSV 映射表提供行删除操作，方便用户管理输入
- 引入确认与完成界面：预览待提交数据、二次确认 Insert，并在结果页展示成功/失败信息及错误明细

## Impact

- 受影响的规格：data
- 受影响的代码：`data/views.py`、`data/forms.py`、`data/urls.py`、`templates/data/*.html`、可能更新 `templates/base.html`
