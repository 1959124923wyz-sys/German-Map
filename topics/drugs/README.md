# German-Map — 毒品问题专题 / Drug Topic

**维护方式（2026-10-09起）：** 按用户最新指示直接在 `main` 分支增量维护04毒品专题。05移民专题留在本地等待合并；不修改05文件或无关共享地图文件。下文早期分支描述仅保留为历史开发记录。

## 当前交付

- `index.html` / `topic.css`：可独立预览的2025年德国县级毒品案件地图。
- `topic.js`：可卸载Leaflet专题图层，提供 `GermanMapTopics.drugs.loadData / activate / deactivate`。
- `scripts/build_pks_drugs.py`：抓取全国约400个县、官方PKS转录镜像，按AGS校验16州。
- `scripts/validate_drugs.py`：严格数据检查，缺失不能填零。
- `data/pks_drugs_2025.json`：仅在成功构建后生成。
- `.github/workflows/drugs-topic-build.yml`：独立构建和审核，不部署主站。

## 来源与统计口径

县级指标 `Rauschgiftdelikte`：警方登记毒品违法案件（2025），案件数、每10万人案件数。

BKA官方县级T01数据：
https://data.gov.de/suche/daten/2025-polizeiliche-kriminalstatistik-t01-grundtabelle-kreise-ausgewahlte-straftaten-gruppen

自动抓取镜像：https://kriminalitaets-karte.de/kriminalitaet/

**透明性限制：** BKA文件下载端点在部分自动化环境返回403，因此采集器使用自称转录BKA县级表格的公共镜像；所有县均保留原始网址。尚未声称每一个数字与BKA直接下载文件完成交叉核对。未来应抽查原始CSV/XLSX。

**不可混淆：** 全国BKA `Rauschgiftkriminalität` 为164,991起，而县级镜像的 `Rauschgiftdelikte` 在法律罪名包含范围上可能不同。164,991是独立全国参考数，不应强行等同县级数据总和。

**大麻：** 没有把大麻排除。2024年4月1日部分合法化造成警察登记违法案件定义变化。合法使用不是违法案件，但不代表没有健康风险。消费状况应接入抽样调查和污水检测独立观察。

**解释限制：** 主动执法强度与法律定义会影响警方发现案件数，不能用分位色阶描述实际吸毒普遍程度。

## 本地构建

```bash
python -m pip install requests beautifulsoup4
python topics/drugs/scripts/build_pks_drugs.py
python topics/drugs/scripts/validate_drugs.py
node --check topics/drugs/topic.js
python -m http.server 8765
```

浏览 http://127.0.0.1:8765/topics/drugs/。

## 主站未来的接入契约

```js
const loaded = await GermanMapTopics.drugs.loadData({countyGeo, stateGeo});
await GermanMapTopics.drugs.activate({map, loaded, onSelection: selection => { /* 主站处理 */ }});
// 切换离开时：
GermanMapTopics.drugs.deactivate();
```

专题 activate 不缩放地图、不破坏公共地图实例、不修改公共状态；宿主负责隐藏其它专题图层及恢复自身。

## 后续扩展

1. 下载BKA官方原始县级表并抽样交叉核验。
2. 柏林／汉堡／不来梅官方毒品分区图层。
3. EUDA污水检测城市点与具体采样年份。
4. 毒品相关死亡、急性中毒、治疗需求。
5. 大麻／可卡因／冰毒／海洛因及交易、走私专项指标；只有可靠地区数据时才上线。

## 州县交互与数据边界（2026-10-08 更新）

