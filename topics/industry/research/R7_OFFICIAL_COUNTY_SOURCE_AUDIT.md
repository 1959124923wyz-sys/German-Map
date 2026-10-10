# R7 官方县级制造业就业数据来源审查（2026-10-10）
本文件只保存查证过的可用来源及**未完成下载状态**，不是发布数据。正式就业底色必须是全国现行400县、工作地、纯WZ2008-C、2019与最近同口径年份原始人数。

## 线索 A：联邦就业局 BA
- 就业统计 https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Fachstatistiken/Beschaeftigung/Beschaeftigte/Beschaeftigte-Nav.html 指向德国/州/县数据库，包含工作地、WZ2008行业与社保就业。
- 行业 https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Themen-im-Fokus/Wirtschaftszweige/Wirtschaftszweige-Nav.html 专栏可按行业查看，需确认WZ C与时间一致。
- 区域报告 https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Fachstatistiken/Beschaeftigung/Beschaeftigungsverhaeltnisse/Beschaeftigungsverhaeltnisse-Nav.html 的 Regionalreport über Beschäftigte (Kreise) 有Wirtschaftszweige维度，但须逐表核查可比较年份和县位，不能把德国与州级PDF当400县。
- 文档 https://statistik.arbeitsagentur.de/DE/Statischer-Content/Service/API/API-BST-Zeitreihe.html 提供县级 EckwerteZeitreiheBST API 与CSV/XLSX/JSON，**Eckwerte并不自动具备纯WZ-C县级历史序列，不能把通用就业总人数冒充制造业就业**。
- **执行结果：截至本文件版本全国2019—2025县级WZ-C人数CSV尚未取得/验收，生产 county-employment.json 仍为零覆盖。**

## 线索 B：区域数据与统计核算
- Regionaldatenbank `42111-02-03-4` 需核实20人门槛与WZ-C字段、区域变更、保密格。2026-10-10尚未取得全国批量原始CSV；历史Regionalatlas ArcGIS尝试HTTP400已经归档。
- 图林根官方县级 `KR000303` https://statistik.thueringen.de/datenbank/tabWMAnzeige.asp?auswahlnr=&ersterAufruf=x&startpage=1&tabelle=KR000303&wmID=133210%7C%7C3 提供2019—2024县级 `Erwerbstätige nach Wirtschaftsbereichen`，但此页面可见行明确为 **Produzierendes Gewerbe (B–F)**；不是纯C。其就业人数（国民经济核算，包括非社保就业）与BA社保就业也不相同，因此不能拼入BA面板。该页面证实有县级历史但**不解决本项目定义的制造业衰退率**。
- Destatis全国年就业 https://www.destatis.de/DE/Themen/Arbeit/Arbeitsmarkt/Erwerbstaetigkeit/Tabellen/arbeitnehmer-wirtschaftsbereiche.html 有全国2019与2025“Verarbeitendes Gewerbe”就业，对宏观方向有帮助，但不可分派给县。
- 黑森GovData县级WZ https://data.gov.de/suche/daten/erwerbstatige-nach-wirtschaftszweigen-jahresdurchschnitt-regionale-tiefe-kreise-und-krfr-stadte 是州级来源，出版范围需要核验，不能以单州代全国。

## 线索 C：BKG行政区几何
- 官方ArcGIS https://tigis.bkg.bund.de/hosting/rest/services/VG250_KREISE25_Punkte_Grenzen/MapServer/0 数据层可查询AGS/GEN/BEZ/GF字段，Geometry Polygon；2025 VG250，400县候选。
- 已提交 `topics/industry/scripts/try_bkg_vg250_counties.py`，只在全部400 AGS相符时产出candidate；研究动作workflow `.github/workflows/industry-r7-bkg-research.yml`尝试下载并自动提交候选至**研究支线**。
- **截至本审计，未看到经校验写入 GitHub 的 candidate GeoJSON**；即使workflow成功触发，也不能把触发视作数据成功。项目底图仍是402历史县界 + 402→400 AGS规范映射。
- 需要保留官方授权与归属。最初下载失败时workflow应显示失败并保留artifact日志，不能保存残缺文件。

## 数据守则
1. 原始资料持久化后记录source URL、查询参数、下载日期、地域、WZ分类、行业门槛、就业类型、保密规则、AGS生效年。
2. 禁止杜撰缺失县就业；缺失不填0；如仅若干县有数据，其余全灰，不能改用新闻条数伪装官方就业收缩。
3. 全国数与BA县就业、Destatis企业场所就业和ETR总就业互不等价，比较前先统一统计对象和统计口径。
