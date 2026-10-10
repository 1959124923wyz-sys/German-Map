# 德国住房危机地图｜阶段交接（2026-10-10）

**独立分支**：`research/housing-crisis-20261010`（切勿把研究任务直接提交主分支）
**GitHub**：https://github.com/1959124923wyz-sys/German-Map/tree/research/housing-crisis-20261010

## ✅ 已证实远端提交并通过 Actions

| 工作流 | 最新成功 run | 数据交付 |
|---|---|---|
| Deutschlandatlas HA26 官方县级统计 | [38037006857](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037006857) | `topics/housing/data/atlas-counties.json`; `research/housing/data/deutschlandatlas_ha26_housing_counties.csv`; `research/housing/qa/ha26_join_audit.json` |
| HA26 市镇联合体实际租金 + 原始 GREIX 工作簿 | [38037204839](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037204839) | `research/housing/raw/{deutschlandatlas_vbgem1222_ha26.csv,greix_city_metrics_q2_2026.xlsx}`; `research/housing/data/vbgem_existing_rents_2022.csv`，QA与SHA256校验 |
| GREIX 月度名义租金 | [38037349072](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037349072) | `topics/housing/data/greix-city-series.json`，`research/housing/data/greix_nominal_monthly_city_series.csv`，月度审计 |
| 县级2022—2025住房存量和人口（第三方转录+核验） | [38037411190](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037411190) | `topics/housing/data/stock-counties.json`，原始CC BY 4.0 JSON快照及QA |

上方 run 均确认为 `completed/success`，相关生成数据确认为 GitHub 分支可获取；**没有修改 main**。中途曾有失败运行（编码规范与 GREIX 年度数据混排），均修正后重跑成功，**以最新成功运行作为阶段验收**。

## 数据覆盖和统计限制（对外不得误读）

1. **官方 Deutschlandatlas HA26（2026-10-08）**：两个官方原始Kreis CSV各有 **400** 个实际县级地区；现有旧底图有 **402** 个历史行政多边形，其中 **399** 个可以直接匹配，六项县级指标均有399个有效可映射数值。官方新县 `03159` 在旧地图中缺席，旧地图 `03152`、`03156`、`16056` 无当前地区对应值。必须后续进行边界版本协调而非简单名称匹配或伪造拆分值。
   - 2025新挂牌/重复出租净冷租金 `preis_miet`（€/㎡）。
   - 2022空置率 `wohn_leer`、2022业主自住房家庭占比 `wohn_eigen`（%）。
   - 2022人均住房面积 `fl_wohn`（㎡/人）。
   - 2024新建住宅可再生供暖占比 `heiz_wohn`（%），2022存量住宅可再生供暖占比 `heiz_wohn_best`（%）。
   - `-9999` 和未匹配均转 `null`，不得填0。
2. **2022存量租金**：市镇联合体层级 **4600条**，其中 **4396条有效**。不可直接当作全国县级数据；与2025新挂牌租金不是同一种市场样本。
3. **GREIX Q2/2026 工作簿**：**6612条名义月度观察，截至2026-06**；工作簿中有 **38组名称，其中“Greix”为聚合指标，故是37个具名城市/地区 + 1个聚合序列**。数据仅供所覆盖城市/地区观察长期趋势，绝不可贴成全国400县官方时间序列；剔除了实际值（inflation_adjusted=1）和非月度记录，均保留来源。
4. **2022—2025县级住宅存量、人口**：通过第三方公开数据再发表 `mietkautionskonto.info` 取得 **400条**；**二次转录来源非Destatis原始接口**。核验2025年全国存量总数**43,951,556套**以及Flensburg/Kiel/Lübeck/Neumünster四地区原始值。与HA26县级空置率399区对应，差异中位数**0.1百分点**，最大**1.0百分点**，**不同分母/指标定义不得擅自合并**。可展示“千人住房套数”和“2022—25住房存量增长”但二者皆不是直接住房短缺指标。
5. **尚未取得：**全国400县级2026年集中安置无住房者完整表、逐县住宅竣工序列、可比的县级家庭收入/租金负担比、系统性地方住房事件。需要继续搜集，不得将这些标记为完成。

