# R5 阶段交接：县级工业就业数据证据审查（2026-10-10）

## 已完成且可核查
- 全国 117 条工业事件及 5 项修订已处于此支线，PR #37；保留 `r1-events.json`、`r2-r3-events.json`、`r4-events-and-updates.json` 原始资料。
- 本轮在官方 Destatis GENESIS 再次确认 **42111-0001** 全国年度制造业工业企业场所统计与 **42111-0010** 州级年度场所就业和营收统计的公开数据入口。
- 官方全国2024年该项制造业企业场所从业人员 **5,540,101**，2025年 **5,433,048**，差值 **−107,053**，变化率约 **−1.93%**；分别对应 22,347 / 22,086 家企业场所（统计覆盖门槛存在，不能将减少261解释为261家关闭）。来源 https://genesis.destatis.de/datenbank/online/statistic/42111/table/42111-0001/search/s/NDIxMTE%3D ，网页上展示行业大类综合值，正式发布前应再次核对表头、口径和门槛。
- 42111-0010 州级历年序列可直接用于**交叉核对**县级汇总，但不能将州级数据复制到县级图层。 https://genesis.destatis.de/datenbank/online/statistic/42111/table/42111-0010
- **尚未完整获取官方402县2019—2025同口径就业面板**。因此地图全国县市真实就业收缩底色依旧明确缺失，严禁为地图做假填色。
- 本轮将调查与数据质量列为优先事项，而不是盲目叠加企业媒体数量。

## 数据整合规范
1. 县级就业分析应储存 `ags, area_name, year, employed_persons, industry_scope, establishment_size_threshold, source_table, source_access_date, confidentiality_flag`。
2. 2019→最近年份仅比较完全同口径且行政边界已对齐数据；有保密/缺失则不出百分比，**不能视为0**。
3. 目前 `county-employment.json` 为明确空值占位，保留到有下载验收记录为止。
4. 实际企业公告、计划、实施新闻分开管理；R2/R3/R4均不是对德国所有工业关闭工厂的全面普查。
5. 首屏仅保留县市单色底色 + 大企业关厂/裁员红点，能源和基建数据后台做相关性研究，不进入前端主图。

## 下一断点
- 找到 Regio-Stat 42111-02-03-4 的原始 CSV/地区下载文件或16州统计站的同口径CSV；计算每年的县数、保密缺失率和AGS对照率，再生成正式指标。
- 独立抽核现有117事件的原始URL、报道时点、实际工厂位置，构建 `verified_site_coordinates.json` 和单独的 `not_additive_groups.json`。
- 增补最新关厂事件时必须标注来源、日期、状态；以同一厂址+同一重组计划去重，不能以新闻报道次数计数。

## 恢复入口
- GitHub: https://github.com/1959124923wyz-sys/German-Map/pull/37
- 支线 `feature/industry-contraction-map-20261010`
- 此文档 `topics/industry/research/R5_HANDOFF.md`

## 第二阶段：来源与覆盖审计已提交
- 新增 `R5_REGIONALATLAS_SOURCE_AUDIT.md`：找到Regionalatlas AI0704（制造业就业占比）、AI0405（制造业受雇岗位人口密度）及公开GIS接口，明确不能直接作为就业人数下降率。
- 新增 `R5_COVERAGE_AUDIT.json`：117条记录逐州、逐年、逐实施状态统计及83条厂址定位待办；这些待办不是83家缺失企业，而是还未核到**精确厂门坐标**的已有记录。
- 新增 `destatis_42111_national_2024_2025.csv`：官方全国两年制造业就业/场所数参考点，来源直接保留GENESIS表号，供以后检查县市合计。
- 当前17个地域分组包括16州与3条跨州/不确定州的集团记录；集团项目不渲染为县级红点。
- `R5_COVERAGE_AUDIT.json`中仍存在十条从鲁尔早期继承的中文自由状态文本；正式发布的统一状态枚举需另加映射，不能直接原样用于“已完成关厂数量”汇总。

## 数据抓取现实限制
- 本轮探索的公开黑森Hessen CSV数据源只含黑森，且本会话下载返回403；没有将它当成已获取的全国面板。
- 官方GIS接口仅定位成功，未完成全国县级逐年实体数据验收；不能宣称全国县级就业变化完成。

## 第三阶段：取得402个几何AG S对应键
- 主项目 `data/germany-counties.geojson` 的402个Feature中**全部存在唯一5位 `feature.id`**；从历史GeoJSON直接提取，生成 `topics/industry/data/county_ags_crosswalk.json`。这一点修正了R1“缺AGS”的认识。
- 上述402个ID是**当前项目历史几何携带的AGS**，并非已经由Destatis 2025/2026县市边界新修订认证；旧区划特别是县域合并需要再核查。
- `topic.js` 已经把未来官方就业序列按 `feature.id` 匹配，不再用同名县市拼接；缺失区域继续灰色，官方就业数据不与新闻计数混色。
- `tests/validate_industry.cjs` 已对402个ID唯一性、长度和AGS代码使用做CI验收。
- 新增 `scripts/try_regionalatlas_county.py`：利用bundesAPI开源文档生成ArcGIS查询，默认只打印请求；必须指定`--execute`才访问网络，结果只保存为候选数据，不自动发布；若不满足覆盖要求须保留失败日志。
- 全国真实2019→2024/2025县级就业面板仍未完成正式下载/验收，R5不得报称地图已按真实就业下降率着色。

## 第四阶段：Regionalatlas ArcGIS 在线抓取实测（未成功）
- GitHub Actions研究任务 `industry-research-fetch.yml` 在支线执行，运行编号 [38037722026](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037722026)。
- 运行脚本 `scripts/try_regionalatlas_county.py` 于2019年与2024年分别测试 `ai007_1_5` 县级制造业就业占比候选表。
- 实际服务器均返回 **ArcGIS code 400 / Invalid or missing input parameters**，程序退出码均为3；已保留日志 [artifact 11663483662](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037722026/artifacts/11663483662)。
- GitHub工作流步骤本身完成（因为候选抓取故意容错），**这不代表县级官方数据已经成功下载**。本轮仍没有真实县级数值、没有用于上色的2019—2024面板。
- 以后优先检查Regionalatlas2026真实表名、ArcGIS当前查询参数、服务端SQL权限；也可改用经身份注册的Regionaldatenbank原始导出或各州统计局CSV，避免同一个错误请求无限重试。
