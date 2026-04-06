# strategy.json 字段说明

## account — 账号信息

| 字段 | 类型 | 说明 |
|------|------|------|
| nickname | string | 小红书昵称 |
| track | string | 主赛道（美妆/科技/学习/美食/穿搭/旅行/健身/职场） |
| sub_track | string | 细分领域 |
| one_liner | string | 一句话定位 |
| xhs_id | string | 小红书号（可选，用于数据追踪） |

## persona — 人设风格

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 专业导师/闺蜜分享/理性测评/搞笑吐槽/知识科普/生活记录 |
| call_reader | string | 称呼读者：姐妹们/宝子们/朋友们/各位 |
| call_self | string | 自称：我/姐姐/学姐 |
| emoji_density | string | 高/中/低 |
| tone_keywords | string[] | 3 个描述内容调性的关键词 |
| catchphrase | string | 口头禅（可选） |
| forbidden_words | string[] | 禁止使用的 AI 味词汇 |
| content_form | string | 图文为主/视频为主/混合 |

## content_strategy — 内容策略

| 字段 | 类型 | 说明 |
|------|------|------|
| pillars | array | 3 个内容支柱，含 name/description/weight |
| pillars[].weight | float | 各支柱的内容占比，总和为 1 |
| note_types | string[] | 常用笔记类型：教程/种草/测评/合集/避雷/经验分享 |
| target_audience | object | 目标受众画像 |
| monetization | string | 涨粉/品牌合作/引流私域/知识付费/电商带货/纯分享 |

## schedule — 调度时间

| 字段 | 类型 | 说明 |
|------|------|------|
| timezone | string | IANA 时区，默认 Asia/Shanghai |
| publish_frequency | string | daily / twice_daily / every_other_day |
| publish_times | string[] | 发布时间点（HH:MM 格式） |
| 其他 *_time 字段 | string | 各 Cron 任务的执行时间 |

## interaction — 互动策略

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy | string | proactive(主动互动) / reactive(只回复) / mixed(混合) |
| daily_comment_limit | int | 每日评论上限（硬上限 25，不可超过） |
| daily_like_limit | int | 每日点赞上限（硬上限 50） |
| comment_interval_min/max_sec | int | 评论间隔秒数范围 |
| session_limit | int | 每次会话操作上限 |
| rest_after_session_min/max | int | 会话间休息秒数范围 |
| target_keywords | string[] | 搜索互动目标时使用的关键词 |
| avoid_accounts | string[] | 避免互动的账号列表 |

## safety — 安全设置

| 字段 | 类型 | 说明 |
|------|------|------|
| require_publish_confirmation | bool | 发布前是否需要人工确认 |
| notification_channel | string | telegram / feishu / discord / slack / none |
| notification_target | string | 通知目标 ID |
| use_test_account | bool | 是否使用测试账号（首次建议 true） |
| max_retries_on_error | int | 出错后最大重试次数（建议 0，即不自动重试） |
| stop_on_captcha | bool | 遇到验证码立即停止（始终为 true） |
| stop_on_rate_limit | bool | 遇到频率限制立即停止（始终为 true） |

## 示例：AI 工具测评账号

```json
{
  "account": {
    "nickname": "AI工具菌",
    "track": "科技",
    "sub_track": "AI工具推荐",
    "one_liner": "每天试用一个AI工具，帮你省下踩坑的时间"
  },
  "persona": {
    "type": "理性测评",
    "call_reader": "朋友们",
    "call_self": "我",
    "emoji_density": "中",
    "tone_keywords": ["理性", "实测", "接地气"],
    "content_form": "图文为主"
  },
  "content_strategy": {
    "pillars": [
      { "name": "AI工具测评", "description": "深度试用+对比评测", "weight": 0.5 },
      { "name": "效率提升教程", "description": "用AI工具解决具体问题", "weight": 0.3 },
      { "name": "行业观察", "description": "AI行业动态和趋势解读", "weight": 0.2 }
    ],
    "note_types": ["测评", "教程", "合集"],
    "target_audience": {
      "gender": "不限",
      "age_range": "22-40",
      "identity": "职场人/自由职业者/学生",
      "pain_points": ["工具太多不知道选哪个", "想提效但不知道怎么用", "怕花冤枉钱"]
    },
    "monetization": "涨粉"
  },
  "schedule": {
    "timezone": "Asia/Shanghai",
    "publish_frequency": "daily",
    "publish_times": ["10:00"]
  },
  "interaction": {
    "strategy": "mixed",
    "daily_comment_limit": 15,
    "target_keywords": ["AI工具", "效率", "ChatGPT", "提效神器"]
  },
  "safety": {
    "require_publish_confirmation": true,
    "notification_channel": "telegram"
  }
}
```
