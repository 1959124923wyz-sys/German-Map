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
