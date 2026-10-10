# 工业地图 R7：尚未扫完的事件库与下轮核验索引
更新：2026-10-10。本索引是可恢复研究待办，不是已验证的新事件，更不能与220条主库合计。

## 研究总体进度与覆盖边界
欧盟 Eurofound ERM 德国专题页 https://apps.eurofound.europa.eu/restructuring-events/countries/Germany 当前显示约 **2024年137、2025年211、2026年252件**重组事件（动态页面，每年包含关厂、减员、破产、扩张、服务行业及重复修订，非制造业工厂全集），德国全期约2957件。严禁使用这几个年度“总件数”充当实际关厂数量；单篇事实页有时同企业重复、多年更新。R1–R6曾针对2025和2026抽样，R7新增2024—2025历史扫漏与后续反转案例，**仍非穷尽检索**。

## 优先补核候选（尚未逐件查重并写入事件库）
- 2024：Waldaschaff Automotive（原R2/R3已有公司，先查是否同址）；Siltronic 400；UPM Hürth 135及Nordland Papier 210（与R5D Ettringen不同厂）；Westfalen Werke 280；Solarwatt 190/500（2024两次公告可能同一重组）；Next.e.GO Mobile 200；Kico（同一企业媒体数字150与搜索摘录1400矛盾，必须打开原factsheet）；Trevira 210；Rodenstock 230；Bosch Rexroth 153；Tadano 249；Coca-Cola 420；AEM Dessau 150；Recaro 200；BBS Autotechnik 240；Putzmeister 280。逐一检查制造业属性与投资者/后续存续。
- 2025：Optovision 230、Ceratizit 230、Yanmar Compact Equipment 290、KMS/Solingen已录R7E、Leica Biosystems 90、FWB Kunststofftechnik 132、PCI Augsburg 105、Kusch+Co 110已录R7E、NIDEC GPM 270、Spreewaldkonserve 200、CSL Innovation 500、Konradin Druck已录R7E、Kusch+Co已录R7E、Stoll已录R7D、Kabel Premium已录R7C、Schlaraffia已录R7C。多个集团将非生产减员与生产合并，不能整个转为红点。
- 2026：追踪2025计划落地状态，特别NEVEON两厂、Feintool修订、BSH两厂（2028仍属计划）、Vileda（2026中）、König+Neurath、Engmatec、Etkon部分外迁及既有R1早期大厂更新。引进公司、工会、州政府及法院公告独立确认。
- 对每条按 **原始厂址+同一改造计划** 去重，保留事件原始公告、最新状态、工厂/集团岗位分配、生产与研发后勤区分、县AGS、二次证据及时间。
- 对“已超计划结束日期”但无新证据的事件保持announced/under_implementation，不能依日历擅改为reported_completed。
- R7已核实的关键反例：Feintool Sachsenheim 2024拟整厂退出，2025-08-22公司正式公告保留工业应用业务；同集团原两厂200人不能全部丢到Sachsenheim。Kusch+Co Hallenberg 2025-12确有停产、2026-05又有后续报道，方可更新确认。

## 官方来源及恢复入口
- ERM德国分年索引：https://apps.eurofound.europa.eu/restructuring-events/countries/Germany
- Feintool修订：https://www.feintool.com/insights/feintool-reaches-agreement-with-employee-representatives-in-sachsenheim-on-realignment-of-business-unit-stamping-europe-part-of-production-in-sachsenheim-to-remain-in-operation/
- 独立支线：`research/industry-r7-evidence-20261010`；Draft PR https://github.com/1959124923wyz-sys/German-Map/pull/42
