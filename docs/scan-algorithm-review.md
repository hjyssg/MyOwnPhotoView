# 扫描核心算法 Review 文档

本文用于代码评审（review），覆盖当前项目扫描链路中最核心的三部分：

- 日期获取（created_at）
- 地区获取（location）
- 地区聚合（location aggregation）

并补充整体扫描流程、复杂度与改进建议。

---

## 1. 扫描主流程（`backend/scanner.py::scan_directory`）

### 1.1 输入与目标

- 输入：目标目录 `directory`、数据库会话 `db`
- 目标：
  - 遍历目录下支持的媒体文件（图片/视频）
  - 生成或更新数据库元数据
  - 标记已从磁盘消失的历史文件为软删除

### 1.2 关键步骤

1. **预加载历史记录**
   - 按目录前缀从 DB 查询已有 `MediaItem`
   - 构建 `existing_items[abs_filepath] -> item`

2. **候选文件发现**
   - `os.walk(directory)` 递归遍历
   - 仅保留受支持扩展名（图片/视频）

3. **增量判定**（跳过未变化文件）
   - 条件：`not force_rescan` 且 DB 存在记录且
     - `mtime` 一致
     - `size` 一致
     - `content_hash` 非空
   - 满足则计入 `skipped`

4. **内容指纹生成**
   - 默认使用采样哈希 `_hash_file_sampled`
   - 小文件全量哈希，大文件 head/middle/tail 采样
   - 失败时回退到路径指纹 `_filename_fingerprint`

5. **媒体类型分支处理**
   - 图片：提取 EXIF、坐标、来源类型、缩略图
   - 视频：抽帧缩略图、提取时长、设置 source_type=video

6. **批量提交**
   - `COMMIT_EVERY` 达阈值即 `db.commit()`，降低事务膨胀

7. **缺失文件软删除**
   - DB 中存在、扫描中未见到 -> `is_deleted=1` + `deleted_at`

---

## 2. 日期获取算法（created_at）

### 2.1 图片日期来源优先级

在 `_process_image_file` 内：

1. EXIF `DateTime`（`piexif.ImageIFD.DateTime`）
2. 文件名模式解析（`_parse_creation_time_from_filename`）
3. 文件系统 ctime（`stat().st_ctime`）
4. `datetime.utcnow()` 最后兜底

### 2.2 文件名解析规则

支持两类主模式：

- `YYYYMMDD_HHMMSS`（允许 `-` `_` `T` 等分隔）
- `YYYYMMDD`

例如：

- `IMG_20250101_093012.jpg`
- `2025-01-01 09-30-12.png`
- `20250101.mov`

### 2.3 视频日期来源

当前实现视频走 `_fallback_creation_time`，即：

- 文件名可解析则用文件名
- 否则用 ctime

> 说明：当前尚未使用 ffprobe 的 `creation_time` 元数据作为优先来源。

---

## 3. 地区获取算法（location）

### 3.1 GPS 提取

在 `_extract_exif_info`：

- 从 EXIF GPS 读取 DMS（度分秒）
- `get_decimal_from_dms` 转十进制度
- `_is_valid_coordinate` 过滤非法值：
  - `None`
  - `(0,0)`
  - 越界经纬度

### 3.2 逆地理编码

在 `reverse_geocode_location`：

- 输入合法坐标后调用 `reverse_geocoder.search`
- 结果包含国家/省级/城市字段
- 通过 `location_zh_map.json` 做中文映射
- 返回拼接地点字符串，如：`中国 上海 上海`

### 3.3 缓存策略

- `@lru_cache(maxsize=10000)` 缓存坐标逆地理结果
- 重复坐标可避免重复 geocode 调用

---

## 4. 地区归一化与聚合算法

地区聚合分两层：

1. **后端语义聚合（城市级）**
2. **前端地图显示聚合（网格级，随 zoom 变化）**

### 4.1 后端语义聚合（`/api/locations`）

1. 从 DB 取可上图素材（有经纬度且未删除）
2. `normalize_location_name` 产出：
   - `location_city`
   - `location_key`（标准化键）
3. 按 `location_key` 分组：
   - `count += 1`
   - `sum_lat += latitude`
   - `sum_lon += longitude`
4. 输出中心点：
   - `center_latitude = sum_lat / count`
   - `center_longitude = sum_lon / count`
5. 按 `count desc` 排序返回

### 4.2 前端地图网格聚合（`MapView`）

1. 根据当前 zoom 选 cell 大小（低 zoom 粗、高 zoom 细）
2. 以 `floor(lat/cell), floor(lon/cell)` 分桶
3. 每桶显示一个 marker：
   - 单地点：常规图钉
   - 多地点：聚合图标（数量气泡）

这层属于“可视化聚合”，不改变后端语义分组结果。

---

## 5. 复杂度与瓶颈

### 5.1 时间复杂度（粗略）

- 遍历文件：`O(N)`
- 哈希：接近 `O(N)`（采样哈希降低大文件 I/O）
- 图片解码与缩略图生成：`O(N_img)`
- 视频抽帧与时长探测：`O(N_video)`
- 软删除对比：`O(N_db)`

### 5.2 主要瓶颈

- 磁盘 I/O（哈希 + 缩略图）
- ffmpeg/ffprobe 子进程开销
- 大目录下 DB 写入与 commit 频率

---

## 6. Review 风险点与改进建议

1. **ctime 跨平台语义差异**
   - Windows 与 Unix 对 ctime 定义不同
   - 建议：日期兜底优先 `mtime`，并在文档中明确策略

2. **视频时间准确性**
   - 建议增加 ffprobe `creation_time` 读取优先级
   - 无元数据时再回退文件名/mtime

3. **地区层级化聚合能力**
   - 当前主键偏城市粒度
   - 建议引入 country/admin1/city 三层 key，支持“省级/国家级”统计

4. **异常可观测性**
   - 建议将扫描失败原因、文件级错误计数落入结构化日志
   - 便于定位某些坏文件导致的扫描质量问题

---

## 7. 评审关注清单（Checklist）

- [ ] 日期优先级是否符合业务认知（EXIF > 文件名 > 文件时间）
- [ ] ctime 兜底是否需改为 mtime
- [ ] 视频 `creation_time` 是否列入近期迭代
- [ ] 地区归一化词典是否覆盖主要样本
- [ ] 聚合中心点策略（均值）是否满足地图展示预期
- [ ] 扫描进度/失败日志是否足够支持排障
