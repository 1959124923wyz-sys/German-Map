# 06 · 德国环保争议地图

独立专题路径：`topics/environment/`；属于 German-Map 公共导航第 5 项（编号 06；07 铁路另行集成）。

## 来源、范围及统计语义

研究数据基准：2026-10-09。专题使用 154 条来源关联记录，包含：

互斥且穷尽**本专题已收录记录**的四个一级类型（41 + 10 + 11 + 92 = 154）：

- **直接行动** `archive`：41；细分交通干扰21、能源干扰10、设施破坏2、文化设施4、工程冲击4。
- **政策措施** `policy`：10。
- **组织／项目争议** `organization` 10 加独立 `facility_story` 1，共11；不把合法异议误认作违法阻工。
- **能源设施** `facility`：92；状态 `retired` 32、`awarded` 36、`ordered` 3、`scheduled` 21。

**全部记录**展示154条。网页只保留“全部、行动事件、环保政策、组织争议、能源设施”五个入口，移除了冗余的分类说明、快捷筛选、地点快捷定位、组织筛选及搜索控件。行动细分和设施状态仍以图例、点位及逐条来源详情展示。

**设施分类是某条记录的证据状态，不代表“所有设施均已停机”。** `awarded` 为煤电退出招标中标，`ordered` 为监管命令，`scheduled` 为未来计划；只有有明确依据的已停机设施属于 `retired`。数据原始表中包含未来年月日作为法定退出截止日期，不能误写成已经发生的环保行动。

政策锚点可能为联邦议院或发布地，设施点是能源项目附近位置；位置用于展示关联对象，不等于整个政策只有局部影响。组织诉讼/法律异议不等于违法行为；对破坏的认领须与法院认定和警方定性区分。事件损失须有独立可核资料，未知值不得补零或推测。

每条记录提供 `sources` URL；数据源包括德国议会、监管机关、法院、警方、机场/能源运营单位、德国媒体以及明确标注为当事方的公开声明。数据属于**精选核实档案**，不是德国所有环保组织活动的全面普查，也不是无害/有害的打分。

## 代码结构

- `index.html`：与主地图共享的顶部专题导航、Leaflet 地图左栏及统计／详情右栏。无需 API 密钥；OSM 瓦片失效时保持事件点位和本地行政边界。
- `topic.css`：只维护 06 差异化组件；公共配色、标题栏、导航、左右栅格、指标卡及抽屉样式继承 `../../css/map.css`。
- `data/records.js`：154 条带来源的原始记录；不会读写主站任何犯罪统计。
- `topic.js`：Leaflet 点位、五个一级入口（全部 + 四类互斥记录）、地点排行、点位交互、详情与来源。行动细分和设施状态通过图例显示；保留原始坐标，近邻符号仅做像素级视觉错位。
- `tests/smoke_environment.py`：桌面与手机视口 Chromium 交互测试。

底图改为与 01–05 一致的 OpenStreetMap/Leaflet，并在独立图层中读取 `data/germany-states.geojson`、`data/germany-counties.geojson` 绘制参考边界，复用统一的中文城市标签 `CrimeCityLabels`；边界加载失败不会阻塞 154 条点位数据。禁止将该专题事件点位当作县级犯罪率、州级评分或已经完成的所有发电设施关闭清单。

## 回归验证

```bash
node --check topics/environment/topic.js
node --check topics/environment/data/records.js
npm install --no-save --no-package-lock leaflet@1.9.4
python -m http.server 8765
# in another terminal:
python topics/environment/tests/smoke_environment.py
```

工作流：`.github/workflows/environment-map-smoke.yml`；全站静态部署复用 `drugs-pages-deploy.yml` 的共享 Pages 发布锁。不单独建立会并行竞争 Pages 的部署工作流。
