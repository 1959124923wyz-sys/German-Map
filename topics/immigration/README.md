# 德国外国籍人口地图（German-Map 05，v12）

上线时间：2026-10-09。独立静态HTML，无API密钥，不读取或修改主站犯罪数据。主站导航入口在根目录 index.html。

- 统计主体：外国籍人口（Ausländische Bevölkerung），2025-12-31 AZR登记，全国14,070,225人；不能误称“非法移民”。
- 包含16州2018—2025年人口历史（人数），2025年人口统计推算的外国籍人口占比（**不同统计体系**），及4州共25条原始县级AZR记录（其他县无资料不得插值）。
- 主页面：topics/immigration/index.html（由本地v12测试通过的离线HTML迁移；生产版开放对主项目真实州界GeoJSON的按需读取）。
- 在线地图会优先加载主项目 ../.. /data/germany-states.geojson（实际路径 ../../data/germany-states.geojson），16州边界合法匹配后着色；若失败则退回真实德国轮廓与州府参考点。主图不展示虚构县界。
- 统计局州级数值：https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Migration-Integration/Tabellen/auslaendische-bevoelkerung-bundeslaender.html
- 梅前州县级：https://www.laiv-mv.de/static/LAIV/Statistik/Dateien/Publikationen/A%20I%20Bev%C3%B6lkerungsstand/A143/A143%202025%2000.pdf
- 如国家边界变化需同步核实映射；使用既有geometry，主站其他专题代码保持不动。

本次上线发布的是独立人群统计专题，不表示外国国籍与犯罪存在因果关系。
