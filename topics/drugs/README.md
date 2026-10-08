# German-Map — 毒品问题专题 / Drug Topic

**工作分支：** `feature/drugs-topic`；与 `feature/immigration-topic` 并行。当前阶段不修改主站共享文件。

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
