---
name: xhs-auth
description: 小红书认证场景 — 登录状态检查、二维码/手机登录、登出、多账号管理
version: 2.0.0
---

# 认证场景

## 能力声明

本 Skill 处理小红书账号的认证生命周期：
- 检查登录状态（自动获取二维码）
- 二维码登录（阻塞/非阻塞两种模式）
- 手机验证码登录（单步/分步两种模式）
- 登出并清除 cookies
- 多账号管理（添加/列出/删除/设默认）

不能做：注册新账号、修改账号资料、绑定手机号。

## 命令清单

| 命令 | 用途 | 必需参数 | 可选参数 | 退出码 |
|------|------|---------|---------|--------|
| `check-login` | 检查登录状态，未登录自动获取二维码 | 无 | `--account` | 0=已登录, 1=未登录(返回二维码) |
| `login` | 二维码登录（阻塞等待120秒） | 无 | `--account` | 0=成功, 2=超时 |
| `get-qrcode` | 获取二维码立即返回（非阻塞） | 无 | `--account` | 0=已登录/二维码已生成 |
| `wait-login` | 等待扫码完成（配合get-qrcode） | 无 | `--timeout`, `--account` | 0=成功, 2=超时 |
| `phone-login` | 手机验证码登录（交互式） | `--phone` | `--code`, `--account` | 0=成功, 1=频率限制转QR, 2=失败 |
| `send-code` | 分步登录：发送验证码 | `--phone` | `--account` | 0=已发送, 1=频率限制转QR |
| `verify-code` | 分步登录：填写验证码 | `--code` | `--account` | 0=成功, 2=验证码错误 |
| `delete-cookies` | 退出登录并删除cookies | 无 | `--account` | 0=成功 |
| `add-account` | 添加命名账号 | `--name` | `--description` | 0=成功 |
| `list-accounts` | 列出所有账号 | 无 | 无 | 0=成功 |
| `remove-account` | 删除账号 | `--name` | 无 | 0=成功 |
| `set-default-account` | 设置默认账号 | `--name` | 无 | 0=成功 |

CLI 前缀：`python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py`

## 执行协议

### 场景 A：检查登录状态（最常用，其他场景前置）

#### 前置条件
- Chrome 已通过 OpenClaw 启动（端口 9222 默认）

#### 执行步骤

1. 运行 `check-login`
2. 解析返回 JSON：
   - `logged_in: true` → 认证通过，可执行后续场景
   - `logged_in: false` → 进入登录流程（见场景 B/C）

#### 后置校验
- 确认返回 JSON 包含 `logged_in` 字段

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=2, "无法启动 Chrome" | 检查 Chrome 是否安装，端口是否被占用 |
| 长时间无返回（>30秒） | Chrome 可能挂起，重启 Chrome 后重试 |

### 场景 B：二维码登录

#### 前置条件
- check-login 返回 `logged_in: false`

#### 执行步骤（推荐：非阻塞模式）

1. 运行 `get-qrcode`
2. 返回 JSON 包含：
   - `qrcode_path`: 本地二维码图片路径
   - `qrcode_image_url`: base64 图片 URL（可直接展示给用户）
   - `qr_login_url`: 登录链接（可选，取决于 QR 解码是否成功）
3. 展示二维码给用户，提示扫码
4. 运行 `wait-login --timeout 120`
5. 解析结果：`logged_in: true` → 完成

#### 备选：阻塞模式

1. 运行 `login`（内部自动获取 QR + 阻塞等待 120 秒）
2. 直接返回登录结果

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| wait-login 超时 | 重新运行 get-qrcode 获取新二维码 |
| qr_login_url 为空 | qrserver.com API 不可用，用 qrcode_path 展示图片即可 |

### 场景 C：手机验证码登录

#### 前置条件
- check-login 返回 `logged_in: false`
- 用户提供手机号

#### 执行步骤（推荐：分步模式，适合 Agent）

1. 运行 `send-code --phone <手机号>`
2. 如返回 `status: "code_sent"` → 提示用户查看短信
3. 获得验证码后运行 `verify-code --code <验证码>`
4. 解析结果：`logged_in: true` → 完成

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=1 + `login_method: "qrcode"` | 触发频率限制，已自动切换为二维码，按场景 B 处理 |
| verify-code 返回 "验证码错误" | 重新运行 verify-code（无需重发验证码） |
| verify-code 连续 3 次失败 | 重新运行 send-code 获取新验证码 |

### 场景 D：多账号管理

#### 执行步骤

1. `list-accounts` — 查看现有账号
2. `add-account --name <名称>` — 添加新账号（自动分配端口）
3. `set-default-account --name <名称>` — 设置默认
4. 后续所有命令加 `--account <名称>` 指定账号

#### 注意
- 每个账号有独立端口和 Chrome Profile，互不干扰
- 选定账号后全程固定，不中途切换

## 安全限制

- 登录操作无频率限制，但手机验证码受平台限制（约 1 分钟 1 次）
- 触发频率限制时自动切换为二维码登录，无需人工干预
- 遇到验证码弹窗 → 停止自动操作，通知用户手动处理
