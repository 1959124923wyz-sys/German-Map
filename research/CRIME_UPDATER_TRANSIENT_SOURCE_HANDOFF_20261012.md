# 维护5第一批｜犯罪地图官方源临时宕机保护（2026-10-12）

## 触发事件与证据
- 2026-10-11 23:38 UTC（台湾时间10月12日早间），定时 GitHub Actions `Germany crime map updater` [run 38185034679](https://github.com/1959124923wyz-sys/German-Map/actions/runs/38185034679) 失败。
- 可复现的日志定位：`scripts/build_city_layers.py` → `scripts/build_munich_local_2025.py` → `parse_population()` → `city_build_common.download_json()`，慕尼黑政府人口表 `https://opendata.muenchen.de/de/api/3/action/datastore_search?resource_id=a641ce6a-4e01-4f4b-9976-1ae6a47e3762&limit=100` 返回 HTTP 503。
- 主线仓库仍有 `data/munich_local_2025.geojson` 的完整缓存：`meta.year=2025`、25个城区、25个稳定城区编号，缺少人口的城区数为0；此前的Pages部署和主线浏览器/配色测试成功。503本身不是「2025数据为零」的证据。

## 最小修复
1. `scripts/city_build_common.py` 对 HTTP 429/500/502/503/504、连接失败与超时统一给子进程临时故障退出码75（EX_TEMPFAIL）。404、403、JSON解析/数据校验错误不属于可保留情形。
2. `scripts/build_city_layers.py` 对返回码75采取只读、校验通过后保留原GeoJSON：必须有FeatureCollection、有效年份/唯一ID、可绘制EPSG:4326边界、注册指标真实数值；慕尼黑额外要求25个`munich-01..25`以及正人口。其他退出码或缓存缺失/损坏仍直接失败。
3. `scripts/test_city_build_common.py` 加入**完全离线**回归：指定HTTP错误与连接故障、404不降级、非法JSON不降级、完整2025慕尼黑缓存不重写、少一个城区或缓存缺失时必须阻断。
4. 已有 `germany-homicide-map-smoke.yml` 与定时更新workflow均执行 `python scripts/test_city_build_common.py`；PR改了 `scripts/build_city_layers.py` 会触发犯罪地图UI检查。仍需以实际Actions绿灯为合并门槛。

## 保护边界
- 不修改任何原始案件、人口、地理边界、标记或前端UI。
- 不删除主线对 `scripts/validate_city_layers.py`、显示县界拓扑和其他来源的验证要求。
- 保留缓存时发出明确 GitHub Actions warning；**缓存只是最后已核实版本，不代表已得到最新数据**，不能将缓存描述为新近更新。
- 临时故障状态之外的失败不能跳过；没有完整旧快照必须失败。
- 后续应在官方服务恢复后重新运行源更新，核对缓存与远端人口口径是否仍一致，不能猜测恢复时间。

## 发布与交接
- 本批源代码、测试、文档存于 `fix/crime-updater-transient-city-source-20261012`；PR和CI状态以GitHub为准。
- 新增脚本与逻辑必须通过PR校验，之后方可合并。合并≠服务端更新已经运行成功；真正验证降级需要观察下一次定时任务或受控测试。
- 后续仍需继续维护4的地图行为统一：跨专题桌面/390px实际点击、点击不自动移图、SVG/Canvas透明命中排查、配色语义和图例匹配、工业事件层的可读性。
