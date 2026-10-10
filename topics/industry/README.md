# 德国工业衰退地图 | industry (staging)
**所属项目**: German-Map；独立专题 `topics/industry/`。数据快照日期：2026-10-10。

## 页面和交付状态
- `index.html` / `topic.css` / `topic.js`：沿用项目的 Leaflet、`../../css/map.css` 深色页首、左右主地图/侧栏。默认只有**单色县市底色+红色重大企业事件点**，无能源/交通叠加和无多模式切换。
- `research/r1-events.json`：第一轮原始61条事件，其中10条继承鲁尔试点，继承的数据保留原始差异和警示。
- `research/r2-r3-events.json`：新增38条厂址/跨厂址候选（R2 15、R3 23），包含可追溯原始 URL、日期和岗位数字性质。
- **共99条不同事件ID，研究记录而非99家完整关闭工厂**。R3/R2部分信息来自ERM及地方新闻，需继续更新公告实施状态。
- `data/county-employment.json`：县级就业底图占位。官方同口径2019—最近年度县市制造业就业数据尚未成功核验，当前为空。**不允许填入捏造的就业增长率。**
- 暂时将县市填色标为“已登记重大收缩事件数”（0/1/2/3/4+），深色仅表示已有重大案例较多，**不得对外声称真实工业就业下降更多**。样本没有穷尽，不能做县排名。
- 红点位置只有已知示意坐标、项目 geocode_cache 的城市级参考点、匹配县行政区包围盒中心点；**绝非厂门位置**。没有足够信息的跨厂址资料只进列表不标点。地图事件与底色按 `state_iso + county_name + districtType` 匹配；跨行政区同名不要单靠城市同名猜测。
- R1生产岗位与研发行政岗位分别存储，`eligible_factory_marker:false`不标为工业工厂事件。集团总数及跨厂址合计不可在地图叠加为各厂裁员。
- **实际工业收缩率**未来从官方县市工业就业统计进入，经同口径、AGS、行政变更和保密值核查后替换占位文件。不可混合BA社会保险岗位与Destatis企业场所从业人员口径。

## 本地测试
项目仓库根目录执行：
```bash
node --check topics/industry/topic.js
node topics/industry/tests/validate_industry.cjs
python scripts/validate_site_assets.py
python -m http.server 8765
```
然后访问 `http://localhost:8765/topics/industry/`。需要网络获取 Leaflet 和 OSM 背景瓦片；事件数据/行政边界存于仓库，静态文件方式运行，无后端API。浏览器 `file://` 通常无法 `fetch` 本地 JSON，不应把本分支版本承诺为离线双击版。

## 上线前检查及维护组工作
1. 合并/上线前由维护组补齐全部专题顶部导航，建议在 `index.html` 以及 `topics/{drugs,immigration,environment,railway,finance}/index.html` 添加工业入口，**勿并行改动主线这些正在维护的页面**。
2. 校对R2/R3的计划最新实施状况，尤其 BioNTech 和跨企业并购重组。收到信息时修改当前事件，不复制新一条“裁员新闻”。
3. 接入官方县级就业收缩数据前，禁止“工业收缩率”的数字标签。统计保密/未覆盖应渲染空白，不补0。建议使用官方AGS+年份+行业覆盖版本索引，当前库的县边界只有name/state/districtType。
4. 继续工厂地址核验，以门牌厂区坐标替换县中心点；区分级别如 `site_exact`、`city_reference`、`county_reference`。
5. 建议将工业专题测试放入现有CI、统一Pages部署锁中；**不要**自行并行启用第二个Pages发布工作流。
6. 执行本专题的 `node` 验收和通用 `validate_site_assets.py`，浏览器点击县、点击新闻点、关闭点图层、切回全国、移动端宽度。

## 统计解释
- `jobs_affected` 可能是现有雇员、计划受影响岗位或计划净裁岗位，`jobs_basis` 有具体说明，不得相加作为实际失业总量。
- `reported_completed`、`confirmed_closed_activity` 表示有实施证据；`announced`、`under_implementation` 不能显示成已全面关闭。
- 企业宣称能源是关厂原因需归为“企业披露原因”，不能从个案自动推论全国因果关系。
