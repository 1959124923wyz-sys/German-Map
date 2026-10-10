# 工业地图 R7 · 可恢复交接点
更新：2026-10-10。长期研究仍进行中，本文件只声明已提交成果。

- Repository: https://github.com/1959124923wyz-sys/German-Map
- 本轮独立支线：`research/industry-r7-evidence-20261010`，从原工业研究支线 `feature/industry-contraction-map-20261010` 的 `0d229010e853b46714999c1bdabab8399761304a` 分出；原 Draft PR #37 和 main 均未修改。
- 基线：R1–R6 174 条唯一事件 ID（不是174家关闭工厂）。
- R7A 研究新增10条、其中3条生产厂址候选、7条非厂区/集团/后勤研发研究隔离，提交 `c0d4183039ea41e2d8df63d7c019b0663959f01b`；文件 `research/r7a-screened-2026-events.json`。
- R7B 回溯新增11条、其中9条厂址/生产活动候选与2条非生产岗位排除，提交 `9ed3defed2bfcd7ea65a94d37ee264d9704251a1`；文件 `research/r7b-2025-retrospective.json`。
- 当前**文件保存层**基线174+R7A 10+R7B 11 = **195唯一研究记录**。但前端 `topic.js` 与验收脚本尚未载入R7批次，**网页仍可能只显示174**；需要修改并在PR CI验证后才能称已展示。
- Musashi Europe 2026年2月修订跨厂总计457（Hannoversch Münden 187、Leinefelde 200、Lüchow 70），Leinefelde仅停机械加工仍留锻造、Lüchow为减员非关厂。不要重复原487或在三个点各算457。
- GMB Tschernitz以勃兰登堡州政府2025-11-28公告约215人裁员为准，不能误用第三方约220为确切数字；关厂最终落实日需追踪。
- Eberspächer Hermsdorf由2026-01-23 ERM回溯确认于2025-12-31关闭；VOIT St Ingbert 2026-09-30关闭是当时计划，仍待第二来源确定执行结果。
- Treofan Neunkirchen仍留291人继续生产，绝非全面关厂；Gestamp Bielefeld与Forvia Augsburg主要物流/研发/支持岗位，隔离且不画工厂点。
- 所有R7 factory marker仅为县/市行政坐标，不是经核实厂门。
- **全国400现行Kreise 2019—2025同口径WZ2008-C纯制造业工作地就业原始面板仍未成功下载。** `county-employment.json` 继续为空，不得把采集事件数量装作县级实际工业就业下降率；缺失不填0，不得混合WZ B+C和雇佣社保/企业场所人数两个统计口径。
- 历史402个GeoJSON多边形依旧只是402→400 AGS映射，BKG现行县界几何尚未拿到。
- 下一步：逐条核验R7A/R7B的工厂状态和重复，继续从官方/ERM查漏，整合R7加载和CI并创建Draft PR（以旧工业支线为base，不触碰main）；官方统计数据必须有完整来源、下载与同口径核验才能发布。
- 证据来源直接在每条JSON `source_url`。技术信息参考 `topics/industry/research/R5_HANDOFF.md` 和 `topics/industry/README.md`。

## R7C 阶段及遗留记录纠错（已提交）

