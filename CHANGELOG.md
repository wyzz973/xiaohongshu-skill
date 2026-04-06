# Changelog

## 2.0.0 (2026-03-13)

- 跨模型稳定性优化：命令卡片格式、Preflight Checklist、评论生成防僵硬规则
- 新增 list-notifications / reply-notification / like-notification 命令
- 新增重复评论检测（post-comment 返回 `"duplicate": true`）
- 新增小红书表情参考（评论/回复可插入 `[表情名]`）
- 新增 channel 板块浏览（list-feeds --channel）
- 新增发布页完整参数支持（location/content-type/original/duet/copy/collection）
- tags 自动从候选池随机选 3-6 个
- 新增 CLI 启动依赖检查（缺包时输出 JSON 错误而非 traceback）
- 新增版本号输出（所有 JSON 响应附带 `"version"` 字段）
- 依赖：requests>=2.28.0, websockets>=12.0
