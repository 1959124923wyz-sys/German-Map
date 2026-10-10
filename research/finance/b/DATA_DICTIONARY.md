# 财政B字段说明与地图接入规则

## cases.csv / cases_map_ready.csv 字段

| 字段 | 含义 |
|---|---|
| `event_id` | 唯一事件记录ID；不保证对应唯一市镇/事件链 |
| `state` | 德国联邦州德文名称 |
| `municipality` | 城镇/县/柏林区的原名 |
| `ags` | 市镇8位AGS字符串；缺失不为0 |
| `geo_level` | municipality市镇；county县；city_district城市区 |
| `county_key` | 县级5位标识字符串，不可改写成8位市镇AGS |
| `event_type` | 研究事件类型；细分值较多，前端需映射为少量中文展示类别 |
| `status` | 证据状态，参看 status_dictionary.csv，不以当前日期自动推断 |
| `decision_date` | 议会/机构决定日期（为空表示不确定） |
| `effective_date` | 措施生效日期（可以为空；不等于最初讨论日） |
| `facility_name` | 受影响设施/项目名，空值并非缺乏事件地点 |
| `amount_eur` | 原始金额（欧元）；空值为未知；禁止全列求和 |
| `amount_kind` | 金额语义：冻结额度/借款授权/预计节支/实际节支/项目预算等；必须连同amount_eur显示 |
| `description_zh` | 经调查整理的中文事件概述 |
| `primary_source_url` | 原始官方主要证据URL |
| `secondary_source_url` | 补充证据URL，可以为空 |
| `primary_source_id` | sources.csv 的 source_id 外键 |
| `secondary_source_id` | 补充来源外键 |
| `last_verified` | 研究员上次核对日期，并非网页实时更新日 |
| `verification_tier` | 证据级别（非统计精度标签） |
| `map_eligible` | 原研究编辑标识，不等同 cases_map_ready 入选资格 |
| `parent_event_id` | 关联母事件，用于资金防重复计算和时间线 |
| `source_page` | 来源页码或定位 |
| `original_label_de` | 德文原项目或文件名 |
| `notes` | 研究限制、状态说明和反例提醒 |

## 关键联接键

- `cases.primary_source_id` → `sources.source_id`，辅源同理；`case_source_links.csv` 可直接用于生成来源侧栏。
- `cases.parent_event_id` → `cases.event_id`，再结合 `event_chains.csv` 避免母子项目重复。
- `cases.ags` → A端市镇 AGS 底图（保持补零）；`county_key` → 县级底图；`city_district` 应采用区级行政数据，不能用全市市镇点位冒充。
- `cases_map_ready.csv` 是 `cases.csv` 的严格子集且部分记录属于**已解除/已完成历史情况**；A端应再按时间轴或当前运营状态筛选。

## 证据限制与展示建议

1. 不将预算冻结金额视为实际节省；财政监管缩减贷款授权也不是工程已取消金额。
2. 无法确认的措施显示“提议/已批准待实施”，不显示为“已关闭”。
3. 财政紧缩之外的技术故障或人员短缺事件，即便同时导致停开，也需要独立核实财政因果关系。
4. 研究样本有搜集偏倚，不适合给联邦州作事件频次或严重程度排名。
5. 公共服务恢复、资助批准、紧缩措施被撤销，应以独立颜色或状态展示，不可全部视为负面事件。
6. `sources.csv` 中的网页/公报PDF实际内容应在生产环境或定稿前复核，原文不都离线收录。