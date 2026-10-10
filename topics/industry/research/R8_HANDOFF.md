# 德国工业地图 R8 — 独立研究阶段交接（2026-10-10）

## 可恢复入口与正式验收
- Repo: https://github.com/1959124923wyz-sys/German-Map
- R8 branch: `research/industry-r8-official-data-20261010`；Draft PR: https://github.com/1959124923wyz-sys/German-Map/pull/43，base=`research/industry-r7-evidence-20261010`（R7 Draft PR #42），**并未合并main、未上线统一主站**。
- R7基线220唯一研究条目；R8A另加10条（7个可单厂/单生产线定位案例、3条不标点集团或破产事件），R8B UPM Bruchsal新增1条；**R8现有231条唯一研究记录**。不要称231间已关厂。
- R8A文件 `research/r8a-2024-industry-backfill.json`，提交 `18589d8b2a5aa34b77dc028d4cdecc90447f1923`；R8B `research/r8b-upm-bruchsal-primary.json`，提交 `d508f2243d1454a3f887c1523e8b3c73178f11ec`；后续状态补丁 `research/r8-implementation-patches.json`，提交 `386476925ffa0623dfdf35ddb0a58241a1819060`。
- R8的231记录+地图与数据模拟测试已在 GitHub CI run [38042518368](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38042518368) 显示 **success**，该次检查对应提交 `83555b65d561c213d22aaa3ba0da9834f9176269`。更后续head以最新CI重新核实。

## 重大突破：官方2025 BKG 400县现行地理边界已取得
- 真实候选文件路径 `topics/industry/data/bkg_vg250_counties_2025_candidate.geojson`，Git blob SHA `cc3ff117c963011c9a4dec74e18a64dad20740d0`，总 **2,881,398字符（约2.88 MB）**；Contents API因为文件>1MB返回空content，读取时必须调用 `mcp__GitHub__fetch_blob` 而不是认为空文件。
- 本会话实际读取、JSON解析并逐字段验收：**400个Polygon/MultiPolygon、400个唯一5位县AGS、16联邦州，且全部400个与旧402→400对照完全一致**。Göttingen `03159`、Wartburgkreis `16063`、Karlsruhe Stadt `08212`与Karlsruhe Landkreis `08215`等均确认；来源BKG VG250 2025版，区划有效日 `2024-12-31`。
- 根因修复：BKG给出8位AGS且县级以`000`结尾，验明后前5位对应项目的现行5位县代码；限制GF=4陆地行政多边形，不混海域GF=2；拒绝缺项或未满400条。脚本 `scripts/try_bkg_vg250_counties.py`、研究数据获取CI `.github/workflows/industry-r8-bkg-acquire.yml`。
- 已**仅在R8专题预览** `topics/industry/topic.js` 中替换原402历史几何为新400 BKG GeoJSON，并在图例附BKG授权说明。测试 `tests/validate_industry.cjs`、`tests/smoke_industry_data.cjs` 均已改为核查400现行县界。**main全站通用地图数据 `data/germany-counties.geojson` 未被替换。**

## 工业事件核实的后续状态（已通过独立patch实施，而不重复增项）
- UPM Hürth旧新闻公告2024拟关，UPM自身2024年度报告正式披露**2024年8月停产**；原135人为计划受影响员工，不等于已失业。
- UPM Nordland Papier Dörpen **只停PM3一条纸机，2024年12月已停产**，全厂其他业务存在；原报告210岗位，随后UPM公告Hürth+PM3合计338的新口径，**不能把原135+210当最终338或实际失业量**。
- Solarwatt Dresden光伏组件生产于2024年结束、2024年11月后续新闻证实；研发、测试等业务继续，不能表述公司完全关闭，原工厂190岗和后续全球400岗不能重复计数。
- UPM Biocomposites Bruchsal公司2024年公告永久关闭，Bruchsal与芬兰Lahti合计59人，德国厂单独岗位数无独立来源，保留 `jobs_affected=null`，不把跨国59当单厂。不同于UPM Hürth、Dörpen、Kaltenkirchen、Ettringen。
- Siltronic Burghausen退出小尺寸晶圆（约400人涉及自然流失/合同到期），12寸晶圆与研发仍在厂；Rodenstock Regen约230人镜片生产转捷克，工程业务留下；Putzmeister Gründau和Heimertingen两厂共280岗位，分厂各`null`并保留研究隔离总数，不能重复分配。AEM Dessau破产但2024仍运营，因此不画已关厂标点。
- 所有新增红点仍为**县级/市级参考点而非经核验的厂门坐标**。

