# R5 数据源调查补充（2026-10-10）

## Regionalatlas 的县级可得指标
### A. 真实制造业就业结果与替代指标必须区分
- **首选结果变量**：同口径按县市制造业从业人数（德国BA工作地就业 WZ-C 或 Regio 42111-02-03-4）；有2019基期与最新同口径年份才可计算真实就业下降率。
- **备选辅助指标** `AI0704`：Regionalatlas“制造业就业人员占所有就业人员比例”，是占比，不等于制造业就业人数，下降也可能是服务业增长导致；**不得直接当作工业就业收缩底色**。
- **备选辅助指标** `AI0405`：Regionalatlas 企业登记来源，“制造业受雇人员 / 每千名劳动年龄人口”，是岗位密度指标，分母人口变化也会造成指标变化；只用于辅助分析。
- **辅助分析**：`AI1001`、`AI1002` 投资及劳动薪酬相关工业指标。

相关来源： https://github.com/bundesAPI/regionalatlas-api ；https://regionalatlas.statistikportal.de/ ； https://github.com/maschinenlesbar-org/regionalatlas-cli

### B. 工业县级数据可尝试从 GIS API 批量取回
- 官方 Regionalatlas 服务（第三方开源工具文档确认）：`https://www.gis-idmz.nrw.de/arcgis/rest/services/stba/regionalatlas/MapServer/dynamicLayer/query`。
- `bundesAPI/regionalatlas-api` 项目记录了请求中通过 `layer` 查询具体指标数据源 `AI0704` 和 `AI0405` 的方法；维护组需要实测接口响应、字段说明、年份以及402县的覆盖率。
- `regionalatlas-cli` 可做测试工具，用 `regionalatlas indicators --search Verarbeitendes` 确认所有年份；`regionalatlas query AI0704 --level kreis --year 2019` 和 `--year 2024` 拉取县级辅助面板；需注意工具实时配置、服务API变化、2019/2024边界对齐。
- **不得用AI0704 或 AI0405 替代真实人数变化率**；即使抓取成功也只能以标签“制造业就业占比变化”或“制造业岗位密度变化”作为单独研究数据。

### C. 黑森 OpenData 已暴露可免费批量下载的 CSV/TXT 端点，但**只能覆盖黑森**
- https://opendata.hessen.de/en/dataset/regionalatlas-deutschlandindikatoren-des-themenbereichs-industrie
- https://opendata.hessen.de/de/dataset/regionalatlas-deutschlandindikatoren-des-themenbereichs-unternehmen
- 资料说明明确：GENESIS 区域统计表已先过滤为**黑森**，CSV下载无需地区统计库注册；原本完整的全国 GENESIS flat-file 通常需要注册账户身份。
- 许可：德国政府数据使用许可署名2.0版（dl-by-de/2.0），发布时必须保留数据提供方署名。
- 下一批应先试下载该 CSV，再查2019与2024/25的**同一时间序列**、县级数据缺失率和元数据的统计覆盖门槛，不能把黑森样本无声明地外推全国。

## 这一阶段结论
1. 原工业地图 R1-R4 **117条事件**及来源已独立GitHub存档，不依赖对话上下文恢复。
2. 目前 **全国县级实际制造业就业面板仍未批量验收**。地图不会因此做任意模拟底色。
3. 此处记录新检索到的官方替代渠道及其科学局限，供研究组或维护组从这里继续。所有数据源不等于实际下载成功。

引用截至2026-10-10公开页面核实。