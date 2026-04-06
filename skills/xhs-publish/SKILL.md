---
name: xhs-publish
description: 小红书发布场景 — 图文、长文、文字配图、视频的分步发布与草稿管理
version: 2.0.0
---

# 发布场景

## 能力声明

本 Skill 处理小红书内容发布的完整生命周期：
- 图文发布（分步：填写表单 → 预览校验 → 确认发布）
- 长文发布（内部自动处理模板选择和内容填充）
- 文字配图发布（分步或一步）
- 视频发布（分步或一步）
- 保存草稿（取消发布时必须执行）

不能做：修改已发布内容、删除笔记、管理合集结构、处理定时任务调度。

## 命令清单

| 命令 | 用途 | 必需参数 | 可选参数 | 退出码 |
|------|------|---------|---------|--------|
| `fill-publish` | 填写图文发布表单（分步第1步） | `--title-file`, `--content-file` | `--images`, `--tags`, `--xsec-source` | 0=成功, 1=未登录, 2=错误 |
| `click-publish` | 确认发布（分步最终步） | 无 | 无 | 0=成功, 1=未登录, 2=错误 |
| `publish` | 一步图文发布（fill + confirm） | `--title-file`, `--content-file` | `--images`, `--tags`, `--xsec-source` | 0=成功, 1=未登录, 2=错误 |
| `fill-publish-video` | 填写视频发布表单（分步第1步） | `--video`, `--title-file`, `--content-file` | `--tags` | 0=成功, 1=未登录, 2=错误 |
| `publish-video` | 一步视频发布 | `--video`, `--title-file`, `--content-file` | `--tags` | 0=成功, 1=未登录, 2=错误 |
| `fill-text2image` | 填写文字配图表单（分步第1步） | `--content-file` | `--title-file`, `--tags` | 0=成功, 1=未登录, 2=错误 |
| `publish-text2image` | 一步文字配图发布 | `--content-file` | `--title-file`, `--tags` | 0=成功, 1=未登录, 2=错误 |
| `long-article` | 长文发布（内部处理模板+填充） | `--title-file`, `--content-file` | `--tags`, `--template`, `--desc-file` | 0=成功, 1=未登录, 2=错误 |
| `select-template` | 长文选择模板 | `--template` | 无 | 0=成功, 2=错误 |
| `next-step` | 长文下一步（填写发布页描述+标签） | 无 | `--summary` | 0=成功, 2=错误 |
| `save-draft` | 保存草稿（取消发布时必须调用） | 无 | 无 | 0=成功, 2=错误 |

CLI 前缀：`python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py`

## 执行协议

### 场景 A：图文发布（推荐分步）

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 标题文件已写入（内容不超过 20 字符等价长度）
- 正文文件已写入，内容完整无截断
- 图片使用绝对路径或 HTTP URL
- 标签只通过 `--tags` 传递，不写进正文文件

#### 执行步骤

1. 写入标题到临时文件（不内联到命令行）：
   ```
   /tmp/xhs_title.txt
   /tmp/xhs_content.txt
   ```
2. 运行 `fill-publish`：
   ```bash
   python .../cli.py fill-publish \
     --title-file /tmp/xhs_title.txt \
     --content-file /tmp/xhs_content.txt \
     --images "/abs/path/pic1.jpg" \
     --tags "标签1" "标签2"
   ```
3. 等待命令返回成功（exit_code=0），检查预览内容是否正确。
4. 确认无误后运行 `click-publish`：
   ```bash
   python .../cli.py click-publish
   ```
5. click-publish 返回后，等待其完全结束，**不得并行执行任何其他命令**。

#### 后置校验
- 返回 JSON 包含 `status: "published"` 或 `note_id`

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| fill-publish exit_code=1 | 先执行 check-login，完成登录后重试 |
| fill-publish exit_code=2, "图片下载失败" | 检查图片 URL 可访问性，改用本地路径 |
| click-publish 无响应（>60秒） | 不重复执行；检查浏览器 tab 状态，运行 save-draft 保存 |
| 标题过长 | 按规则重新措辞（不机械截断），重写文件后重试 fill-publish |
| 用户取消发布 | 必须执行 save-draft，禁止直接关闭 |

### 场景 B：长文发布

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 标题、正文文件已就绪
- 如需自定义描述，准备独立的 desc 文件（正文摘要 ≤1000 字，非正文原文）

