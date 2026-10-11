# CCTV 直播订阅源（稳定版）

为 Apple TV + **APTV** 打造的 CCTV 全频道直播订阅源，专治公开源「一直缓冲、卡顿」。

- **CCTV-1 重点保障**：1 个主线路 + 5 个备用线路，全部经人工逐条抓帧核验台标内容。
- **全频道覆盖**：CCTV-1 ~ CCTV-17、CCTV-5+、CCTV-4K。
- **IPv4 / IPv6 / 整合** 三份订阅，按需导入。
- **稳定优先**：所有线路经**真实解码检测**（不只是读元数据），能识别「有声音没画面」的 DRM 加密流。
- **不折腾**：不每天自动刷新，实测稳定后长期使用。线路失效时手动重新构建即可。

## 订阅地址

把下面的地址粘贴到 APTV 的「订阅」里即可（推荐整合版）。

| 版本 | 地址 | 说明 |
| --- | --- | --- |
| **整合（推荐）** | `https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv.m3u` | IPv4 + IPv6 全部线路 |
| IPv4 | `https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv-ipv4.m3u` | 仅 IPv4，兼容性最好 |
| IPv6 | `https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv-ipv6.m3u` | 仅 IPv6 |

> 若 `raw.githubusercontent.com` 访问慢，可换成镜像前缀：
> `https://ghproxy.net/https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv.m3u`

## APTV 导入方法

1. 打开 APTV → 底部 **设置** → **订阅** → 右上角 **+**。
2. 名称随意（如 `CCTV`），地址填入上面的订阅地址。
3. 保存后回到首页，等待拉取完成即可观看。

## CCTV-1 线路说明

CCTV-1 采用 **1 主 + 5 备** 共 6 条线路，列表里按 `[主]`、`[备1]`…`[备5]` 标注。
带 `✓已核验` 标记的线路，是我逐条抓帧、目视确认过台标内容确实为对应频道的。

| 线路 | 来源 | 说明 |
| --- | --- | --- |
| 主 ~ 备5 | 公开直播源（人工核验） | 1280x720，已确认台标正确，非官方 DRM 源 |

播放器会自动选中第一条可用线路；如果主线路失效，会自动切到备用。

## 已排除的问题源（重要）

构建过程中发现并**永久拉黑**了以下几类源，避免你再次踩坑：

1. **央视官方 CDN（`ldncctvwbcd` / `ldncctvwbnd` 路径）**
   路径里的 `cdrmld` = **China DRM 加密流**。用 `ffprobe` 只能读到元数据（显示 1280x720 H264），
   看起来"合格"，但视频宏块实际加密 —— 播放时**只有声音、没有画面**（画面为粉色/花屏）。
   这类源已全部移出订阅。
2. **`ali-m-l.cztv.com/channels/lantian/channel21`**
   上游多个仓库把它标为 CCTV1，实测台标是 **CCTV-13 新闻（中国蓝新闻）**，属**频道串台**。
3. **`event.pull.hebtv.com/jishi/cp1`**
   实测画面是 **TVU networks 测试卡**（静止无信号），无实际节目内容。
4. **`bztv.tvbus.cc`**
   所有频道都返回同一个 404 页面，是失效源。

## 线路来源与筛选逻辑

1. **人工核验白名单**：逐条抓帧、目视确认台标内容正确后写入脚本，优先级最高。
2. **社区公开源聚合**：从 10+ 个公开 m3u 仓库收集 CCTV 频道，去重后逐条做**真实解码检测**
   （解码错误率 + 帧间变化），能自动识别 DRM 加密流、死流、静止测试卡。
3. **打分排序**：人工核验源 > 可解码源，其余按分辨率、响应速度、线路归属综合排序。

## 关于 IPv6

公开的 IPv6 直播源绝大多数来自**移动运营商网络**（`2409:` 前缀）。电信家庭宽带访问时，
部分线路可能不通，属于跨运营商限制，并非源本身失效。建议**优先使用整合版或 IPv4 版**，
IPv6 版作为补充尝试。

## 目录结构

```
.
├── subscriptions/          # 生成的订阅（APTV 直接使用）
│   ├── cctv.m3u            # 整合版
│   ├── cctv-ipv4.m3u       # 仅 IPv4
│   └── cctv-ipv6.m3u       # 仅 IPv6
├── scripts/
│   ├── build.py            # 构建脚本（拉取 → 实测 → 打分 → 生成）
│   ├── sources.json        # 上游源清单
│   └── data/
│       ├── manual.m3u      # 人工精选国内源
│       ├── geo_cache.json  # 归属地缓存
│       └── latest.json     # 最近一次构建结果
└── docs/
    └── 阅兵80周年回放.m3u    # 附加：2025.9.3 阅兵完整回放（央视官方源）
```

## 重新构建（线路失效时）

```bash
# 需要 ffprobe（brew install ffmpeg）
python3 scripts/build.py --timeout 8 --workers 32
```

也可以在 GitHub 仓库的 **Actions → Build Subscriptions → Run workflow** 手动触发，
构建完成后会自动提交更新。

## 免责声明

本仓库仅收集、整理网络上公开的直播流地址，供个人学习与测试使用，不存储、不转发
任何视频内容。所有频道内容的版权归原权利人所有。请勿用于商业用途，并在测试后
自觉支持正版收视途径。

## APTV 本地测试

仓库根目录提供 [cctv-APTV-test.m3u](cctv-APTV-test.m3u) 供临时导入测试；该合集是 2026-10-11 承德电信 IPv4 检测样本，签名可能已过期。频道缺口、检测边界与导入步骤见 [APTV-导入说明.md](APTV-导入说明.md) 和 [覆盖摘要](docs/testing/cctv-ipv4-coverage-2026-10-11.md)。