## 县级WZ-C就业仍是未完成重大瓶颈
- 已发现官方Regionaldatenbank `42111-02-03-4` 公开CSV索引入口 `https://www.regionalstatistik.de/genesisws/downloader/00/tables/42111-02-03-4_00.csv`；但在R8 GitHub Actions 实际请求返回**HTTP 404**，绝不可称成功获取。
- 已把失败日志**真正保存到GitHub**：`topics/industry/research/R8_REGIONAL_FETCH_FAILURE.log`，实际文本 `OFFICIAL RAW CANDIDATE NOT ACQUIRED: <HTTPError 404: ''>`。
- 抓取脚本 `scripts/acquire_regionalstatistik_raw.py`、工作流 `.github/workflows/industry-r8-regional-data.yml` 已归档，保存日志并只允许符合原始来源的RAW候选入研究目录。不曾产出可信2019—2025 WZ-C全国400县纯制造业工作地就业面板。
- 此后可走真实GENESIS REST API（公开OpenAPI `https://www.regionalstatistik.de/genesisws/rest/2020/GOJsonApi.json`）尝试数据表`/rest/2020/data/table`或`/rest/2020/data/tablefile`，需核实游客权限/POST参数和WZ-C字段。也可用BA官方行业县级CSV，而非B+C混合数据。
- 正式地图`data/county-employment.json`仍然**空值**。县级底色仍只说明“研究样本已登记事件数”，绝不描述为真实工业就业收缩率；任何缺失不能填0。
- 下一阶段优先抓取并审计官方WZ-C、查询剩余漏厂、跟踪原计划2025/26实际执行情况，再由维护组判断主地图合并与手机界面回归。未经许可本专题研究分支不要修改主分支、统一导航、Pages等其他专题。

## 证据
来源见各条`source_url`、`confirmation_source_url`，官方GIS见已提交GeoJSON `_provenance`。获取/验收/来源与实施状态分开留存，不得将“找到网址”表述为“已经拿到数据”。

## R8官方Regionaldatenbank接口实测补充（重要，已真正保存）
- 查官方2020 REST OpenAPI `https://www.regionalstatistik.de/genesisws/rest/2020/GOJsonApi.json` 确认大小写为 `/genesisws/rest/2020`，metadata/table、data/tablefile、data/table都是 **POST**，username/password放HTTP header，查询参数在form body。避免把曾经的CSV 404错误路径反复尝试。
- 建立 `scripts/probe_regionalstatistik_genesis.py`、自动保存的研究工作流 `.github/workflows/industry-r8-genesis-probe.yml`。
- 已真实写入 `topics/industry/research/R8_GENESIS_API_PROBE.json`，三项调用均**HTTP 401**，官方服务器JSON明确报 `Code=15`，德语信息“您无权调用此服务或请求头信息不完整以致无法识别凭证”。本轮访客账号 `GAST/GAST` 不是有效的数据访问凭证，需注册获认证后再提取；不把401冒充成功下载。
- 研究程序完整保存URL、查询参数、HTTP状态和响应片段，不保存/公开个人认证密钥；没有生成任何就业人数、没有改动生产 `county-employment.json`。下一位研究者优先寻找免认证BA官方下载CSV或按官方流程申请API token，不要继续使用匿名GAST盲试。