## 复现与恢复操作

在仓库根目录（可借GitHub Actions独立环境联网）：
```bash
python research/housing/build_deutschlandatlas.py
python -m pip install openpyxl
python research/housing/probe_secondary.py
python research/housing/build_greix.py
python research/housing/build_stock_proxy.py
```
各脚本会明确校验字段、数量与来源并生成审计；任何失败**禁止提交部分生成文件**。源数据快照存在 `research/housing/raw/`，已处理CSV在 `research/housing/data/`，供页面使用的JSON在 `topics/housing/data/`，核验在 `research/housing/qa/`。

当前主站模板：`topics/finance/`，共享Leaflet和 `data/germany-{states,counties-display}.geojson`。下一步建议先建立 `topics/housing/index.html` + `topic.js` + `topic.css` 的独立专题原型、严格复用指标年份和来源，再扩县级竣工/无住房人员/城市事件证据。默认色阶：2025县级挂牌租金；下拉切换其他各自独立指标；没有任何合成危机指数；同历史地图的未匹配3县保持灰色。

### 恢复时首先做

- `git fetch origin research/housing-crisis-20261010 && git checkout research/housing-crisis-20261010`；
- 检查以上四个成功 run 和 `research/housing/qa/*`；
- 不更改 `main`、共享底图文件或其他地图模块；仅此分支继续追加；
- 每一新批必须：源码+原始出处+核验+记录状态，远端确认 commit/Action 成功，再更新本交接文档。


## ✅ 第二阶段追加（2026-10-10，本条经远端校验）

### 住房危机地图独立可运行原型

- `topics/housing/index.html`、`topic.css`、`topic.js`：沿用全站深色导航、Leaflet + OpenStreetMap 左图右栏，默认地图是**2025挂牌租金**。下拉九个彼此独立的指标、点击县市、联邦州下拉、全国复位、县市排行榜和原始出处链接均已建立。没有合成危机评分，也没有把事件“数量为零”误当无危机。
- 自动 Chromium 桌面/手机回归：[Run 38037812213（PASS）](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037812213)，校验402地图图形、399实际租金单元、16州选择、九种指标、缺失逻辑、住房存量交叉层、县市点击和复位；截图上传为该run的artifact。后续还有包含萨克森历史资料面板的回归重跑，以最新成功 run 为准。
- 注意：**分支原型尚未合并 main，也没有宣称已在公众 GitHub Pages 上线**。本仓库长期主站运行路径仍由主分支管理。

### 萨克森2022—2026官方安置无住房人员

- [州统计局原始出处](https://www.statistik.sachsen.de/html/untergebrachte-wohnungslose-personen.html)，[原始2026县市 XLSX](https://www.statistik.sachsen.de/download/soziales/statistik-sachsen_untergebrachte_wohnungslose_kreise.xlsx)，[2022—2026年连续时间序列 XLSX](https://www.statistik.sachsen.de/download/soziales/statistik-sachsen_zr_untergebrachte_wohnungslose.xlsx)。原表与SHA256目录：`research/housing/raw/saxony_homeless_*.xlsx`、`research/housing/qa/saxony_homeless_workbook_layout.json`。
- 官方工作簿采集 [Run 38037868308（PASS）](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037868308)，五年系列抽取与当年原表核对 [Run 38037938196（PASS）](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037938196)。
- 已交付 `research/housing/data/saxony_official_homeless_2022_2026.csv`、`topics/housing/data/saxony-homeless-counties.json`、`research/housing/qa/saxony_homeless_audit.json`。
- 全州13个县市的2026年1月31日受安置无住房人数经保密取整共计 **5590人**，与州统计局当年官方全州总数5590一致；每县均有2022—2026五期记录，共65个县·年观测。严格标注“仅萨克森13县、并非德国全国、仅受安置人员、保密5人取整、地区聚合不保证完全可加”。
- 页面只在点击萨克森真实县市时显示可折叠五年记录，其他州完全不展示萨克森数值，不做虚假的全国无住房地图。