#### 执行步骤

`long-article` 命令内部自动处理模板选择和内容填充，推荐使用单命令模式：

```bash
python .../cli.py long-article \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --tags "标签1" "标签2" \
  --desc-file /tmp/xhs_desc.txt
```

如需手动分步控制：

1. 运行 `long-article`（不带 `--template`），获取可用模板列表
2. 运行 `select-template --template "模板名称"`
3. 运行 `next-step`（可选 `--summary` 传入摘要）
4. 运行 `click-publish`

#### 关键约束
- tags 只在 `next-step` 或 `long-article` 传一次，`click-publish` 不再传
- desc 文件末尾不要包含 `#tag`，标签只通过 `--tags` 参数传递
- 分步模式依赖 session tab 复用，若 select-template 或 next-step 报 session 丢失，改用单命令 `long-article`

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| select-template 报 session 丢失 | 改用 `long-article --template "模板名"` 单命令模式 |
| next-step 失败 | 检查 desc 内容是否含 `#tag`，清理后重试 |
| long-article exit_code=2, 超时 | 内容过长或网络慢，等待后重试；视频上传最长等待 10 分钟 |

### 场景 C：文字配图发布

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 正文文件已就绪（标题文件可选）

#### 执行步骤（推荐分步）

1. 运行 `fill-text2image`：
   ```bash
   python .../cli.py fill-text2image \
     --content-file /tmp/xhs_content.txt \
     --title-file /tmp/xhs_title.txt \
     --tags "标签1" "标签2"
   ```
2. 确认预览后运行 `click-publish`

#### 备选：一步发布
```bash
python .../cli.py publish-text2image \
  --content-file /tmp/xhs_content.txt \
  --title-file /tmp/xhs_title.txt \
  --tags "标签1" "标签2"
```

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=1 | 先登录再重试 |
| exit_code=2 | 检查 content-file 是否为空或路径错误 |

### 场景 D：视频发布

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 视频文件为绝对路径，格式 mp4/mov
- 标题、正文文件已就绪

#### 执行步骤（推荐分步）

1. 运行 `fill-publish-video`：
   ```bash
   python .../cli.py fill-publish-video \
     --video "/abs/path/video.mp4" \
     --title-file /tmp/xhs_title.txt \
     --content-file /tmp/xhs_content.txt \
     --tags "标签1" "标签2"
   ```
2. 等待视频上传完成（可能需要数分钟）
3. 确认预览后运行 `click-publish`

#### 备选：一步发布
```bash
python .../cli.py publish-video \
  --video "/abs/path/video.mp4" \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --tags "标签1" "标签2"
```

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| 视频上传超时（>10分钟） | 检查文件大小和网络，压缩视频后重试 |
| exit_code=2, "格式不支持" | 转换为 mp4 格式后重试 |
| click-publish 后无响应 | 等待视频处理完成，不重复点击 |

## 关键规则（CRITICAL RULES）

1. **生产环境必须用分步流程**：`fill-*` → 预览检查 → `click-publish`。禁止直接用 `publish` / `publish-video` 等一步命令跳过校验。
2. **click-publish 后禁止并行执行任何命令**：等待其完全返回后，再进行下一步操作，否则可能导致发布失败或内容异常。
3. **标签不写进正文文件**：所有标签只通过 `--tags` 参数传递，正文和描述文件中不包含 `#tag` 字样。
4. **内容通过文件传递**：`--title-file` 和 `--content-file` 使用绝对路径的临时文件，不内联中文内容到命令行参数。
5. **取消时必须调用 save-draft**：用户取消发布时，必须执行 `save-draft` 保存草稿，不得直接关闭 tab。
6. **图片路径必须是绝对路径或 HTTP URL**：禁止使用相对路径；HTTP URL 由脚本自动下载，禁止手动 curl/wget。

## 安全限制

| 操作 | 每日上限 | 时间分布 |
|------|---------|---------|
| 发布（所有类型合计） | 3-4 篇 | 分布在不同时段（早/午/晚） |
| 相邻两次发布间隔 | — | 至少 30 分钟 |
| 夜间（23:00-06:00） | 禁止发布 | — |

遇到验证码弹窗、账号异常提示 → 立即停止，记录日志，不重试。