- R7C 7条有来源的具体生产设施档案，提交 `9647e43d08eb8087920e9ef3707f57c331b93eed`：Kabel Premium Pulp & Paper Hagen 420、Daikin Güglingen 200（仅部分转产捷克）、Rohrwerk Maxhütte Sulzbach-Rosenberg 300已报停、Schlaraffia Bochum 171、Oventrop Brilon 185（装配转波兰但其他德国业务保留）、Britax Römer Leipheim 216、Reemtsma Langenhagen 600。Reemtsma ERM表头2025-03-24与网页引证新闻2026-03-24有冲突，暂按可见新闻日期登记，并要求以后独立纠错；该厂2027计划不等于已关。
- 新文件 `research/r7-legacy-identity-audit.json`，提交 `ca23b8eaf5b8620b0d6a86c497f834da3036d4b9`。纠正旧Eberswalder Wurstwaren的实际工厂位于**Britz（Barnim，AGS12060）**而非招聘会所在Eberswalde市。Eurofound EWN 203947、原RBB资料指向同一厂和约500员工，因此只修正现有ID；Varta Nördlingen约350岗位已在R1记录，亦不新建重复事件。保留原R1源档未直接覆盖，通过R7补丁加载。
- R7A 10 + R7B 11 + R7C 7 = **新增28独立研究条目**，加上原R1–R6 174，已保存总数 **202**。其中12（R7A/B）+7（R7C）=19新增厂址/生产活动标点候选；其余9为其他业务或不宜画关厂点的隔离记录。不可将202说成202家关闭的工厂。
- 已在独立R7支线更新前端 `topic.js`、`tests/validate_industry.cjs`、`tests/smoke_industry_data.cjs` 对202事件批次严格校验；最终通过状态应在Draft PR [#42](https://github.com/1959124923wyz-sys/German-Map/pull/42) 最新CI读取。
- 官方BA仅有行业可选的交互数据库，未通过可信方式实收全国400县双年度纯WZ-C工作地数字。发现BKG的现行免费VG250县界公开GeoPackage/Shape/WFS，另BKG在线ArcGIS图层允许GeoJSON，但仍**没有下载和导入合格400县几何**。研究必须区分来源已找到与数据已下载。
- R7支线PR #42 base=原工业支线而不是main，不能自动合并或部署。

## R7D / R7E 最新交接（当前有效总数220，覆盖先前的202统计）

- R7D新增 **13条**（11条厂址、2条仅研究隔离），文件 `research/r7d-2024-company-primary-audited.json`，GitHub持久化 commit `e7107db900f40b92f19a048965574dba5e156c55`。
- R7E新增 **5条**厂址记录，文件 `research/r7e-2025-undercovered-sites.json`，GitHub持久化 commit `e876e96753d57ca9720e49992bb256a6d95f38c5`。
- **当前已保存 R1–R6 174 + R7A 10 + R7B 11 + R7C 7 + R7D 13 + R7E 5 = 220条唯一研究事件ID。** 新增46条中厂址候选 3+9+7+11+5=35条、集团/办公室/未证明停产等隔离11条，绝非220家确认倒闭的工厂。完整事件页需以最新CI核验。
- 重大状态订正：Feintool Sachsenheim 2024原拟2027全面关厂，2025-08-22企业劳资协议改为**部分保留工业应用生产线**，仅汽车业务外迁；不能称已全厂关闭。原Sachsenheim+Vaihingen合计减200不可分给任一厂。源：https://www.feintool.com/insights/feintool-reaches-agreement-with-employee-representatives-in-sachsenheim-on-realignment-of-business-unit-stamping-europe-part-of-production-in-sachsenheim-to-remain-in-operation/
- NEVEON 2024公告两生产厂Ebersbach an der Fils(巴符Göppingen 08117)及Burkhardtsdorf(萨克森Erzgebirgskreis 14521)和Wiesbaden**行政中心**合计240人；只为两厂各保留 jobs=null，各厂地址虽找到但图点仍县级参考，240整体备忘研究不画红点。
- UPM Raflatac Kaltenkirchen 154岗（2024官方公告，逐步在2025转波兰芬兰比利时），与UPM Ettringen和Nordland纸厂不同。Vileda Augsburg 118是无纺布厂，尽管Eurofound行业顶栏标批发；Papierfabrik Meldorf Tornesch 133仅确定破产、不能当成已关厂；Fjord Paper原网页错误出现2024/2025结束日期混淆，应优先用事实页预期2025-04。
- 新查Kusch+Co Hallenberg 110岗位，2025-12确实停止生产，2026-05社会计划媒体证实；Etkon Markkleeberg 240岗位牙套外迁但保留牙科修复体生产；Oettinger Braunschweig 150岗转到德国其他厂且物流继续；KMS Solingen 120，Konradin Leinfelden 110计划待追踪。
- 对R1 Eberswalder工厂地理补丁旧称Eberswalde更正为Britz (Barnim), 12060，避免与ERM EWN 203947重复；可追溯修订存于 `r7-legacy-identity-audit.json`，不覆写原始文档。
- 前端 `topic.js` 和验收 `tests/validate_industry.cjs`、`tests/smoke_industry_data.cjs` 已集成220条，已观察GitHub Actions在220条版本commit `ae9eb94e6f3278804a1a3b205036c59386f50ae0` 的 run **38040905563成功**： https://github.com/1959124923wyz-sys/German-Map/actions/runs/38040905563 。
- 新增长期查漏清单 `research/R7_COVERAGE_BACKLOG.md` 与官方统计/地区几何调查记录 `research/R7_OFFICIAL_COUNTY_SOURCE_AUDIT.md`（包含数个可用网址，但数据**未下载**）。
- BKG 2025县界研究脚本 `scripts/try_bkg_vg250_counties.py`，安全研究工作流 `.github/workflows/industry-r7-bkg-research.yml`：仅校验400唯一canonical县AGS完全匹配后才会把候选原始几何提交R7分支；**核查此时GitHub仍无候选文件** `data/bkg_vg250_counties_2025_candidate.geojson`，不能称已得到县界或变更已上线。若后续工作流异步写入，下一会话重新读取branch head确认。
- 国别县2019/2025 **纯WZ-C工作地制造业就业**面板仍未取得。图层仍为研究事件数、不可作为就业下降率。Thüringen KR000303可取旧年县级B–F总工业就业，但绝不是WZ C；BA Eckwerte API普通总社保就业不等于WZ C。
- Draft PR #42 的base仍为旧工业工作分支，不动main、不自动合并。恢复 https://github.com/1959124923wyz-sys/German-Map/pull/42 及最新R7文件即可继续。
