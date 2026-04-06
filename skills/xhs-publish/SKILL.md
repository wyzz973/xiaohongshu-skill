---
name: xhs-publish
description: >
  Use when 用户要求发布内容到小红书、上传图文、上传视频、发长文、
  发帖、发笔记、定时发布时触发。
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
    emoji: "\U0001F4DD"
    os: [darwin, linux]
---

# 小红书内容发布

## 工具边界

所有操作只通过 `python scripts/cli.py <子命令>` 或 `python scripts/publish_pipeline.py` 执行。禁止 MCP 工具、外部项目或任何非本项目实现。

## 账号选择（前置）

运行 `list-accounts`：0 个 → 不加 `--account`；1 个 → 自动使用并告知用户；多个 → 询问用户选择。选定后全程固定。

---

## 输入判断

1. "发长文 / 写长文" → 长文流程
2. 有标题+正文+视频 → 视频流程
3. 有标题+正文+图片 → 图文流程
4. 只有 URL → WebFetch 提取内容后给出草稿待确认
5. 信息不全 → 补齐后再发布

## ⚠️ 发布前检查（每次必须全部确认）

1. [ ] 标题写入 /tmp/xhs_title.txt（不内联中文到命令行）
2. [ ] 正文**完整**写入 /tmp/xhs_content.txt（确认未截断，段落完整）
3. [ ] 图片/视频路径是绝对路径或 HTTP URL（禁止相对路径）
4. [ ] 标题长度 ≤ 20（汉字/全角=1，ASCII 每两个=1）
5. [ ] tags 通过 `--tags` 传入（不写进正文文件）
6. [ ] 发布前已让用户确认最终内容

---

## 图文/视频发布（推荐分步）

### 图文

```bash
# 步骤 1：填写表单
python scripts/cli.py fill-publish \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --images "/abs/pic1.jpg" "/abs/pic2.jpg" \
  [--tags "标签1" "标签2"] [--schedule-at "ISO8601"] \
  [--location "地点"] [--original] [--visibility "公开可见"] \
  [--collection "合集名"] [--content-type "自主拍摄"]

# 步骤 2：用户在浏览器确认预览

# 步骤 3a：确认 → python scripts/cli.py click-publish
# 步骤 3b：取消 → python scripts/cli.py save-draft（⚠️ 必须保存草稿）
```

### 视频

```bash
python scripts/cli.py fill-publish-video \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --video "/abs/video.mp4" \
  [--tags "标签1" "标签2"] [--visibility "公开可见"]
# 确认 → click-publish / 取消 → save-draft
```

### 文字配图

```bash
# 分步
python scripts/cli.py fill-text2image \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  [--tags "标签1" "标签2"] [--location "地点"]
# → click-publish

# 一步发布
python scripts/cli.py publish-text2image \
  --content-file /tmp/xhs_content.txt \
  [--title-file /tmp/xhs_title.txt] [--tags "标签1" "标签2"]
```

⚠️ **用户取消时必须调用 `save-draft`**，不得直接关闭 tab，否则内容丢失。

### 图片说明

`--images` 支持本地路径和 HTTP URL，**脚本自动下载 URL 图片，禁止手动 curl/wget 下载**。

---

## 长文发布

```bash
# 1. 填写长文内容
python scripts/cli.py long-article \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt

# 2. 从返回的 templates 列表中让用户选择
python scripts/cli.py select-template --name "用户选择的模板"

# 3. 填写发布页描述（正文摘要 ≤1000 字，非正文原文）
python scripts/cli.py next-step \
  --content-file /tmp/xhs_desc.txt \
  [--tags "标签1" "标签2"]

# 4. click-publish
```

⚠️ 长文发布注意事项：
1. tags 只在 `next-step` 传一次，`click-publish` 不再传
2. **描述文件 (`xhs_desc.txt`) 不要包含 `#tag`**——标签只通过 `--tags` 参数传入，代码会在描述框内通过 `#` 联想添加。如果描述文件末尾有 `#tag`，代码会自动提取合并到 tags 并从描述中移除，但应避免这种写法
3. 分步 CLI 调用依赖 session tab 复用（`_connect_existing`），如果遇到 session 丢失导致 select-template 或 next-step 失败，可用单 Python 脚本跑全流程

---

## 标题长度规则

长度 = 汉字/全角符号各计 1，ASCII 字符（英文/数字/空格）每 **2 个**计 1（不足 2 个按 1 计）。上限 20。

超长时：根据核心含义重新措辞（不是机械截断），目标恰好 19-20。生成后重新计算，反复调整直到合格。

---

## 可选参数

| 参数 | 说明 | 何时用 |
|------|------|--------|
| `--tags "T1" "T2" ...` | 标签候选池（脚本随机选 3-6 个） | 建议传 8-15 个 |
| `--location "地点"` | 地点 | 探店/旅行/本地生活 |
| `--content-type "类型"` | 自主拍摄 / 来源转载 | 视情况 |
| `--original` | 声明原创 | 原创内容 |
| `--no-duet` / `--no-copy` | 禁合拍/禁复制 | 保护内容 |
| `--collection "合集名"` | 加入合集 | 系列内容 |
| `--visibility "范围"` | 公开可见/仅自己/仅互关 | 默认公开 |
| `--schedule-at "ISO8601"` | 定时发布 | 非立即发布 |
| `--headless` | 无头模式（未登录自动降级有窗口） | 服务器 |

## 失败处理

- **未登录**：提示先登录（xhs-auth）。`--headless` 自动降级到有窗口模式
- **图片下载失败**：换 URL 或改本地图片
- **视频超时**：等待最长 10 分钟，超时重试
- **标题过长**：按规则重新措辞
- **用户取消**：必须 `save-draft`，不得直接关闭
