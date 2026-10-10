# 德国工业衰退地图 · 长期研究接续点（R5D，阶段性完成）

**2026-10-10 · GitHub 已持久化；研究支线不是正式上线主分支。**

- Repo: `1959124923wyz-sys/German-Map`
- Branch: `feature/industry-contraction-map-20261010`
- PR: https://github.com/1959124923wyz-sys/German-Map/pull/37 （Draft）
- 研究事件记录：**R1 61 + R2/R3 38 + R4 18 + R5A 10 + R5B 16 + R5C 12 + R5D 18 = **173唯一事件ID****。每条带来源，不代表155间已关厂。
- 新增 `research/r5a-eurofound-sites.json` (10)、`research/r5b-manufacturing-cases.json` (16)、`research/r5c-screened-manufacturing.json` (12)、`research/r5d-2025-factory-closures.json` (18)，均已提交原支线。
- R5C特别查到欧盟ERM重复新闻 `ENOXX 204191` 和 `B.PRO 204395` 是同一家Oberderdingen业务的180岗退出计划，**只存一个事件**。Verallia Essen **仅评估**未来关厂、Ultinon Aachen **当时只破产风险**、BASF后台业务外迁不是制造业关厂，均从红点排除。2025 Osram Schwabmünchen 270计划关厂与2026跨国集团1000岗是不同口径，避免重复。
- R5B同一企业不同厂址岗位已分开或留空；如Thermo Fisher Bremen 100 + Langenselbold 60 均为独立归属；Weinig 400全球岗位没有任何单厂数字，禁止分配。
- 重点新证据：Sande Stahlguss Sande 已关；Oskar Frech Plüderhausen 80岗（实际强制裁员计划50、其余30退休/自然减员）并拟向上海与美国转产；Güntert Villingen-Schwenningen 拟102岗重组仍继续经营；Witzenmann Pforzheim 230岗计划，ERM顶部地名另出现Kieselbronn/Remchingen但正文不支持三地拆分。
- Geodata: `data/germany-counties.geojson` **原本已有**5位AGS `feature.id` (402历史图形)；2016 Osterode am Harz (`03156`)→Göttingen (`03152`)、2021 Eisenach (`16056`)→Wartburgkreis (`16063`)。`data/ags-crosswalk-402-to-400.json` 已记录**400个现行canonical AGS**。注意：只是AGS转换，**不能视作已经更新县界形状**。新事件用 `county_name` 指定县，以防城区/周边县重名。
- **官方县市工业就业数据还未实际批量得到**：`data/county-employment.json` 为空，当前红色深浅只能表示研究库已收录重大事件数量，不是实际制造业就业降幅。地图不应宣传为真实工业收缩率排名。
- `scripts/build_county_employment.cjs` 从经过审核的 **WZ2008_C、workplace、2019/比较年**县AGS原始CSV安全导出并拒绝缺失、保密、跨行业混合。禁止拿E1111C的B+C聚合直接当WZ C；严禁把R5新闻条数伪装成县就业。
- Tests: `tests/validate_industry.cjs` 含事件、跨厂数字、400AGS、官方CSV导入测试夹具（测试假数据**不入正式地图**）；CI `.github/workflows/industry-pr-check.yml`。要确认当前PR head的GitHub Actions validate结论及新增运行时全页面启动 smoke 测试；如果失败读取任务日志修复。
- 静态页面 `index.html` `topic.js` 按项目整体深色头栏+单层热度县地图+大事件红点设计；未来维护组统一接入导航/Pages时再合并。主分支未修改。