- 全国地图（低倍率）用可点击的16州轮廓选州；右侧增加16州县级数据汇总列表。
- 州视图展示**县级记录合计**和其下全部县/独立市的登记案件率；**估算的州每10万人案件率**按县级已四舍五入的率和案件数反推人口加权获得，不是BKA另行核实的州统计表。
- 进入县市需要点击“查看县市地图”或主动放大（默认7.5级以上）；县市点击可打开2025登记案件、每10万人案件率、相对于2024年的变化；回溯按钮支持从县返回州和从州返回全国。
- 任何地区都不展示未经核验的可卡因、大麻、冰毒、海洛因细分案件数。BKA 2025 T01 州级官方表见 https://data.gov.de/suche/daten/2025-polizeiliche-kriminalstatistik-t01-grundtabelle-bundeslaender ，但BKA附件下载在自动化环境中返回403，需要取得表格再解析罪名键。
- 地图SVG路径取消鼠标焦点造成的巨大矩形轮廓，键盘焦点用路径描边显示；高缩放州轮廓不应截获县级点击。

## 近期毒品新闻与警方通报（2026-10起）

第三选项卡“近期通报”，数据文件 `topics/drugs/data/drug_news.json`，构建器 `topics/drugs/scripts/update_drug_news.py`，每日在 .github/workflows/drugs-news-update.yml 中定期重建并发布。

- 主要来源：Presseportal 转载的德国警方、检方公开新闻稿，按毒品交易、查获、非法种植、死亡/疑似过量急救分类。筛选规则为**保守关键词候选**，不构成全量、无误的案件库。误归类须抽查原文。
- 来源验证：仅原始 `presseportal.de/blaulicht/pm/...` 及德国联邦毒品事务负责人公告域名；新闻标题与发布时间取公开来源，保持明确来源链接。
- **地点约束：** 有地理坐标的标记只是**城市中心附近的近似定位**，不是毒品交易的精确案发点，更不是吸毒场所。无法合理定位的通报继续在侧栏展示而**不伪造点位**。
- 时间约束：近期警方通报按**发布日期**滚动90天，发布日期不等于案发日期；全国年度毒品死亡数据另作背景资料展示（允许超过90天），不绘制成单个事件标记。
- 新闻数量和地图圆点不等于犯罪数量、吸毒人数、死亡人数，也不代表样本完整率；不能与BKA 2025年PKS年度统计相加。
- 浏览器模块为 `topics/drugs/news.js`，专题地图使用独立**SVG renderer**，避免重复之前因Canvas覆盖交互层导致州县无法点击的错误。按“州/分类”筛选后，可点击条目打开原始新闻。
- 无网络、源站HTML更改、时间窗口无数据时保留上一版可验证源记录，前端应提示新闻不可用，绝不能显示伪造数据。


## 2025年州级毒品健康与指定罪名补充资料（2026-10-08）

