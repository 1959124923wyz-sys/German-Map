# 08 · 德国地方财政地图（A+B合并）

## 已接入数据和分级设色语义

- 默认地图：德国2025年**13个非城市州辖内市镇和市镇联合体**人均财政收支差额（核心及附属预算）；柏林、不来梅、汉堡没有这一可比的市镇财政指标，显示“无数据”，不是盈余/零赤字。来源：德国统计门户 [官方指标页](https://www.statistikportal.de/de/nachhaltigkeit/ergebnisse/ziel-8-menschenwuerdige-arbeit-und-wirtschaftswachstum/staatsdefizit-je)。
- 城市专题：莱茵兰-普法尔茨州**12个非县辖市**2025年全年市政现金收支人均值。来源在每个城区的 `source` 字段。**不能把普通县政府预算当作县域全部市镇合计；本图未涂色普通县。**
- 事件：财政B第1—7轮累计170条调查记录，其中72条满足其基础地图候选条件；所有记录附状态和主要来源。**72不代表正在执行的危机，更不是72个独立项目或72处精确设施地点。** 其余98条是未实施、县/区层级、证据需核查或其他不适合直接上图的记录，仍可在“全部研究档案”中查看。
- 事件展示在**县级AGS地区近似中心**；县域聚合仅为查询入口，不代表具体设施/市镇的精确坐标。不产生伪造经纬度或设施点。
- 数据核验时点：2026-10-09。当前地图为研究样本，不能据记录分布判断某州财政风险更高，也不能把统计上的短期借款视为破产概率。

## 界面（第二版）

与主地图统一深色导航、左地图右侧栏和 Leaflet 底图。三个主入口为“全国收支”“城市收支”“财政事件”，仅切换真实数据层，不产生合成财政危机指数。州级颜色默认显示；事件点默认关闭，避免掩盖财政收支，切换“财政事件”自动显示县域聚合点，切回原模式恢复之前叠加偏好。

右侧优先展示单个地区的人均财政收支、三个覆盖数字和有限条事件；事件类型及状态筛选、170条完整档案位于折叠式“筛选与完整研究档案”，不会默认挤占地图。单击地图上的县域事件数量可筛选该县域。所有记录及原始出处均予保留。中文主要城市标签使用主地图公共模块。

## 第十轮（支线增量、上线前优化）

- 新增 Destatis 2022—2024年**综合地方债务**，13个非城市州共39条人均债务观测，3个城市州各3年的缺失记录标为“不适用”而不是0。全国地图在2025年人均财政收支、2022/2023/2024综合地方债务之间切换，不新建主导航。
- 综合地方债务含市镇本级、附属预算和按比例分摊的市属企业债务；它与2025年地方借款存量、年度财政收支差额之间**没有可加性**。2023与2024年人口基数口径存在变化，不能直接依据人均值变动推断官方同比。
- Destatis 2024网页全国总额342761百万欧元与其13州分项加总343762百万欧元存在差异；保留官方分州数据，**不显示由有争议分项求和的全国总额**，详见生成器的质量检查。
- 精简地图渲染：州级、县级多边形只创建一次，切换视图仅重设图层显隐和样式；弹层事件聚合仍保留事实与来源说明。
- 新增 `data/build_finance_integrated.py`、`data/finance-integrated.js`、`tests/validate_finance_integrated.py`，与原始CSV一起可重复生成。
- 来源：[Destatis官方综合债务年度分州表](https://www.destatis.de/DE/Themen/Staat/Oeffentliche-Finanzen/Schulden-Finanzvermoegen/Tabellen/liste-vierteljaehrlichen-schulden.html)。

## 第九轮（支线增量，未合并main）

- 添加 `research/finance/a/state_municipal_loans_2021_2025.csv`（各州2021—2025年短期流动性借款和投资借款原始研究表，160行，其中城市州30条标为不适用，130条有效）。2025年非城市州两类借款分别为385.87亿欧元和1551.36亿欧元。**借款是债务存量，不是年度财政赤字，也不包含市属企业分摊债务。**
- `data/finance-history.js` 从原始A线CSV构建，并保留莱法州2025/2026上半年各36条地区记录；期别为2025全年（只有12城）、2025上半年（12城/24县）、2026上半年（12城/24县）。本次地图提供2025全年12城、2025上半年12城、2026上半年12城、2026上半年24个县政府本级四种独立选项。**禁止把县本级财政同城市或其下属市镇财政合算。**
- 点击州可展开2021—2025年借款存量（单位亿欧元），默认折叠，不制造新的全国债务热力图；三主菜单保持不变。
- 生成指令：`python topics/finance/data/build_finance_history.py`；新增回归：`python topics/finance/tests/validate_finance_history.py`。
- 官方依据：[2026地方财政报告](https://www.bertelsmann-stiftung.de/fileadmin/files/Projekte/Monitor_Nachhaltige_Kommune/Finanzreport2026.pdf) 表9/10（第43/44页），[莱法州2026年上半年市镇财政报告](https://www.statistik.rlp.de/nachrichten/nachrichtendetailseite/nach-rekorddefizit-2025-luecke-zwischen-ausgaben-und-einnahmen-im-ersten-halbjahr-2026-geringer)（县本级与城市分表）。

## 代码和资料

- `data/build_finance.py`：从 `research/finance/a/` 和 `research/finance/b/` CSV 再生成 `finance-data.js`，不凭空计算或补齐缺失值。
- `data/finance-data.js`：线上加载的静态JSON数据封装，无外部API密钥，原始资料保留在 `research/finance/`。
- `data/finance-audit.json`：生成时的记录统计与基本约束。
- `topic.js` / `topic.css` / `index.html`：Leaflet静态地图、切换指标、证据详情和状态筛选。
- `tests/validate_finance.py`：本地数据、一致性、AGS、来源及页面引用检查。
- `../../data/germany-states.geojson` / `../../data/germany-counties.geojson`：复用项目现有州县地图。历史边界含已废止AGS，特别是哥廷根、艾森纳赫及2026年哈瑙变化。**县域锚点属示意位置；若改用2026行政区图，需重新测试全部关联编码。**

## 决策与局限

不要将不同统计主体（州本级、县本级、县域汇总、市镇、市属企业）或不同统计范围（核心预算、附属预算、综合地方债务）直接拼成统一评分。默认颜色仅由同口径的人均**财政收支差额**决定，与B事件密度无关；城市专题同样只显示有数据的12市，不做全德国城市排行。

用户端应看到两类明确的时间：`decision`（作出决定）和 `effective`（生效日期）。`effective` 状态也可能已结束；`adopted` 等不代表执行。`reversed` 可能是改善/解禁，不能涂红为仍在危机。金额只在弹窗显示原始类型 `amount_kind`，**绝不可汇总合计**。`parent` 不等于新项目数量；整个数据库是定向证据档案，非全德国市镇完整普查。

## 本地验证

```bash
python topics/finance/data/build_finance.py
python topics/finance/tests/validate_finance.py
node --check topics/finance/topic.js
node --check topics/finance/data/finance-data.js
```

部署路径：`topics/finance/`。与其他专题共用 `css/map.css`、原有OpenStreetMap/Leaflet和GitHub Pages；不要开第二条同时发布Pages的工作流。建议将本模块纳入 `.github/workflows/drugs-pages-deploy.yml` 的 paths 触发与文件检查，并在主要页面的导航增加 `地方财政`。

## 审查说明

生成器与校验只核验结构与官方来源链接的存在，不代替对原始网页/政府PDF逐个现场再核。市镇地图数据库仍缺全国统一口径的2024综合债务工作簿；这次上线**不会声称拥有全国市镇综合债务地图**。B核心事件、来源链与数据字典见 `research/finance/b/`；完整历轮排除案和审查脚本保存在另附的A+B离线归档包。
## 2026-10-10 · 简洁州级地图与事件勾选交互（当前版本）

- **全国底色固定**：始终显示2025年13个非城市州的人均地方政府收支差额，城市州无可比口径显示灰色；债务/借款不再作为另一幅地图涂色，而是在点选州之后的下钻详情中呈现，杜绝各统计主体混用。
- **点击州放大**：单击州沿真实州界缩放、显示该州2025年人均收支与2022—2024综合债务/2021—2025借款明细（折叠）。高缩放级别显示县级真实边界供查询。仅莱法州有可核对的县市和时期财政数据，其他州县不推算不存在的县级数字。按“返回全国”恢复视图。
- **事件独立勾选**：单个复选框控制72个候选事件的县域聚合标记及事件列表；不改变国家收支底色。地图标记悬停显示来自原始description的简短内容摘录和县域示意提醒，右侧事件行同样附一句预览，点击阅读完整原文及来源。
- **视觉**：移除三张切换视图、债务指标主控制、大量默认脚注、冗余覆盖统计卡片；方法、历史债务、事件筛选与完整170条调查档案保留在可展开详情中。
- `tests/smoke_finance_browser.py` 覆盖真实 Chromium 桌面/手机的固定州级底色、点击放大、莱法州县市下钻、债务折叠、事件开关、悬停提示与恢复全国；三份既有财政数据一致性验证仍须全部通过。