## 长期研究的下一步优先级
1. 先获得德国联邦就业局 **县市工作地制造业WZ C** 2019—2025同口径原始表（优先），或 Regio-Stat `42111-02-03-4` 按同口径导出；缺失县必须显示灰色。巴伐利亚 `E1111C` 是B+C聚合，切勿冒充纯制造业。
2. 继续系统穷举 Eurofound 德国2024—2026制造业事件，逐条检查厂址、岗位、宣布日期和后来实施状态；补充政府、工会和公司一手来源，特别针对「已宣布拟关厂」后续进展。研究多厂事件时共享总数、单厂保持 `null`，不重复叠加。
3. 根据BKG官方VG250更新到2025真实400县界、保留原AGS跨年对照及源许可证说明；注意政治区划已变化。
4. 每取得一批10—30条记录，**先提交 `research/r5d...json` 再改加载器和测试并提交，然后更新本文件**，检查CI通过后方可称这一阶段完成。
5. 每次断点续接先读这个文件、PR #37、最近GitHub提交及 `README.md`，不要求用户重复交代。

## 已发现的残余限制
- R1沿用鲁尔早期若干参考坐标，R2—R5大多数红点是城市/县域参考位置，非工厂门址。
- Eurofound是大企业新闻样本，工业服务、财务集团及存续场地须独立筛查；数据库条目数不表示真实关厂总量。
- R1—R4若有历史数据口径错误，应该用带来源的补丁，不覆盖丢弃原始证据。

## R5D 核心新结果（已保存至支线）
- 回溯Eurofound德国2025年重大工业收缩：BSH Bretten 980和Nauen 440按独立厂址；Staedtler Neumarkt 200和Sugenheim 100各厂分列，生产拟集中纽伦堡；DS Smith五座德国拟关闭工厂各保留独立记录、约500人的合计数字留研究隔离备忘；RW Silicium Pocking 110；Danone Ochsenfurt 230（富尔达扩产）；Norsk Hydro Lüdenscheid 190；O-I Glass Bernsdorf 100；UPM Ettringen经过最终社会协议由235改为189；Meyer Burger Hohenstein-Ernstthal 289和Bitterfeld-Wolfen 331分别对应不同业务；Mehler Fulda 192。
- R5D数据 `research/r5d-2025-factory-closures.json` 18条，**17条有具体厂址，1条DS Smith集团备忘不显示红点**。注意有些“2025年末拟关厂”只有2025的公告，没有之后的二次确认，不能仅根据今天已到2026年改成“已完成”。
- R5A/B/C/D 研究档案中**46个明确单厂县级归属均已经写入五位 `county_ags`**，此为经源地名与项目现有AGS县界核查的行政级位置，而非厂门地址；严格区分巴符州Karlsruhe城市 `08212` 与Karlsruhe县 `08215`，Augsburg、Passau、Coburg 同名城乡。
- 新增官方资料预核验档 `research/official-source-verification.json`；官方完整就业表仍**尚未实际下载**，不得称已经完成“全国工业就业下降率”。
- 严格导入脚本 `scripts/build_county_employment.cjs` +测试夹具测试保密值、WZ2008-C、AGS，对照年份，拒绝混合B+C；CI已加 `tests/smoke_industry_data.cjs` 的真实静态数据启动模拟，能捕捉页面加载、关联县数和非真实底色声明错误。
- 本地源文件未再造任何新的sandbox ZIP：研究资料已**以GitHub分支commit为唯一验收保存点**。用户/维护组继续可直接查看 https://github.com/1959124923wyz-sys/German-Map/pull/37 。

## 下次首要任务 / 尚未解决的瓶颈
1. **决定真实工业就业底色成败的是官方县级WZ-C工作地从业人员数**。BA交互就业数据库支持全国/16州/县市csv-json导出，但当前联网工具不能直接走网站交互下载全部400县原始时间序列；下一对话优先通过自动化或浏览器辅助合法导出。未取得则不要发布虚假制造业就业降幅。
2. 官方现行2025 VG250 400县几何仍未导入；现402历史几何虽有现行AGS对应但形状仍旧，两个并县处视觉边界需最终修正。
3. 对已核厂址继续收集厂门经纬度和实施确认，筛查Eurofound多次公告重复计数。集团岗位不能乘厂数。
4. 任何后续R5E、R6阶段先写新的 `research/...json` 入branch，再更新专题JS和tests，**测试绿灯后更新本HANDOFF**；切勿直接merge main或改动其它主题导航。
