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


## ✅ 第三阶段追加：全国住房建设与无住房者底图（2026-10-10）

**本节覆盖上文“尚未取得全国数据”等早期研究状态。之前的表仍作为历史记录保存，不应误以为仍未完成。**
本节全部列明的生成数据已在独立分支经过 GitHub Actions `completed/success` 和远端文件校验，未合并主分支。

### 1. 修复全德住房地图400县行政区边界与自动化测试

- 数据现以 `topics/housing/data/germany-counties-2024.geojson`（德国联邦测绘署BKG经Deutschlandatlas GIS服务发布的VG250县级2024地图）为**住房专题单独使用的400县底图**，与官方HA26县级统计 `topics/housing/data/atlas-counties.json` **400/400 AGS匹配**。不触碰其它主题仍使用的402县旧底图。
- BKG 地图专项校验：[run 38038891243 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38038891243)，审计 `research/housing/qa/bkg_2024_400_county_geometries.json`，来源版权 `© BKG (2026), dl-de/by-2-0`；图形只将经纬度精度减至5位小数、简化非空间属性，不虚拟调整边界。
- HA26 官方数据保存与改版后测试：[run 38039674961 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38039674961)。此前failed的校验断言仍用402，现在改400后已重跑成功。
- 页面已采用新400县矢量图形，2025挂牌租金、2022空置、自住比例、2023居民可支配收入等指标仍各自独立；无合成“住房危机指数”。新增层数后最新真实Chromium桌面和移动端：[run 38040471801 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38040471801)。此run验证**12项独立选项**、租金400县、全国无住房者394县数值、全国2023年新建住宅竣工400县数据，以及州/县切换、萨克森和北威州地方档案。

### 2. 德国全国2025年获安置的无住房人员（400县，394县有数值）

- 发现GovData政府数据门户公布了**无需API token的公开静态官方源**：`https://genesis.destatis.de/genesisWS/downloads/00/tables/22971-0080_00.csv`，官方数据为Destatis GENESIS **22971-0080，统计时点31.01.2025**。它**不是2026年县级数据**！2026年德国全国总数官方已公布为452,910，但静态县表此次只含2025年。
- 官方原始文件 `research/housing/raw/destatis_22971-0080_national_counties.csv`；解析 `research/housing/build_destatis_homeless.py`，输出 `research/housing/data/destatis_sheltered_homeless_counties_2025.csv`、`topics/housing/data/germany-homeless-counties-2025.json`、`research/housing/qa/destatis_homeless_2025_county_audit.json`。
- 来源表有交叉分类（国籍×性别×年龄），**只提取三个维度均为Insgesamt的列index 86**，严禁累计所有分组导致重复计算。按当前400县AGS精确匹配，有 **394县数值 / 6县缺失**，全部为5人取整，严格保留缺失。逐县有效值加总 **474,690人**，官方公布2025全国约**474,700人**（差10人，符合分县取整误差）；萨克森13县2025年数字与此前单独独立来源逐项比对**13/13完全一致**。
- 官方全国2025校验来源：https://www.destatis.de/DE/Presse/Pressemitteilungen/2025/07/PD25_246_229.html 。2026全国约452,900（GENESIS表精确到5人为452,910），来源：https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/06/PD26_222_229.html 。2025和2026比较亦受报告覆盖与口径影响。
- [全国下载run 38039968017 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38039968017)，[全国县级归并与全国总量交叉验证run 38040205063 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38040205063)。
- 本指标只包括获得临时安置的无住房人员；街头露宿者、住亲友家者等隐性无住房者不在此统计，**绝对人数不应被解释成“某县住房危机程度”**，也不得将全国2026总量伪装为2026县级分布。

### 3. 全国2023年新建住宅建筑竣工住房（400县，有效数值400）

