# 德国地图维护5｜停止自动外部搜索与更新（2026-10-12）

## 目的与生效边界
用户要求：关闭各张地图的自动搜索/抓取/数据更新，但保留手动更新功能。**仍允许自动运行静态站点发布与非采集型数据验证/浏览器回归**；浏览器内正常地图瓦片、已提交静态JSON加载不属于后台自动搜索更新。

## 仓库审计
审计 `.github/workflows/*.yml` 共29个原有工作流。真正含 `schedule/cron` 的有三个，全部移除：
1. `germany-homicide-map.yml`：原每日 20:17 UTC，整个犯罪地图抓取、城区GIS/公安公告更新。
2. `drugs-news-update.yml`：原每日 04:27 UTC，德国警方毒品相关新闻采集、地理编码及Pages部署。
3. `drugs-euda-update.yml`：原每月14日 05:42 UTC，EUDA污水站点数据刷新。

另有13个与资料获取、外部官网核验、候选GIS构建或公开网站探针有关的工作流可能因源码 `push` 自动触发；全部统一为 **`workflow_dispatch` 手动模式**。共16个受影响工作流（包括上面3个）。覆盖犯罪、毒品、城市研究及源验证；它们均可在 GitHub Actions 中按需单独运行。

## 专门保留的自动行为
- `drugs-pages-deploy.yml`：当主线代码更新时自动部署GitHub Pages，**不执行外部新闻抓取或政府数据重建**。此次没有关闭。
- `atlas-shared-shell.yml`、`germany-homicide-map-smoke.yml`、`immigration-map-smoke.yml`、`environment-map-smoke.yml`、`railway-map-smoke.yml` 等：PR/主线正常CI、真浏览器检查保留；验证已提交快照不等同于每日重新爬源。
- `finance-pr-check.yml` / `three-topics-pr-check.yml`：专题源文件一致性、数据结构、页面与来源引用校验仍可按代码变动运行（不作为定时数据采集）。
- 前端用户打开地图时需要的地图瓦片/站内数据仍正常加载；没有通过删数据假装关闭定时更新。

## 防复发
新增 `tests/validate_manual_update_policy.py` 和 `.github/workflows/manual-source-update-policy.yml`。新CI核对全工作流不存在定时 `schedule`、受保护的16个抓源工作流仅 `workflow_dispatch`，同时仍保留自动网站部署及重要的PR验收。

## 如需以后手动更新
在 GitHub 仓库 **Actions** → 选择目标工作流（例如 `Germany crime map updater`、`Drug news collector and Pages publish`、`Drugs EUDA official wastewater refresh`）→ **Run workflow** → 选择 `main` → 执行。该命令会实际访问外部源、可能提交数据、部署网站；只有用户明确要求时才运行。纯网站修改不要求运行任何数据采集工作流。

## 注意事项
- 关闭未来的自动事件并不撤回过去生成的资料，不主动更改已发布数据的年份和含义。
- GitHub Pages 源文件可能仍包含“更新于某年某日”，属于数据快照，不意味着仍在后台自动更新。
- 新增专题/新workflow必须复查是否引入 `schedule`、`repository_dispatch`、`workflow_run` 或隐蔽的外部抓取自动触发；该Python守卫目前对普通 `schedule` 和已列出工作流的 `push` 保证，不能视作对所有未来机制的绝对覆盖。
- 合并及检查完成前只可称为“已提交关闭补丁”；主线合并之后方可称关闭。
