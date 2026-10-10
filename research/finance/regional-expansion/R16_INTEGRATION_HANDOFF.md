# 德国财政08｜R15–R16 研究接力记录（2026-10-10）

工作分支：`research/finance-regional-expansion-20261010`；PR #36 保持研究性质，**不得自动合并**。主站 `main` 的财政页面独立上线，包含此前A+B财政事件170条/来源180条/基础候选72条。本研究不改线上页面。

## 本批次实际已验证的数据

1. **2023年官方全国综合市政债务源XLSX成功下载并校验**：`https://www.statistikportal.de/sites/default/files/2024-11/Integrierte_Schulden_der_Gemeinden_und_Gemeindeverbaende_2023_Tabellenband_0.xlsx`，二进制7,336,842字节，SHA-256 `af5b3e0ff66cd30f7566721028e57374bce2bffd1b1cb0fe3a870344b3bb53d0`。结果见 `derived/integrated_2023/source_2023_download.json`。原始二进制保留于Actions 30日附件，非Git文本文件。
2. 2023年官方Excel全19个工作表已解析检查，其中**13个非城市州的州分表**合计**11,896条不同报告单位**，其中市镇10,771、县政府本级294、联合行政机构831。**2023的萨尔州58条必须计入，不能以每表超过100行为准筛选州表。** 结构审计见 `derived/integrated_2023/workbook_2023_structure_audit.json`。
3. 与2024年11,874个同类报告单位的原始12位/9位/5位代码比较，稳定存在**11,867个代码**；2023独有29、2024独有7。检查点：`derived/integrated_2023/integrated_2023_vs_2024_entity_audit.json`；不同年债务比率尚未经过行政区变化及2022人口普查后人口基数核对，**稳定代码不等于可直接同比**。
4. 2023数据已经准备`normalize_integrated_2023.py`，要由研究支线Actions执行、校验并回写`derived/integrated_debt_2023_by_state/`；只有**确认这些CSV真实出现在GitHub分支后**才称为完成。
5. 2025 BKG边界来源官方文件目录与MD5已核验：文件 `vg250_12-31.utm32s.gpkg.ebenen.zip`，官方 MD5 `e6b4cf28d4b83557b4d6e3236713dec0`。升级了`build_bkg2025_ags.py`以绑定校验值及2025 Atlas县级前缀，并升级Actions使失败原因写入`derived/bkg2025/last_run_status.json`。**尚未取得正式GitHub保存的边界匹配审计以前，绝不宣称已完成。**
6. 行政区大变动：黑森州官网证明**哈瑙于2026-01-01脱离Main-Kinzig-Kreis，成为非县辖市**。来源：https://innen.hessen.de/kommunales/kommunen/gemeinden-und-landkreise 以及 https://www.hanau.de/rathaus/politik/kreisfreiheit/index.html 。因此BKG **2025-12-31** 地图即使通过100%编码检查也不能冒充2026-01-01以后区划。

## 已确认的外部补缺来源（状态精确区分）

- 全国县级核心预算债务（**非综合债务**）：Regionalstatistik EVAS `71327-01-05`，官方区域统计目录明示县级、12月31日、核心预算而不含关联公共企业；候选下载 `https://www.regionalstatistik.de/genesisws/downloader/00/tables/71327-01-05-4_00.csv`。**目前仅确认官方目录与URL，尚未获得经SHA及字段校验的全国原件**。
- 2023官方州级综合债务：https://www.destatis.de/DE/Themen/Staat/Oeffentliche-Finanzen/Schulden-Finanzvermoegen/Tabellen/integrierte-kommunale-schulden-nicht-oeffentichen-bereich-presse_2023.html 。可作为2023州级结果交叉核对，不能把官方全国金额直接与所有市镇/联合体/县本级数值相加验证。
- 2022年市镇综合债务官方出版物：https://www.destatis.de/DE/Themen/Staat/Oeffentliche-Finanzen/Schulden-Finanzvermoegen/Publikationen/Downloads-Schulden/integrierte-schulden-tabellenband-5713201229005.html 。**已核验出版物存在，原始XLSX尚未获取/校验**。
- 汉瑙自2026独立县：https://innen.hessen.de/presse/innenstaatssekretaer-uebergibt-genehmigung-fuer-hanau-auskreisung 及 2026实际服务：https://www.hanau.de/rathaus/politik/kreisfreiheit/index.html
- BKG 数据许可：https://gdz.bkg.bund.de/index.php/default/open-data/verwaltungsgebiete-1-250-000-stand-01-01-vg250-01-01.html 。地图需标 `© BKG (数据获取年) dl-de/by-2-0`、链接BKG与授权许可，改编数据应披露修改。

## 严禁的研究错误

- `derived/quality_audit.json`是R11历史快照，仍有“2024工作簿未下载”的旧说法；新版R12/R13和本交接记录优先，**不要篡改旧文件假装当时已完成**。
- `derived/integrated_debt_2023_by_state/`只代表2023**不同法律报告主体的原始行**，不是全国县域综合债务总量；不能用 `county_ags5`把市镇、联合机构和县本级简单相加。
- 非城市州13州的市镇综合债务与柏林/汉堡/不来梅州-市合体财政口径不同；不能把城市州显示为0。
- 2024 Deutschlandatlas 缺失税收能力仍为204条哨兵缺失，不是0。2023 county short cash credits 120条为合法零值。
- 2023/24居民人口基数存在不同调查基准的可能，任何“人均债务同比增长率”必须有一致的相同人口口径才能发布。
- B侧事件研究库已被主站收录，不得重复叠加；事件数量不能代替地区财政压力评分。

## 断点恢复步骤

1. GitHub 打开 Draft [PR #36](https://github.com/1959124923wyz-sys/German-Map/pull/36)，检查`derived/integrated_2023/`、`derived/integrated_debt_2023_by_state/`、`derived/bkg2025/`是否存在实际Action回写产物。
2. 若2023数据已生成，运行 `python research/finance/regional-expansion/tests/validate_2023_integrated.py`；核对2023原件SHA、11,896条报告单位及11,867个跨年稳定代码。
3. 如BKG尚无 `official_counties_2025_audit.json`，读 `derived/bkg2025/last_run_status.json` 错误并修复脚本/下载流程；未得到成功标志前只保留旧地图。
4. 若要做全国县市涂色，须先取得官方统一主体口径的县级财政数值；不得借用县本级或跨实体合算。
5. 本研究分支只回写 `research/finance/regional-expansion/` 与专门测试/研究流程；最终维护线负责合并、地图性能与浏览器回归验收。
