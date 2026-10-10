# 德国基础设施地图｜支线整合说明（2026-10-10）

独立专题路径：`topics/infrastructure/`。此模块在 **feature/infrastructure-map-phase1** 研发支线上，不代表已经在 GitHub Pages 主站正式发布。

## 产品结构
- 与德国地图犯罪/环保/财政专题同款深色顶部导航、浅色 OSM / Leaflet 地图和右栏统计。
- **底色**：16州旧试验综合指数；低分为深色。点击州查看铁路线路/车站设施评分、光纤覆盖率及供电中断原始数据。
- **事件**：默认隐藏，勾选显示11个精选工程案例；悬停显示一句话摘要，点击显示详情、状态、时间、来源及坐标精度。
- **旁证**：州详情独立展示六州高速公路桥梁承载TLI IV/V、部分州DIN桥梁状态及州道ZEB路面数据。未取得数据以缺失处理，不填补，不加入原指数。
- 地图复用 `../../data/germany-states.geojson` 的16州 ISO，避免重复存储州界。

## 数据文件
- `data/raw_states_2025.csv`：此前研究保存的16州四指标原始快照。
- `data/state_scores_2025.json`：此前第一阶段产生的旧试验指数，附原始分、权重、各州分数及敏感性计算。
- `data/condition_evidence.json`：六州可横向比较的高速公路桥梁TLI IV/V（含分子分母），以及管理范围不同的局部DIN/ZEB证据。
- `data/events.json`：11个工程项目档案，项目ID唯一、状态可追踪、每条至少有一条公开来源及坐标精度。
- `tests/validate_data.cjs`：自动检查16州ID、指标计算、缺失值、桥梁分母和事件来源等。

## 统计口径、重要局限
1. **这是试验指数，不是德国官方全国基建质量排名**：铁路线路35%、车站15%、光纤30%、电力20%，铁路设施评分（小为好）用 `100 - 20*(grade-1)` 转换，光纤采用百分比，供电由 `100*(1-SAIDI/30)` 转换。这些转换/权重是人为设定，并非统计学发现或因果解释。
2. 供电SAIDI存在跨州电网运营商按总部所在州归属的官方限制。修订综合指数时宜剔除该项或重新验证空间归属，因此仅保留旧版试验结果供维护组复核。
3. 所有桥梁、道路数据 **单列展示**：TLI承载等级IV/V ≠ DIN1076设施状态≥3.0；ZEB各州检测范围、道路类别及年份也可能不同。严禁跨类汇总或把缺失视为好。
4. 事件是**选择性调查**，记录数量不代表县市基础设施破败程度。多数点是市镇附近示意位置，不能据此定位桥梁精确坐标。已完成项目不能标为仍在封闭。
5. 2026年KfW市政投资积压2312亿欧元仅属全国抽样估算，不拆给州，也不参与评分。
6. BASt全国桥梁完整原始表和2026年版记录尚未完成全量下载、去重、分母校验；本支线不声称已经取得16州统一桥梁评分。
7. 某些历史路面局部证据的报告入口仅为来源目录或主管机构网站，合并前应补齐具体原始文件/页码，届时可选择隐藏未复核记录。

## 主要原始来源
- DB InfraGO 2025年度基础设施报告：https://www.dbinfrago.com/web/unternehmen/Strategie-und-mittelfristiges-Zielkonzept/InfraGO-Zustandsbericht-12636112
- Gigabitbüro 2025 FTTB/H：https://gigabitbuero.de/artikel/neue-versorgungsdaten-im-breitbandatlas-verfuegbar-datenstand-dezember-2025/
- Bundesnetzagentur SAIDI（含地理归属限制）：https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Versorgungssicherheit/Versorgungsunterbrechungen/Auswertung_Strom/start.html
- IHK NRW《Brückenmonitor 2025》：https://www.ihk-nrw.de/hauptnavigation/presse/medieninformationen-2025/pm-20250310-brueckenmonitor-6495744
- 梅前州官方桥梁状况：https://www.strassen-mv.de/de/bruecken/zustand/
- 勃兰登堡州2026道路养护计划：https://mil.brandenburg.de/mil/de/presse/detail/~21-09-2026-erhaltungsprogramm-fuer-landesstrassen
- KfW Kommunalpanel 2026：https://www.kfw.de/%C3%9Cber-die-KfW/Newsroom/Aktuelles/Pressemitteilungen-Details_897920.html
- 11个事件的各自公开来源见 `data/events.json`。

## 合并前检查
`bash
node --check topics/infrastructure/topic.js
node topics/infrastructure/tests/validate_data.cjs
python scripts/validate_site_assets.py
`
 
首批分支已增加自动数据与链接检查工作流。真实浏览器鼠标/移动端回归尚需维护组运行，且不需要额外单独创建GitHub Pages部署流程。合并上线时核对所有专题导航、主站导航以及 Pages 工作流已有触发范围。
