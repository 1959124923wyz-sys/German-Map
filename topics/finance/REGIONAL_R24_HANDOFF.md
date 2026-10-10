# 财政08｜2026-10-10 研究数据分批上线交接

## 研究分工与去重
- 财政B的R1–R7 170条地方事件、180条来源及72条地图候选已经在主分支，未重复导入、未推断发生频率。
- 这次正式新接入的全国县市债务资料来自财政区域研究支线 Draft PR #36 的R24核验结果，而不是财政B追加的新事件；研究支线原件保留，未经审核的区域指标暂不迁移。
- 资料只进入县市点选详情，不新增全国热力图模式，继续以2025年13个非城市州的地方政府人均收支差额作默认底色。右侧地方事件仍是默认关闭的独立勾选图层。

## 已入主线、可重复构建
| 文件 | 记录与口径 | 地图用途 |
|---|---|---|
| `research/finance/published_20261010/county_core_budget_debt_2023_active.csv` | Regionalstatistik 71327-01-05-4，2023年398个县级地区；392有效人均值，6缺失 | 点击县市区域显示2023年县域**市镇及联合管理机构核心预算债务**；不是该县政府本级债务，更不是综合债务 |
| `research/finance/published_20261010/independent_cities_official_2024.csv` | Statistikportal 2024年102个**非县辖市**综合债务以及分开的税收能力、短期借款佐证 | 县市详情中新增2024年城市综合债务折叠摘要；并不与县域核心债务相加 |
| `topics/finance/data/finance-regional-evidence.js` | 上述精简发布数据，未包含虚构缺失值 | 浏览器离线加载 |
| `topics/finance/data/build_finance_regional.py` | 确定性原始字段转换、主体及缺失检查 | 可复现构建 |
| `topics/finance/tests/validate_finance_regional.py` | 数量/来源/缺失/年份/内容一致性 | CI发布前校验 |

来源：
- https://www.regionalstatistik.de/genesisws/downloader/00/tables/71327-01-05-4_00.csv
- https://www.statistikportal.de/sites/default/files/2025-12/Integrierte_Schulden_der_Gemeinden_und_Gemeindeverbaende_2024_Tabellenband_0.xlsx
- PR #36: https://github.com/1959124923wyz-sys/German-Map/pull/36
- R24来源审计：`research/finance/regional-expansion/R24_HANDOFF.md`（仅在研究支线）

## 当前刻意不发布的研究资料
- 2023—2024年约11,867个“同码财政报告单位”的变化率；人口分母/实体改革未经统一核验。
- 2024年10,750市镇综合债务全域多边形图；2024同年的官方地理边界仍未完全核准。
- 2026年10,939市镇边界与2024年债务错期直接覆盖，尤其**哈瑙2026年新代码06415**。
- 混合范围的2025年58条县市债务候选，以及规划区数据、初步决算、预测值的全国同色比较。
- 2024城市税收能力与2023县短期借款，原值随来源表保留，但不混合展示为同一个“财政风险”分数。

## 运行与恢复
```bash
python topics/finance/data/build_finance_regional.py
python topics/finance/tests/validate_finance_regional.py
python topics/finance/tests/smoke_finance_browser.py  # 需本地静态服务+Playwright
```
如需继续扩展全国市镇2024债务地图，请先让PR #36完成2024同版官方几何和AGS逐个匹配，再由维护线以独立PR审查。恢复当前上线成果使用本次独立PR和主线Git提交；不可将PR #36完整直接合并进生产分支。
