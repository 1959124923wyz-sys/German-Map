# 德国地图仓库清理 · 可恢复交接（2026-10-12）

## 主分支实际盘点
- 审计时主分支：`f0ca8d404d628904309d3d0b34d6d6422dcf48f8`，共458个被追踪文件、64,406,163字节。
- 递归Git树未发现提交的`node_modules/`、`__pycache__/`、`.pytest_cache/`、`.DS_Store`、Playwright测试截图目录或临时编辑器文件；按Git blob SHA严格比较也没有完全相同的重复文件。
- 最大的数据多为实际运行的行政区GIS、railway JS分段、官方财务原始表与可追溯研究，不应因为体积大就称作垃圾。

## 第一批已判定为可移出的文件
- `topics/infrastructure/data/bridge_bkg_counties_2025.geojson`：8,394,601字节，BKG县界研究阶段留在运行目录的大型GeoJSON。现有基建网站`topic.js`只读取`state_scores_2025.json`、`condition_evidence.json`、`events.json`、`bridge_county_metrics_2025.json`和`../../data/germany-states.geojson`；相应`smoke_browser.py`、`validate_data.cjs`和Pages部署脚本均无此文件引用。
- 该大文件在删除前已通过**独立归档分支** `archive/infrastructure-unused-bkg-geometry-20261012` 永久保留完整Git blob（原SHA `12f4d9625077abdaaeacc16c15086ed774ae0580`）。将来如需要研究这版GIS，可直接从归档分支复制；不能把当前移出理解为丢失国家测绘局原始证据。
- 移出后主分支预计减少8.4MB的无用静态负担，完全不影响已显示的16州、桥梁县级指标或22件工程档案。

## 防止仓库继续产生垃圾
- 新增根目录`.gitignore`，忽略Python缓存、Node依赖、Playwright HTML报告、编辑器临时文件、OS索引文件、本地venv及`.env`敏感文件。
- **明确保留**所有官方数据来源、原始研究CSV、审计过程、BKG正式县界候选、研究交接文档，以及运行时需要的GeoJSON。特别是`topics/industry/data/bkg_vg250_counties_2025_candidate.geojson`仍用于工业运行/源码校验，不可随便删除。
- 工业`R8_REGIONAL_FETCH_FAILURE.log`虽很短，但明确记录了官方404、是故障证据，不将其误判为普通本地临时日志。

## 验收及后续
- `topics/infrastructure/tests/validate_data.cjs`、基建真实浏览器、三专题原始数据及GitHub Pages部署须通过。网页地图未进行设计或内容删减。
- 后续可再审查研究过期文档/手动工作流，但必须先证明不被生产、CI、研究恢复入口所依赖。未经确认的来源和有意义的历史原始资料不做批量删除。
- 按用户规则，后续不做手机端专项、不扩大地图面积、不增加统一静态数据时效说明，外部数据自动搜索与更新仍关闭。