- 官方各州与联邦区域数据库Regionalstatistik表 `31121-01-02-4` 免费公开直链：`https://www.regionalstatistik.de/genesisws/downloader/00/tables/31121-01-02-4_00.csv`。GovData目录称全国县级表，但这份静态资源**最后更新时间27.11.2024、仅含统计年度2023**。不是2025数据。
- 原表 `research/housing/raw/regionalstatistik_31121-01-02-4_national_counties.csv`，解析程序 `research/housing/build_regionalstatistik_completions.py`，输出 `topics/housing/data/germany-residential-completions-2023.json`、`research/housing/data/regionalstatistik_new_dwellings_counties_2023.csv`、`research/housing/qa/regionalstatistik_2023_completions_county_audit.json`。
- 原表多列重叠类别，仅提取 **Wohnungen in Wohngebäuden | Insgesamt | Anzahl**，同时核对1套、2套和3套及以上分类构成，避免重复统计；柏林和汉堡只有一个县级行政区，原表仅公布两位州级编码 `02` / `11`，因行政范围**完全一致**，分别正规化为 `02000` / `11000`，不把同样操作用于含两县级市的Bremen。
- 验证全德 **400/400县有数值**，合计 **257,241套**，对照官方德国全国数**257,241套**，误差**0**；该数仅指**新建住宅建筑**内竣工的住房套数，不等于所有新房交付/改扩建/非住宅楼宇内新增居住单元。此数据有全国维度，但**年份旧于已收集的北威州2025年53县新建住宅竣工数据**。
- [官方原始表存档run 38040262880 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38040262880)，[新住宅竣工400县解析与全国总量验证run 38040396758 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38040396758)。
- 新增县级地图切换指标 `completed_dwellings_new_residential_buildings_2023`，选择年份独立，有独立原始来源说明；不得用旧静态表冒充2025。

### 4. 官方Zensus 2022萨克森地区住房、家庭与空置原始证据

- 新增德国萨克森州统计局原始**4份**Zensus2022工作簿：`research/housing/raw/saxony_zensus2022_{county_buildings,county_households,all_buildings,vacancy}.xlsx`。
- 包含州内13县详细住宅和家庭统计、全州住宅建筑普查和空置原因专题，来源入口 `https://www.zensus.sachsen.de/zensus-2022.html`，由 `research/housing/probe_saxony_zensus2022.py` 下载。文件结构/各工作表维度QA `research/housing/qa/saxony_zensus2022_workbook_inventory.json`。
- [原始表下载与校验run 38039904638 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38039904638)。**这只是保存原始工作簿和结构审计，未将未审校的空置细分数值公布为地图指标。**

### 5. 下一阶段优先事项与严格口径

1. 寻找 **2024/2025 全国400县新建住房竣工年份**，静态公开的Regionalstatistik直链目前仅2023。既有北威州2025县表可作为新数据校验，不得覆盖2023全国数值。
2. 寻找2026全国400县**获安置无住房者**同口径下载表；GENESIS交互表已有2026国家数据，但现有静态 `22971-0080_00.csv` 仅2025。勿将现有2025县级数字贴成2026。
3. 整理萨克森2022年各县可用于实质解释的**长期空置与可出租空置、实际存量租金**字段，保留源表注释及保密符号；继续寻找Destatis Zensus全国 `Regionaltabelle Gebäude und Wohnungen` 原始机器CSV/Excel（约20MB）。
4. 县级真实家庭租金负担（租金/家庭净收入）目前没有一致可验证的全国400县序列。Destatis官方2022微观住户调查德国平均为**27.8%**，不等于县级或2025年指标；禁止将2023人均地区可支配收入与2025挂牌租金简单拼成“县级负担率”。
5. 局部事件仅凭来源实证精确位置才能加坐标；先保持简洁地图，不制造虚构住房事故或多余图层。

