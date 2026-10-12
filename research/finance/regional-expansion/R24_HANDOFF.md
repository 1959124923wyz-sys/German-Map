# 德国地图08 · R24 研究继任检查点（2026-10-10）

**唯一正式工作分支**：`research/finance-regional-expansion-20261010`；PR #36 **Draft／研究专用，暂不合并**。当前 `main` 已上线财政专题、包含原A+B事件170条与来源180条；不重复导入B线案例，不擅自更新网页或Pages。

## 研究数据已实际保存并在GitHub二次读取核实

### 1. 2023—2024全国市政综合债务
- 2023原始官方XLSX：7,336,842字节，SHA256 `af5b3e0ff66cd30f7566721028e57374bce2bffd1b1cb0fe3a870344b3bb53d0`，2023统计单位**11,896**（市镇10,771、联合管理机构831、县本级294）。2023年度的全部13个非城市州CSV均已实际保存于 `derived/integrated_debt_2023_by_state/DE-*.csv`；原始XLSX只在Actions 30日附件中，长期Git保存为分州派生CSV+哈希+原件下载地址。
- 2024原始官方XLSX：8,026,315字节，SHA256 `8712ff40e0a2dba71bc43c6a6fa720cdc847dd913e077c876aef5bc79e25198f`。**11,874**个不同统计单位（市镇10,750、联合机构830、县本级294），13州分表已由R12正式保存。
- 2023/24相同原始地区报告单位编码 **11,867** 个交集、2023独有29、2024独有7；匹配统计主体、双年原值和人口分别写入 `derived/integrated_panel_2023_2024/DE-*.csv`；`panel_audit.json` 已保存，验证通过。**147个名字或机构形式字符串变化列为人工核对**（包含常见缩写），不等于147次行政改革。任何同比增长率/县域合计不得直接由文件自动推导。

### 2. 全国2023县级核心预算债务（另一种口径）
- 官方Regionalstatistik表 `71327-01-05-4` 已实得 **44,435字节** 的 cp1252 原始CSV，SHA256 `28f034e26731bd538bfec5461a8375156be085b41ac33eb62798167a7b88b80b`，**原始CSV字节也已作为研究Git文件永久保存**：
  `derived/regional_core_debt/official_regional_71327_2023_raw_cp1252.csv`。
- 原表471条历史五位地区代码，73条为历史废止代码且2023年没有有效数字。与2023年另一份官方KRS名录对照后，398个活跃代码，其中**392个有效数值**、6个原表缺失，另有2个城市州名录特殊代码未出现。可用筛选表 `derived/regional_core_debt/county_core_budget_debt_2023_active.csv`、清理表和 `county_core_2023_active_audit.json` 均已核验。
- 指标严格为**县级范围对应的市镇及联合机构的核心预算债务**（官方地域汇总）而非综合债务；不可和包含市属公共企业持股债务的“综合地方债务”互换；2023数据也不能写为2025/26当前债务。

### 3. BKG 2025/2026官方行政边界与经验证实的2026自治变更
- 2025-12-31 BKG 官方原件70,627,276字节，SHA256 `df71d6a7ec0a0ca38e0559d9a90523a81c7948c74e7c7c3ddeab79041d1046f5`：县级400 AGS5，433个原始几何部分，研究GeoJSON `derived/bkg2025/county_boundaries_2025_simplified.geojson` 已保存 **4,482,113字节**。
- 2026-01-01 BKG 原件70,630,747字节，SHA256 `6b096eb4862b4eafda9294e425fb5a6d0e7773eb5815a4d4edc78b639ec2728f`：**401县级行政区、434原始几何部分**，新唯一代码 **06415（哈瑙）**；研究县级GeoJSON `derived/bkg2026/county_boundaries_2026_simplified.geojson` **4,487,653字节**。
- 2026-01-01 BKG **市镇级**含**10,939个不同AGS8**（11,094原始图形行）；与2024年市镇综合债务单元10,750条同码10,743、2024旧码7条不再出现；与2025 Atlas市镇AGS10,949条同码10,938，2025旧码11条不再出现，2026新有码1。10,939个市镇边界已用Shapely/pyproj提取为**16州的 GeoJSON 分片，总计28,993,287字节**：`derived/bkg2026/municipal_geometry_by_state/DE-XX.geojson`；`municipality_geometry_2026_audit.json`显示全部通过。
- 2026年的**行政区新码06415/市镇新码06415000**，而2024旧哈瑙市镇旧码06435014。不得在2026图层上直接把2024债务当作2026数值；跨年份编码和统计主体调整须另行人工确认。
- 两版边界、许可证、简化距离与面积均保存审计；原始官方ZIP通过MD5/SHA审核，Actions原件二进制附件仅保留30天，已保存Git的数据是GeoJSON、AGS、哈希和可重建脚本。页面应显著注明 `© BKG (2026) dl-de/by-2-0`、BKG及许可证链接和修改说明。
- **全部几何文件只在研究分支，没有进入现网**；各市镇独立简化会有微小边界缝隙，制作视觉地图需要回归测试。

## R24 最新探索：2024原年份地理边界（尚未标记完成）
- 2024-12-31官方VG250-EW旧版二进制目录：https://daten.gdz.bkg.bund.de/produkte/vg/vg250-ew_ebenen_1231/2024/ 。`build_bkg2024_ags.py`、专用研究Actions已建立，意在对照2024真实10,750个市镇综合债务实体。
- **第一轮Action因历史官方归档ZIP不存在旁路 .md5 返回404而失败**，失败日志已保存：`derived/bkg2024/last_run_status.json`。现已提交修复：若官方MD5缺失，将先获取ZIP、记录SHA-256供第二轮固定校验。**只有** `derived/bkg2024/municipal_2024_ags_audit.json` 真正在GitHub出现、且值通过校验才能视作完成；未验证前不能宣称已获取2024同年份县市几何。
- 仍缺2025年统一县市综合债务公开原表；目前最新公开全国详细综合地方债务为2024年（Statistikportal发布2025-12-02）。

## 数据校验方式与恢复路径

1. **从Draft PR #36恢复**：https://github.com/1959124923wyz-sys/German-Map/pull/36 。先打开本文本，再检查相应 `derived/*/last_run_status.json` 是否确实 `verified:true`。
2. 国家综合地方债务：`python research/finance/regional-expansion/tests/validate_2023_integrated.py`；历史同主体面板：`derived/integrated_panel_2023_2024/panel_audit.json`。失败时阅读各工作流诊断状态，不可“猜”GitHub上传成功。
3. 2023县级核心预算：`derived/regional_core_debt/county_core_2023_active_audit.json` 和原始cp1252 CSV；392条有值，非400条全有值。
4. 全国2026县级、市镇边界：`derived/bkg2026/county_geometry_2026_audit.json`、`municipality_geometry_2026_audit.json`；对应 `build_bkg2026_geometry.py`、`build_bkg2026_municipality_geometry.py` 重建。
5. 2024专版行政边界：检查 `derived/bkg2024/last_run_status.json`，对照是否新保存 `municipal_2024_ags_audit.json`，然后考虑按州生成2024完整市镇图层（与10,750市镇综合债务同年），这是高优先级下一步。
6. **发布前**须另外审计口径统一、2024行政码不匹配、2023/24人口分母差异、源文件许可证署名、地图图层大小/性能、桌面和移动端真实浏览器、用户现有简洁交互习惯，合并由维护线执行。研究支线不能自己触发Pages。

所有研究产物的类型分开：`verified_source`、`research_derived`、`not_published`，不对不存在的数据填0，不对不同的财政主体简单相加。
