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