**断点恢复**：检出 `research/housing-crisis-20261010`；阅读 `research/housing/HANDOFF.md` 文末第三阶段；检查以上成功 Action/审计；地图入口 `topics/housing/index.html`；独立原始下载脚本和回归脚本都在 `research/housing/` 与 `topics/housing/tests/`。新改动每批先提交GitHub，确认SHA与Actions结果，再更新本交接文档。**本分支原型尚未合并或发布到主站**。

## ✅ 第四阶段追加：Zensus 2022 全国400县住房普查深挖（2026-10-10）

**严格记录：以下四组采集、字段审计和前端回归均有 `completed/success` 的 GitHub Actions 证据，数据已实际存在远端研究分支；旧交接中“仍缺全国县级存量租金、空置结构细节”的条目已经过时。** `main` 未合并或修改。

### A. 德国联邦统计局官方完整2022住房普查，全国400县、全级别历史地域

- 原始权威下载：`https://www.destatis.de/static/DE/zensus/gitterdaten/Regionaltabelle_Gebaeude_Wohnungen.xlsx`，Zensus 2022住房建筑普查区域表，约 **21,451,209字节**，SHA256 `82da8578a4657e20752b436a756ed27846c77f96e3f7333bdea7f4fe29a8b551`，统计时点 **2022-05-15**。
- 源文件：`research/housing/raw/destatis_zensus_2022_regional_housing_national.xlsx`，原始全德地区表另包含市镇与市镇联合体记录，**不得与县级数值相加**。
- 全国原始工作簿采集并保全：[run 38042015961 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38042015961)。字段结构 `research/housing/qa/destatis_zensus2022_national_housing_workbook_schema.json`。
- 县级机器表规范化处理程序：`research/housing/build_destatis_zensus_counties.py`，准确识别 `Regionalebene=Stadtkreis/kreisfreie Stadt/Landkreis` + 五位县级 `_RS`，**400/400** AGS和官方2024 BKG 400县编码完全对应。生成 `research/housing/data/zensus2022_official_400_counties_{dwellings,buildings}.csv`，全量字段 `topics/housing/data/zensus2022-county-archive.json`。机器表有**89个住宅指标字段、47个建筑指标字段**。县级提取 [run 38042183940 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38042183940)。
- 对每个简写字段由原始格式表查回德文分层标题，严禁靠代码猜含义：`research/housing/probe_zensus_column_labels.py`、`research/housing/qa/zensus2022_official_housing_column_codebook.json`，[run 38042252131 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38042252131)。

### B. 新增全国2022年真实存量租金、长期空置及可入住结构

- 计算脚本 `research/housing/build_zensus_housing_indicators.py`；原表逐县记录和分母验证输出 `research/housing/data/zensus2022_official_district_rents_vacancy_breakdown.csv`；供地图页面使用 `topics/housing/data/zensus2022-housing-indicators-counties.json`；详尽审计 `research/housing/qa/zensus2022_rent_vacancy_400_county_audit.json`。
- **各项均400/400县有效**。原始官方机器代码与意义：
  - `QMMIETE` = 2022年实际已出租住房平均净冷租金（欧元/㎡），与2025年互联网挂牌租金**不具有直接同比可比性**；
  - `LEQ` = 2022 Zensus总体住房空置率（保留官方原值，不等同于BBSR另一个定义）；
  - `ETQ` = 2022 Zensus业主居住份额（官方原表定义的 Eigentümerquote，注意与HA26 `wohn_eigen` 具体统计对象可能不同）；
  - `LEERSTAND_INSGESAMT` = 已空置的住房套数；
  - `LEERSTAND_DAUER__4` = 连续空置**至少12个月**套数，除以 `LEERSTAND_INSGESAMT` 得“空房中长期空置的比例”，**不是全部住房空置率**；
  - `LEERSTAND_GRUND__1` = **三个月内可供入住**的空房，除以 `LEERSTAND_INSGESAMT` 得“空房中较快可入住的比例”；也保存相对于所有住房的比例，但**不是可出租房源/市场活跃空置率**；
  - `LEERSTAND_GRUND__2…6` = 施工中或计划施工、拆除、出售、未来自用与其他空置原因，原始套数均保留。
