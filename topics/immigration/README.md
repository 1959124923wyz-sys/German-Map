# 德国非法移民与边境管制专题（德国犯罪地图05）

> German-Map 并行开发协作协议 v1.0 的执行记录。开发分支仅为 `feature/immigration-topic`；主地图与毒品专题均只读。本专题尚未集成生产主页。

## 分支、路径与权限边界

- 分支：`feature/immigration-topic`。共同起点：`8144810775f82bb798061e81cc75336d63d77691`。
- 可改：`topics/immigration/**`；为验证本专题所需、以 `immigration-` 开头的独立 `.github/workflows/immigration-*.yml` 文件。
- 不可改：`main`、`feature/drugs-topic`、`topics/drugs/**`、现有专题业务代码、公共页面、地图核心模块、已有 GeoJSON/数据、城市层与现有工作流。
- 特别禁止改动：`index.html`、`js/app.js`、`js/core/**`、`js/layers/county-layer.js`、`js/layers/state-layer.js`、`js/panels/**`、`css/map.css`、`data/germany-counties.geojson`、`data/germany-counties-display.geojson`、`data/germany-states.geojson`、`data/city_layers.json`、`.github/workflows/germany-homicide-map.yml`。
- 当前自动检测：`.github/workflows/immigration-scope-guard.yml` 在本分支的**所有推送**以及目标为 main、来自本分支的 PR 上执行；从与 main 的共同祖先开始审查所有修改路径。未通过检查不能视为完成阶段验收。
- 当前限制：检查是 CI 报错，不是 GitHub 服务器级的分支保护。若要防止有权限者绕过失败检查直接合并，仓库管理员还需要启用 GitHub Ruleset/Branch protection 并将检查设为必需；任何本专题代码都不会自动改动此设置。

## 专题接口（最终集成目标）

```js
window.GermanMapTopics = window.GermanMapTopics || {};
window.GermanMapTopics.immigration = {
  id: 'immigration',
  title: '非法移民',
  async loadData() {},
  activate(context) {},
  deactivate() {}
};
```

`activate(context)` 由主程序注入 Leaflet 地图实例、专题容器和地理数据读取接口，不获取/重建地图实例，不抢占主图缩放、州县点击、详情窗口或全局状态。退出应移除专题自建 Leaflet 图层、定时器、事件监听器和临时 DOM；不能用全屏 Canvas、透明盖层或全局 pointer-events 捕获鼠标。重复进入/退出必须可行。

### 集成阶段需要的共享接口（仅需求，当前不得修改公共代码）

1. `context.map`：现有 Leaflet map 对象；不可移除其他专题图层。
2. `context.container`：仅本专题可以渲染/清除的侧栏 DOM 容器。
3. `context.stateGeoJSON` / `context.countyGeoJSON` 或等价只读数据提供函数：共享当前经过验证的州县行政边界；不修改其坐标与 AGS。
4. 主程序负责切换其他模式、现有抽屉生命周期以及禁止重入。专题仅管理自建对象。
5. 如果主题图层与公共县州图层有交互优先级冲突，应在集成阶段由主程序集成协调；本分支不改变共享层的 pane、z-index 或事件。

## 数据治理（必须满足才可上线）

每个正式指标需要定义：指标 ID、中文名、德文原名、法定统计概念、统计时点/期间、年度、发布日期、来源机构、原始链接、地理层级、AGS、原始数值/单位、完整性、缺失地区和跨地区/跨年可比性。缺失值用 `null`，不把未公开或不适用写成 0，不根据全国/州数据虚构县级分布。所有抽样、覆盖范围不完整的数据必须显式标注。

严格区分：非法入境被查获（人数/案件数）、非法居留被查获、负有离境义务人员、暂缓遣返（Duldung）、庇护申请人、人口走私案件、离境命令、实际离境/遣返。不同数据库口径不做加总，不以国籍、外国人口、庇护寻求者总数充当非法移民数量。

优先来源：德国联邦警察（Bundespolizei）、联邦刑警局（BKA PKS）、外国人中央登记册（AZR；联邦议院公开答复）、联邦统计局（Destatis GENESIS）、Eurostat、Frontex。具体数据文件纳入前需再次核对原始表号、数据定义与许可。

## 验收门槛

1. 数据有来源，缺失非零，地域分布没有推断造假。
2. 模块可 load → activate → deactivate → activate，不遗留互动遮挡。
3. 不接管公共缩放、州/县点击、抽屉和全局状态。
4. `verify_scope.py` 对所有提交进行变更路径审计，`unittest` 通过。
5. README/数据元数据列出来源、口径、覆盖、缺失及已知限制。
6. 阶段性交付仅提交此分支，可发起到 main 的 **Draft PR**，不得自行合并或部署正式网站。

## 执行与测试

本分支本地检查：

```bash
python -m unittest discover -s topics/immigration/tests -p 'test_*.py'
python topics/immigration/scripts/verify_scope.py --base "$(git merge-base origin/main HEAD)" --head HEAD
```

CI 同时执行上述检查。本 README 是约束文件，不代表已经存在经核实的全国县级非法移民数据或完成生产集成。

## 2026-10-08 · 州级地图绘制阶段

独立测试页面 `topics/immigration/index.html` 读取**主仓库只读** `data/germany-states.geojson`。地图按不同来源切换：AZR 2025年底的离境义务总人数／持Duldung人数／无Duldung人数；以及联邦警察2025年度遣返执行量（按执行机构统计）。

- 16州原始数值均与官方表对应（AZR Drucksache 21/4103 第21页；遣返 Drucksache 21/4403 第4页），使用不同来源的独立元数据。
- 仅做**五档州级绝对人数分级着色**，不生成县级估值、不宣称高低“风险”；没有人口分母，不能解释为移民人口占比。
- 指标切换改变地图颜色、五档图例、国家总量、州详情和前五州列表；缺失状态用灰色。
- 生产集成接口仍为 `loadData / activate(context) / deactivate`，额外公开 `selectState(iso)` 和 `selectMetric(id)`，使主程序现有州级点击逻辑能调用组件，而**不在专题内部抢占地图事件**。
- `activate` 的着色面在 zIndex 215，`interactive:false` 且 pane `pointer-events:none`；主程序可能需要在统一集成阶段隐藏原有县级高透明填充，以免遮住本主题颜色。该操作由公共地图最终集成负责。
- 独立测试页的 Leaflet 州点击层仅在测试页创建，不属于导出的专题组件；生产主程序不得复制该层。
- 退出清除本专题 Leaflet 图层及自建DOM监听器，不动其他业务图层、州县边界和主地图状态。测试页面可点“退出/重新进入”手工烟测。

### 使用方法

在仓库根目录启动静态服务器（仅本地，不触发正式发布）：

```bash
python -m http.server 8765
# 浏览器访问 http://localhost:8765/topics/immigration/
```

主程序最终集成至少提供 `context.map`、`context.container`、`context.stateGeoJSON`；公共州级选择回调使用 `window.GermanMapTopics.immigration.selectState('DE-NW')`。所有代码保持在本专题目录或 immigration 前缀工作流内。