- 数据文件：`topics/drugs/data/state_health_offences_2025.json`；模块：`state-evidence.js`。只出现在用户选中州后右栏的折叠区，不创建新一级地图或虚构整州分毒品图层。
- 2025年相关死亡记录覆盖9州：Baden-Württemberg、Bayern、Berlin、Bremen、Hamburg、Niedersachsen、Nordrhein-Westfalen、Sachsen、Schleswig-Holstein；每项保留`source_url`和`source_type`。**其余7州暂缺资料，不等于零。** 全德2025年2,150人是单独的联邦官方死亡统计，切勿把9州记录之和当全德总数。
- 部分死亡值直接来自州政府、州警方；其余来自**引用州政府/BKA数据的公共媒体、专业组织**，应用上明确标注“待独立官方原表交叉核验”。不同州的调查时点、死亡纳入口径仍可能不同。
- 2025年各州可比的**每10万人死亡率目前只直接核实柏林7.7**（柏林政府公布，2024年7.6）；其他州虽有死亡绝对数，但暂不依据估算人口反推死亡率。
- 下萨克森州（Niedersachsen）分类记录取自其州刑警局 **2025 T01 第48-55页**：[原始PDF](https://www.lka.polizei-nds.de/download/77720/Tab.01_2025_NI.pdf.pdf)。列出§29 BtMG 一般违法 / 贩卖走私及 §34 KCanG 对应罪名（大麻753 / 1677；可卡因及快克3618 / 977；冰毒83 / 25；海洛因329 / 71）；**每列只表示选定罪名，不能跨列相加后宣称为“该毒品全部案件”。** 特别是严重数量罪名可落在其他代码。
- 石勒苏益格—荷尔斯泰因州（Schleswig-Holstein）2025年的Crystal冰毒**一般违法45起、贩卖2起**，取自[州刑警局短报第19页](https://www.schleswig-holstein.de/DE/landesregierung/ministerien-behoerden/POLIZEI/DasSindWir/LKA/Ermittlungen_Auswertung/kriminalstatistik/_downloads/PKS2025_Kurzfassung.pdf?__blob=publicationFile&v=4)，不代表所有冰毒相关违法案件。
- BKA的16州PKS T01全国联合文件于2026年9月22日发布（[GovData入口](https://data.gov.de/suche/daten/2025-polizeiliche-kriminalstatistik-t01-grundtabelle-bundeslaender)），但BKA xlsx直接下载在部署环境中仍可能返回403。未核验的州及物质全部保持空缺，不用全国分布推算。

## 2026-10-08 增量核验：缺什么补什么

最新覆盖：**12/16州2025年毒品相关死亡统计**、**5/16州2025年按物质统计的官方犯罪分项**、**1州有经出处标明的2025年大麻相关医院诊断记录**。原本9州和2州的统计见前节，保留先前源和代码定义。

本次新增：

- **Brandenburg 勃兰登堡：** 死亡2025年19人（2024年17人），[州内政部公告](https://mik.brandenburg.de/mik/de/service/presse/pressemitteilungen/detail-pm-und-meldungen/~23-03-2026-erneut-weniger-straftaten-in-brandenburg)；[PKS2025州原始报告第39—41页](https://mik.brandenburg.de/sixcms/media.php/9/PKS_Bericht_2025_web.pdf)提供KCanG §34一般违法219、非法交易171、全部罪名701，以及“含特定严重罪名”的按物质汇总：可卡因/快克404、冰毒248、海洛因27、苯丙胺类1,230。**701与219/171有包含关系，不能相加**；表33药物种类口径较§29简单罪名宽，勿横向误比。
- **Rheinland-Pfalz 莱茵兰—普法尔茨：** [州刑警局PKS2025年度报告第48—49页表15](https://www.polizei.rlp.de/fileadmin/polizei.rlp.de/Service/Dokumente/Statistiken/_PKS_Landesweit/2025/PKS_Jahresbericht_2025.pdf)：KCanG一般违法515、非法大麻交易858；可卡因一般违法1,043（报告文字中另提到1,048，**按表15直接数字采用1,043**），海洛因一般违法152，苯丙胺及衍生物一般违法3,202（包括MDMA等，**不可称纯冰毒**），大麻相关总登记2,321。不同法律条款的层次不同，不能相加。
- **Hessen 黑森：** [州内政部2025 PKS公告](https://hessen.de/presse/straftaten-gehen-2025-weiter-zurueck)直接披露可卡因一般违法2,406起（2024年2,300）以及快克一般违法543起（2024年578），两者分别展示，不以“可卡因全部案件”命名。
- **Thüringen 图林根：** 死亡2025年77人（2024年50），[dpa转引州警方年度报告](https://www.zeit.de/news/2026-04/04/zahl-der-drogentoten-in-thueringen-erneut-gestiegen)。未拿到州警方死亡原表前，前端标为间接核验。
- **Sachsen-Anhalt 萨克森—安哈尔特：** 死亡2025年61人（2024年48），[dpa转引州内政部](https://www.sueddeutsche.de/panorama/traurige-statistik-zahl-der-drogentoten-in-sachsen-anhalt-auf-hoechststand-dpa.urn-newsml-dpa-com-20090101-260227-930-743602)。前端标为间接核验。
- **Mecklenburg-Vorpommern 梅克伦堡—前波美拉尼亚：** [2026年9月dpa刊载于州议会网站](https://www.landtag-mv.de/dpa-ticker/dpa-mitteilung?cHash=a8814c06e6023b635157e30ad837a8ef&tx_w3dpa_dpalist%5Baction%5D=detail&tx_w3dpa_dpalist%5Bcontroller%5D=Dpa&tx_w3dpa_dpalist%5Buid%5D=7381)，引州政府议会答复：2025年大麻相关医院诊断记录486例（2024年421），其中精神病性障碍相关诊断133例（2024年94）。**不是486个独立吸毒者，更不能据此单独判断大麻法律调整造成病例变化**。尚待取得议会原始答复PDF。
- **Bayern 巴伐利亚复核注记：** 2026年3月[州内政部PKS发布会](https://www.stmi.bayern.de/media/presse-und-medien/news/2026/03_2026/260316-kriminalstatistik-2025-ppp.pdf)报247人，而[州警2026年6月上普法尔茨公告](https://www.polizei.bayern.de/aktuelles/pressemitteilungen/104900/index.html)报246人。前端保留先前版本对应的247并附上口径/统计时点差异；不可擅自把两个版本当作彼此毫无冲突。

技术处理：州分项数据允许 `groups`（一般违法/交易）或 `additional_metrics`（单一、明确罪名范围）分开并列，不允许跨列相加。只有真值和有来源的数字显示；缺失永远不替换为0。证据 UI 仍在 `topics/drugs/state-evidence.js` 的可折叠区域，绝不另开一级专题。

## 2026-10-08 继续核验：萨克森与汉堡州（7/16州有分物质数据）

这次新增了 **Sachsen（萨克森）** 和 **Hamburg（汉堡）** 两份2025年州警官方PKS原始报告，按物质的州级覆盖达到 **7/16**。州级死亡统计仍覆盖 **12/16**。

- **萨克森（州全境）：** [州刑警局《PKS 2025年度概览》第43—45页](https://www.polizei.sachsen.de/de/download/Landesportal/PKS-Jahresueberblick-2025.pdf)明列一般违法/交易走私（对应PKS 731***/732***）：海洛因272/35、可卡因及快克336/175、甲基苯丙胺（各种形态）2,418/263；KCanG §34相关罪名1,669；跨多个代码的Crystal冰毒总计2,785（2024年2,597）；全部毒品违法案件7,219（2024年9,738）。**Crystal多罪名总计与甲基苯丙胺的一般违法/交易有交集，不能重复相加。** 2025年州毒品相关死亡26人，2024年28人，已把旧的新闻间接来源替换为州警方原报告。
- **汉堡（州全境）：** [汉堡州刑警局2025 PKS详细表](https://www.polizei.hamburg/resource/blob/1161478/9a8911027a7857989d984ac1114ff28a/pks-2025-do-data.pdf)中BtMG §29一般违法：海洛因982（2024年1,192）；可卡因及快克3,298（2024年3,614），**其中快克1,995（2024年2,212，属于3,298的子集）**。另据[汉堡州刑警局2025年形势简报](https://www.polizei.hamburg/resource/blob/1144760/b281f93a54934b8aebd17c3d4a2790c7/pks-2025-handout-do-final--data.pdf)：KCanG §34全部登记1,918（2024年953），其中大麻非法交易1,230；其他BtMG非法交易1,331。**1,230是1,918的子集；不同年份大麻数据的法律基数不同，不能按普通同比解释。**
- 采集规则：`additional_metrics` 里的“其中”“全部”与 `groups` 里按一般违法/交易的不同PKS代码保留原样，**不得形成一栏统一的「某种毒品全部案件」排名**。由于荷兰/沿海港口等特殊执法特点，不能把跨州PKS登记数视作实际毒品使用率。
- 自动部署必须通过严格的数据源字段验证、浏览器打开州数据核对与既有新闻/污水/白色边界测试。



## 2026-10-08 第一阶段增量：柏林官方PKS（8/16州）

- **Berlin（柏林）**：柏林州警方[PKS2025 Kurzbericht（毒品犯罪段落第30页）](https://www.berlin.de/polizei/_assets/verschiedenes/pks/pks-kurzbericht-2025.pdf)记载，可卡因（含快克）按 **731200 BtMG §29** 计一般违法**2,218起**，按 **732200** 计非法交易及走私**1,432起**；大麻按照 **KCanG §34** 计相关登记案件**2,343起**，其中非法交易**1,309起**。**其中1,309起已包含在2,343起之内**，绝不可相加。
- 第一期分类数据覆盖由7州增至8州；死亡资料维持12州。该来源属于全柏林州（Land Berlin），并非某个柏林警区的单独统计。
- 新增自动数据校验器 `topics/drugs/scripts/validate_state_evidence.py`：强制匹配16州行政区、2025年、原始来源及州级覆盖元数据，核查柏林两个可卡因PKS代码与大麻包含关系。部署前必须执行该校验；Playwright则打开柏林州侧栏检查数字实际显示。
- **不同统计范围不可相加：** 2025年Berlin可卡因一般违法与交易不等于可卡因全部刑案，KCanG子项不能与KCanG总体相加，历年大麻PKS受2024年法律调整影响。


## 2026-10-08 分类统计第①项：柏林及巴登—符腾堡

这一批仅推进计划第①项（按物质的PKS罪名分类），**已有至少一项核实分类数字的州由7州增加到9州**，并不代表9州已获得完整毒品罪名分布。12州死亡记录暂不扩充，也不擅自推算死亡率。

- **Berlin / 柏林：** [柏林警方2025年PKS简报（毒品犯罪段落）](https://www.berlin.de/polizei/_assets/verschiedenes/pks/pks-kurzbericht-2025.pdf)——BtMG §29可卡因/快克一般违法2,218起（731200）、非法交易/走私1,432起（732200）；KCanG §34违法2,343起，其中非法交易1,309起。**1,309已经包含在2,343内**，不可重复加总。
- **Baden-Württemberg / 巴登—符腾堡：** [州政府2025年禁毒犯罪统计专题](https://sicher-bw.de/kriminalitaet/rauschgiftkriminalitaet)——新精神活性物质 NpSG §4 违法156起，依BtMG记录的新精神活性物质非法交易61起。**这是两个不同法律统计项**，既不可相加，也不能据此称为“该州NPS全部案件”。该州海洛因、可卡因、冰毒详细计数继续标为缺失。
- 自动质量检验 `topics/drugs/scripts/validate_state_evidence.py`：核查记录确属16州之一，标注2025年、数据源属于州级机构并附原文URL，核对柏林毒品罪名键与大麻子项的包含关系、巴登—符腾堡NPS法条及元数据覆盖数量。部署前运行；浏览器冒烟测试还会点击这两个州校验右栏数字。


## 2025年官方原始分类第①项：巴伐利亚与北威州（11/16州）

截至2026-10-08，可找到**至少一项经2025年州政府或警方原表核实的分毒品案件数字**的州由9州增至**11州**。这不是11州具有完整分物质分罪名矩阵。毒品死亡记录维持12州，健康诊断记录维持1州；仍缺分类原表的州继续显示“无核实数字”，不使用全国比例、邻州数据或人口推算。

- **Bayern／巴伐利亚州：** [州警方《2025年度PKS新闻报告》，第33页（PDF第35页）](https://www.polizei.bayern.de/mam/kriminalitaet/260316_pks_pressebericht_2025.pdf)明确记载大麻及其制品相关违法7,164起（2024年15,270）、涉及可卡因含快克的BtMG违法4,440起（2024年3,972）、新精神活性物质NpS相关违法1,308起（2024年823）。它们属于**按涉案物质界定的宽口径统计项**，不能误标成§29一般违法、§34 KCanG全项或直接推算吸毒人数。尤其大麻法律于2024年4月调整，不宜按通常年比年法解释案件降幅。
- **Nordrhein-Westfalen／北莱茵—威斯特法伦州：** [州内政部《PKS2025 Handout》，第38页（PDF第43页）](https://www.im.nrw/system/files/media/document/file/pks-nrw-2025-handout.pdf)列出可卡因含快克相关案件7,507起，较2024年的6,433起增加1,074起。统计项覆盖涉及可卡因的违法，而非仅BtMG §29一般违法代码731200；州全部毒品犯罪35,517起属于**另一范围的合计**，两者不能相加。
- 以上记录存于 `data/state_health_offences_2025.json`，右侧“州级补充资料”延用现有折叠面板，不添加独立地图控制或额外显眼卡片。`scripts/validate_state_evidence.py`固定两州的主要原表数字、2024基期、来源级别及11州覆盖元数据；`tests/smoke_drugs.py`通过展开对应州验证UI呈现。
- **本阶段仍在推进第①项。** 原定后续次序：②补充16州死亡率官方口径；③2021—2025趋势（2024年大麻法律断点必须明确）；④扩展城市级资料；⑤提高新闻质量与自动更新可靠性。


## 2026-10-09 计划①＋②：原始口径标准化、死亡统计补缺（11/16；13/16）

开发目标以三个问题为准：**哪里警方登记案件较多；涉及什么毒品；风险是在上升还是下降。** 优先完善①分类数据和②死亡数据，之后再考虑③2021—2025长期趋势、④城市专题和⑤新闻后台，而不是叠加独立的地图和按钮。

本批实际变化：

- **毒品死亡资料：13/16州。** 新增 Mecklenburg-Vorpommern（梅克伦堡—前波美拉尼亚）2025年24人。出处为[《Ostsee-Zeitung》2026年9月30日对州刑警局数字的转述](https://www.ostsee-zeitung.de/mecklenburg-vorpommern/drogenberater-warnt-vor-mischkonsum-in-mv-konsumenten-immer-juenger-6RTS5SJZZRDFNKE7RNYC45YPK4.html)，按 **regional_newspaper_citing_LKA**（媒体转引）单独标记，尚非2025原始州表；2024年的15人据[2025年3月dpa转引州刑警局](https://www.zeit.de/news/2025-03/30/15-drogentote-in-mecklenburg-vorpommern-im-jahr-2024)。保留核定时点差异提示。
- **升级巴登—符腾堡死亡来源：** 原先引行业组织的191人（2024年195人），现直接链接[州内政部2026年4月10日公布的2025年官方统计](https://im.baden-wuerttemberg.de/de/service/presse-und-oeffentlichkeitsarbeit/pressemitteilung/pid/zahl-der-drogentoten-im-jahr-2025-leicht-zurueckgegangen)。其中129例涉及混合用药；不把该项与其他致死物质项简单相加。
- **目前仍缺3州2025年全州死亡总数：Hessen、Rheinland-Pfalz、Saarland。** 科布伦茨警方[2025年警区报告第37页](https://www.polizei.rlp.de/fileadmin/polizei.rlp.de/Service/Dokumente/Statistiken/PKS_KO/260210_Jahresbericht_PKS_2025_PPKO.pdf)明确注明2025年全州死亡数据当时尚未获得，**11例只属于科布伦茨警区**；德国西南广播2025年12月30日关于萨尔州“迄今33例”的资料并非核定全年同质统计，也暂不入库为年度州级总数。
- **分类统计：仍为11/16州。** 余下 Bremen、Mecklenburg-Vorpommern、Saarland、Sachsen-Anhalt、Thüringen 必须找到2025全州、按物质或罪名明确划分的记录才纳入。州内个别警区、区县的分物质记录可以留作以后城市专题，不能充当全州覆盖。
- 所有28条 `additional_metrics` 现带 `scope_kind`，区分 `general_offence`（一般违法）、`trade_or_smuggling`（交易走私）、`statutory_total`（指定法律完整类别）、`multi_offence_substance`（同物质多罪名汇总）、`multi_offence_all_drugs`（全部毒品多罪名总数）、`subgroup`（已计入父项）和 `other_statutory_offence`（其他专项法规罪名）。
- 汉堡快克属于可卡因一般违法、汉堡大麻交易属于KCanG大麻总数、柏林大麻交易属于KCanG大麻总数：以 `subset_of` 指向各自父项，自动核对“子集不大于总数”。对仍属不同口径的州，继续分栏原文展示，不强制汇总成“全德国可卡因犯罪”排名。
- `scripts/validate_state_evidence.py` 将历史的州键和2025年元数据规范化为**每条单独具备年份、州名、数值、统计范围、法律/罪名标识、来源及来源级别**的内部核验记录，识别重复键、缺失范围、子项超过总项、未知州等错误；不改变前端JSON消费契约。`.github/workflows/drugs-pages-deploy.yml` 不再把覆盖州数写死，改由数据元字段交叉核验。

下一步依次：继续检索缺失的3州死亡原表和5州分类原表；待可核实的官方人口分母和统一死亡认定口径到位，再加入“每10万人死亡率”；多年的毒品罪名趋势必须对2024年4月1日KCanG法律变更标注断点。


## 2026-10-09 第二轮：莱茵兰—普法尔茨罪名深化与五年趋势小试点

- **阶段①不以覆盖州数为唯一目标。** 既有11州分物质资料中，Rheinland-Pfalz（莱茵兰—普法尔茨）完成2025年州警方[PKS年报第48—49页表15](https://www.polizei.rlp.de/fileadmin/polizei.rlp.de/Service/Dokumente/Statistiken/_PKS_Landesweit/2025/PKS_Jahresbericht_2025.pdf)深度补录：KCanG §34全部罪名2,319起（不同于含BtMG/MedCanG的“大麻相关登记案件2,321”宽口径）；新增大麻走私495、特别严重案件316、非法种植86、§34 Abs.4重罪47，均是KCanG §34总项的子类。旧有大麻一般违法515、非法交易858同属这一法定总项，**不能与2,319相加**。另外2025年BtMG一般违法涉及NPS 173起（2024年283），NpSG违法178起（2024年55）；**不可合并为同一种法律范围的NPS总数**。
- **阶段③只做一个可验证的试点：** 新增`long_term_trends_by_state.Rheinland-Pfalz`官方PKS登记毒品违法案件2021—2025年序列：20,624 / 19,832 / 19,296 / 13,433 / 9,888，来源于同一报告第47页图21。此系警方登记案件数，**不是实际毒品消费量或吸毒人数**。2024年4月1日大麻部分合法化、2025年KCanG子键调整，令跨期比较受限。
- 前端仅在右侧旧有“州级补充资料”折叠栏呈现一个**极小的趋势折线**，2023—2024年间有明确的虚线法定断点，折线不跨断点连接；其他未核实5年数据的州**不出现假趋势**，不增加第四张地图、按钮或外部依赖。
- 本次数据质量脚本固定这7项新罪名、法定父子关系、全部5个年份和2024断点；浏览器回归测试要求该州右栏出现各数字且SVG仅有两段折线。**新数据未增加已核实州数**：仍为分物质11/16州、死亡13/16州。缺失2025年州级死亡数据的Hessen、Rheinland-Pfalz、Saarland继续留空，不能拿法兰克福市、科布伦茨警区或2025年12月的暂报代替全年州级核定数字。
- Bremen 2025全州PKS T01原始目录已找到：[不来梅州内政机关发布页面](https://www.inneres.bremen.de/dokumente/pks/detailinformationen-kriminalstatistik-2025-31032)；PDF下载网关偶尔拒绝自动化读取，暂不将市县或警区数据冒充全州数，后续优先取得可稳定核验的原表行。