- **全国住房套数验证**：县级 `GEBAEUDEART_SYS_1` 合计 **43,106,558套**，与普查全国原值 **43,106,589套**相差 **-31套**。保密扰动致各分类/县汇总可能相差少量（最长空置期子类按县最大偏差12套、原因子类最大13套）。不强制要求按类别严丝合缝汇总，也不擅自篡改。
- **存量租金独立交叉核验**：Flensburg 6.96 €/㎡、Kiel 7.64、Lübeck 7.47、Neumünster 6.22，同此前独立取得的德国地图集市镇联合体租金文件四地逐一相同。
- 已实际通过构建任务 [run 38042356410 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38042356410)，无缺失值编造。
- 县级实值JSON与CSV之外，所有地区均可在完整归档 `zensus2022-county-archive.json` 查看原始字段。

### C. 地图原型更新与客户端 QA

- `topics/housing/index.html`, `topic.js` 新增3个可切换的全国县级地图指标：
  1. **2022年实际存量租金** `existing_cold_rent_2022_eur_m2`
  2. **2022年空置至少12个月占全部空房比例** `vacant_12mo_plus_of_vacant_2022_pct`
  3. **2022年三个月内可入住占全部空房比例** `vacant_available_3mo_of_vacant_2022_pct`
- 现在共有**15个互不混合的指标选项**，但页面默认仍仅显示2025挂牌租金主图，其他统计通过一个下拉菜单切换；没有新增独立地图浮窗或“危机综合评分”。
- 新来源归属于Destatis Zensus 2022原件，统计年份、分母、与挂牌价不同口径的限制同时进入右侧说明和方法展开抽屉。
- Chromium完整桌面+手机实际测试：[run 38042441415 PASS](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38042441415)。测试覆盖400县2022住房普查数据有效性、独立来源、15项指标、全德其他层、州县选择、萨克森与北威档案、移动端不溢出。

### D. 尚存缺口，后续研究行动

1. **2024及2025年全国400县级竣工序列**仍未取得，全国静态Regionalstatistik 31121-01-02-4接口原始文件只含2023年，现有2025北威州53县可留作交叉校验。应逐州搜集原始表或找到全德政府机器接口的新快照；不得用2023数据冒充2025。
2. **2026年全国400县的受安置无住房者**县级细分仍缺；2025年官方县级表394有数值，但2026全国汇总452,910不等于2026县级序列。按地区统计站和2026 GENESIS数据库进一步查找，统计日与分类必须一致。
3. 本次得到的“预计3个月内可入住”空置原因不等于Zensus 2022 **4000W-0002 Marktaktive Leerstandsquote (Geschosswohnungen)**；后者另一指标已找到全国总量2.3%，若需要逐县序列应独立取得原始单独表，并明确只涉及多单元公寓住房。**不要用本次新衍生指标假称是4000W-0002。**
4. 全国可比的“县级实际家庭住房负担率”仍待独立微观调查，严禁拼接2025挂牌租金与2023地区人均可支配收入推算住户负担率。
5. 可深入普查的建成年份、租金价位段、能源与房屋拥有主体等89+47源字段；需要继续做单位解释、跨指标一致性审计，避免把加总过的多口径分组当作独立住房数量。

**恢复**：从远端 `research/housing-crisis-20261010` 检出，先读本文第四阶段；工作簿位于 `research/housing/raw/destatis_zensus_2022_regional_housing_national.xlsx`；运行 `build_destatis_zensus_counties.py` + `probe_zensus_column_labels.py` + `build_zensus_housing_indicators.py` 即可完全复建新的400县级指标；使用 `topics/housing/tests/smoke_housing_browser.py` 及CI验证。所有批次仍坚持源文件、SHA256、代码、QA、分支提交的保全原则。
