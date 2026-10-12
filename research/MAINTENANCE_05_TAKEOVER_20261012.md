# 德国地图｜维护4→维护5接手手册（2026-10-12）

> 文档性质：维护工作法、已核实仓库基线与待办清单；**不是新增数据、修复或上线声明**。本轮只建立独立分支，不修改生产代码、GIS数据、页面或CI。下列事实在 2026-10-12 从 main、PR、Actions 与 research 交接文档核对。

## 0. 基线、范围及证据
- 仓库：`1959124923wyz-sys/German-Map`；main 在接手核对时为 `2986d994ef03ff2e29cdd4129845af6bc8988eb2`，对应 PR #69 的配色治理。
- 网站为**十种专题模式、九个HTML页面**：暴力犯罪、财产犯罪（同一主页双模式）、毒品、移民、环保、铁路、地方财政、工业衰退、基础设施、住房危机。
- 维护4的关键合并记录：[#64](https://github.com/1959124923wyz-sys/German-Map/pull/64) 导航/相机与假00000；[#65](https://github.com/1959124923wyz-sys/German-Map/pull/65) 犯罪州县点击；[#66](https://github.com/1959124923wyz-sys/German-Map/pull/66) 州主动定位/移动面板；[#67](https://github.com/1959124923wyz-sys/German-Map/pull/67) 工业SVG命中；[#68](https://github.com/1959124923wyz-sys/German-Map/pull/68) 视觉外壳；[#69](https://github.com/1959124923wyz-sys/German-Map/pull/69) 语义配色。
- 以上PR已合并；关联Actions绿灯是**当时版本的CI结果**，不等于所有用户侧浏览器场景永远无Bug。
- 既有规范：`README_DEV.md`、`research/ATLAS_INTERACTION_HANDOFF_20261011.md`、`research/ATLAS_VISUAL_UNIFICATION_20261011.md`、`research/ATLAS_COLOR_SEMANTICS_STANDARD_20261011.md`、`research/CRIME_COUNTY_INTERACTION_HANDOFF_20261011.md`、`research/CRIME_STATE_FOCUS_MOBILE_HANDOFF_20261011.md`、`research/THREE_TOPICS_POINTER_AUDIT_20261011.md`、`topics/STATE_DOSSIERS_HANDOFF_20261011.md`。遇到具体专题先读该目录的 README/research/tests。

## 1. 必须沿用的工作风格
1. **主动、少打断、真交付**：自主分解研究/排错步骤，减少无意义的确认和进度汇报；每次反馈说明可核验的结果、局限及保存状态。大工作按可独立验收的批次提交，不把未上传内容叫「已保存」。
2. **从用户感受回溯底层原因**：先定位能复现的异常与最小场景，再查事件命中、Leaflet pane/z-index、GeoJSON对象、相机API或数据范围。避免只调CSS盖住问题、复写整张地图或大规模无关重构。
3. **标杆=暴力/财产犯罪的交互**：全国首次点击州→保留州概览；进入州后可点击县市→县市详情；按需返回州/全国。普通点击不擅自 `fitBounds/panTo/setView`；仅明确的定位操作可移动视角。
4. **先修最突兀者，再做共同底座**：共享导航、暗色外壳、版式、侧栏层级、移动端触控；保留专题专属含义、颜色和数据口径。视觉对齐不等于让所有图层都同色。
5. **层级渐进披露**：全国首屏简洁、地图为主；区域/县市/事件详情根据操作展开。超长证据、方法、企业列表放资料室、折叠内容或独立页签，不挤满地图。
6. **事实完整性优先于丰富度**：使用来源、采集年份、口径、分子/分母、AGS映射、坐标准确度；区分“记录的事件/案例”与“全量发生率/实际发生数”。缺失不可当0，也不可因为专题名具有危机感就把数值涂红。
7. **保护主线**：独立分支→最小修改→源码/数据/站点链接校验→桌面1440+手机390真Chromium验收（有意义的真实鼠标/触控而非仅合成事件）→PR→CI→合并→Pages检查→短交接。
8. **检查失败时停止发布**：除非有公开证据、经过核验，不称“已上线”“已彻底修好”。源站503与本站逻辑回归失败须分开处理；失败数据刷新不得覆盖上一批有效快照。

## 2. 三种必须警惕的复发类型
**类型A：假区域编码/对象形状混淆。**
住房显示 `00000` 并非400县源数据错误，而是Leaflet `layer` 被当成 GeoJSON `feature` 传给 tooltip；纠正 `tooltipText(l.feature)` 后将浏览器断言写入 `topics/housing/tests/smoke_housing_browser.py`。同类问题应核对 `feature.properties`、AGS 和 null/undefined，而非猜测原表错误。

**类型B：透明Canvas拦截实际点击。**
犯罪州、Berlin街区、city detail与工业上层覆盖出现过 Canvas 尺寸远大于可见图形的鼠标捕获；对高层可交互点/边界用共享 `L.svg({pane: ...})`，在视窗移出时及时卸载局部图层；测试应执行真实坐标点击和 `document.elementsFromPoint()`，覆盖打开面板→县点击→跨州→关闭→再次点击。不要把所有业务层改成Canvas后仅用 `layer.fire('click')` 验收。

**类型C：无意的强制镜头与侧栏遮挡。**
`selectState` 及 `chooseCounty` 等数据选择默认不移动；主动定位才根据真实几何做 `fitBounds`，计算桌面浮窗/手机控件非对称留白并限制缩放。移动端资料室默认紧凑、可展开，保留标题及关闭控件。

## 3. 数据与色阶契约
- 正式规范：`research/ATLAS_COLOR_SEMANTICS_STANDARD_20261011.md`；执行表：`js/core/atlas-color-semantics.js`。
- `pressure-high` 高值高压力→浅至深红；`pressure-low` 低值高压力→深至浅红；`neutral` 蓝阶仅代表大小，不得称为危机程度；`diverging` 带零值意义的双向色标；`categorical` 清晰的分类色。缺失灰色，不填零。
- 住房2022人均居住面积：小值深红/大值浅；2022存量、2025挂牌租金：高值深红；其余无法直接判优劣者保持中性描述色。财政赤字红盈余绿，债务高值暖色但不能推断一定陷入财政危机。
- 铁路未知/未测区段不应与验证安全的绿色一致。犯罪登记率、工业收录事件数、毒品登记/污水检测、移民国籍人数份额等都有各自的定义边界。
- 增加新指标时：先登记稳定key、单位、年份、分母、缺失及颜色语义，保证图例与实际映射一致，再发布。

## 4. 关键脚本、CI及阅读入口
| 部分 | 主要文件或命令 | 测试要证明的内容 |
|---|---|---|
| 犯罪主交互 | `js/app.js`、`js/layers/state-layer.js`、`js/layers/county-layer.js`、`js/layers/city-detail.js`；`python scripts/smoke_test_ui.py`、`python tests/smoke_county_dossier.py` | 原400县10项指标、真实点击、州县返回、源范围与离线底图模拟 |
| 三大专题 | `.github/workflows/three-topics-pr-check.yml` | `topics/industry/tests/smoke_industry_browser.py`；`topics/infrastructure/tests/smoke_browser.py`；`topics/housing/tests/smoke_housing_browser.py`；支持390px |
| 各专题数据 | `topics/industry/tests/validate_industry.cjs`；`topics/infrastructure/tests/validate_data.cjs`；`topics/housing/tests/validate_greix.cjs` 和 `validate_local_archive.cjs` | 数量、身份编码、来源、分母、时间以及口径 |
| 共享外壳 | `css/atlas-shared-shell.css`、`scripts/smoke_atlas_shell.py`、`.github/workflows/atlas-shared-shell.yml` | 十模式九页面、1440/390、导航顺序/唯一active/水平溢出；截图共20张 |
| 配色语义 | `js/core/atlas-color-semantics.js`、`tests/validate_atlas_color_semantics.cjs`、`.github/workflows/atlas-color-governance.yml` | 语义登记、低值反向、分布中性色 |
| 全站链接 | `python scripts/validate_site_assets.py` | 所有本地CSS/JS路径及页面导航 |
| 部署 | `.github/workflows/drugs-pages-deploy.yml` 及 GitHub Pages 相关 workflow | PR测试成功不等于Pages已发布；核对主线部署工作流实际结论 |

注意：本项目官方GIS与统计快照已提交；纯UI检查优先用版本化数据，不能每次都调用外部API后被源站503误伤。通用外部数据刷新不应以「接口暂不可达」把旧数据清零。

## 5. 已知未完成与高优先级
1. **跨专题真实体验复核仍有价值**：尤其县市实点、缩放边界、不同pane压住点击、返回州/全国的面板状态、手机侧栏触摸、事件点开关及首屏简洁。之前CI通过不替代新功能加入后的端到端测试。
2. **配色V1的后续完整治理**：逐专题图例方向/单位/时间、缺失灰色、可访问性、全量新增指标语义登记的自动约束；目前不要声称所有未来指标都已自动覆盖。
3. **工业地图库是样本而非全国衰退率**：231条记录不等于231座倒闭工厂；不能叠加计划裁员人数当实际失业人数；全国400县WZ2008-C制造业2019至今官方同口径就业时序仍欠缺。
4. **住房已有大量县级字段**：2022普查与2025挂牌租金不可机械计算涨幅，地方档案及历史数据不能伪造成全量跨年序列；后续查漏须按来源逐条核。
5. **基础设施指数仍是试验结果**：22项工程是选择性样本；TLI、DIN与ZEB不能混同；桥梁候选县级数据未具备官方全德风险排名意义，空间匹配缺口不得静默分摊。
6. **2026-10-11晚间定时犯罪数据更新失败**：Actions run [38185034679](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38185034679) 的报错是慕尼黑官方开放数据接口返回HTTP 503，发生在 `scripts/build_munich_local_2025.py` 的 `parse_population` 调用 `download_json`。主线同SHA的UI/Pages/配色测试当时成功。处理建议：调查源站恢复或采用可追溯last-known-good降级机制，避免掩盖失败和意外清零；先隔离研发并进行数据一致性验收。

## 6. 下一次真正修改的执行清单
- 核对当时main最新SHA、已合并PR、待办及GitHub Actions；发现主线变化先重新评估，避免旧基线写回。
- 先写一条可复现的用户场景与根因证据；记录不变的数据、口径、交互和文件范围。
- 每轮一到少数几种相关Bug，不跨无关模块推倒重来；修改附可重复真鼠标验收。
- 独立分支至少保存：补丁、最小测试、必要来源/口径解释、简明HANDOFF。推送并检验commit SHA成功后才称保存。
- PR阻断检查不通过时不合并；合并之后另核验Pages部署，再报告「已发布」。
- 进度通知以实际结果为主，报告：根因、受影响主题、改动和保留范围、验证证据、GitHub链接、剩余事项。

## 7. 本次接手结果
本次仅核实历史PR、交接文档、测试及workflow，并保存接手规范；**未执行新的浏览器测试、未修复上述存量问题，亦未修改或部署网站**。
