---
name: xhs-auth
description: >
  Use when 用户要求登录小红书、检查登录状态、切换账号、扫码登录、
  手机号登录、添加/删除/切换账号时触发。
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
    emoji: "\U0001F510"
    os: [darwin, linux]
---

# 小红书认证管理

## 工具边界

所有操作只通过 `python scripts/cli.py <子命令>` 执行。禁止 MCP 工具、外部项目或任何非本项目实现。

## 账号选择（前置）

运行 `list-accounts`：0 个账号 → 不加 `--account`；1 个 → 自动使用并告知用户；多个 → 询问用户选择。选定后全程固定，不重复询问。

---

## 检查登录状态

```bash
python scripts/cli.py check-login
```

- `"logged_in": true` → 已登录
- `"logged_in": false` + `"login_method": "qrcode"` → 有界面，走二维码登录
- `"logged_in": false` + `"login_method": "both"` → 无界面，询问用户选二维码或手机验证码

## 二维码登录

`check-login` 未登录时自动返回 `qrcode_image_url` + `qrcode_path`，无需单独调 `get-qrcode`。

**第一步** — 展示二维码：

```
请使用小红书 App 扫描以下二维码登录：

![小红书登录二维码]({qrcode_image_url})

您也可以在手机浏览器中直接访问此链接完成登录：
{qr_login_url}
```

⚠️ **必须**同时展示 `qrcode_image_url` 和 `qr_login_url`（如有），禁止省略任一。

**第二步** — 等待（单次调用，无需轮询）：

```bash
python scripts/cli.py wait-login
```

输出 `"logged_in": true` 则完成；超时则 `get-qrcode` 刷新后重试。

⚠️ `get-qrcode` 在已登录状态下返回 `"logged_in": true` 而非二维码，只有未登录时才生成二维码。

## 手机验证码登录

⚠️ **每次登录都必须向用户确认手机号，禁止从记忆/上下文自动填入。**

**第一步** — 询问用户手机号，确认后：

```bash
python scripts/cli.py send-code --phone <手机号>
```

频率限制时自动返回二维码，切换为二维码登录。

**第二步** — 询问用户 6 位验证码，确认后：

```bash
python scripts/cli.py verify-code --code <验证码>
```

## 退出登录

`delete-cookies` 内部自动完成 UI 退出 + 清除本地 cookies：

```bash
python scripts/cli.py delete-cookies
python scripts/cli.py --account work delete-cookies  # 指定账号
```

## 多账号管理

每个命名账号独立端口（从 9223 起）和独立 Chrome Profile，完全隔离。

```bash
python scripts/cli.py add-account --name work --description "工作号"
python scripts/cli.py list-accounts
python scripts/cli.py set-default-account --name work
python scripts/cli.py remove-account --name personal
python scripts/cli.py --account work check-login    # 指定账号执行
```

## 失败处理

- **Chrome 未找到**：安装 Chrome 或设置 `CHROME_BIN`
- **二维码超时**：`get-qrcode` 刷新后重试 `wait-login`
- **验证码错误**：重新 `verify-code --code <新验证码>`
- **CDP 连接失败**：检查 Chrome 是否开启 `--remote-debugging-port`
