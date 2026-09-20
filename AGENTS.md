# 项目协作规范

## 沟通与命令

- 所有回复使用中文。
- 每次执行 shell/cmd 命令前先运行 `pwd`，确认当前目录正确；优先使用 PowerShell。
- 安装命令不使用 `&&`，分行执行各命令，例如：
  ```powershell
  pwd
  cd window_client
  pwd
  npm install --save-dev @electron-forge/maker-wix
  ```

## 流程控制

- 使用 **Early Return / Guard Clause**：函数开头先处理空值、无效参数和前置条件，主逻辑保持扁平。
- 避免 `if (true) {}` 等无效分支；优先使用 `if (!condition) { return; }`。
- 嵌套不超过 3 层；复杂判断和处理提取为独立函数。
- 每个函数只做一件事，函数名清晰表达意图，单个函数不超过 100 行。
- 多层 `if-else` 用提前返回或对象映射扁平化。
- 循环用 `continue` 跳过无效项，并将循环体处理提取为函数；避免循环内深层 `try-catch`。

```ts
function processUser(user: User | null) {
  if (!user) return { error: '用户不存在' }; // 前置检查
  if (!user.isActive) return { error: '用户未激活' };
  if (!user.hasPermission) return { error: '无权限' };
  return doSomething(user); // 主逻辑
}

function getStatus(code: number) {
  const map: Record<number, string> = { 200: 'success', 404: 'not found', 500: 'server error' };
  return map[code] || 'unknown'; // 映射替代多层分支
}
```

## 异常与错误处理

- `try` 只包裹可能抛出异常的代码；每个 `try` 处理一类错误。
- `catch` 记录错误后立即返回，避免继续嵌套。
- 重复的错误处理提取为统一函数，并先检查资源状态。

```ts
async function fetchData() {
  let user;
  try { user = await getUser(); } catch (e) {
    console.error('获取用户失败:', e); return null;
  }
  if (!user) return null;
  let data;
  try { data = await loadData(user.id); } catch (e) {
    console.error('加载失败:', e); return null;
  }
  if (!data) return null;
  try { return processData(data); } catch (e) {
    console.error('处理失败:', e); return null;
  }
}

function safeEnqueue(controller: Controller, data: unknown) {
  if (controller.desiredSize === null) return; // 已关闭
  try { controller.enqueue(data); } catch { safeClose(controller); }
}

function safeClose(controller: Controller) {
  try { controller.close(); } catch { /* 静默处理 */ }
}
```

## 数据与交付

- 使用 `Number(value || 0)` 转换数值，使字符串可转换、空值归零并避免 `NaN`。
- 一次性完成全部 TODO。
- 不新增任何 `__tests__` 测试文件。
- 所有新增或修改的代码都必须有注释,“初学者”水平也能读懂这些注释。

## 提交前检查

- [ ] 边界条件使用 Early Return，守卫位于函数开头。
- [ ] `try-catch` 范围足够小，`catch` 及时结束。
- [ ] 嵌套未超过 3 层，函数未超过 100 行且职责单一。
- [ ] 相似逻辑已复用，多层 `if-else` 已扁平化。
- [ ] 循环已使用 `continue` 或独立处理函数降低嵌套。
- [ ] 错误处理已统一，资源状态已先检查。

> 好代码应能从上到下线性阅读，而不是像迷宫一样来回跳跃。
