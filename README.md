# CCTV 官网直播入口合集

仓库原有的直播 m3u8 直链需要短时签名。2026-10-11 在承德电信 IPv4 直连网络抽查时，多条 CCTV-1 线路均返回 HTTP 403；你的 APTV 截图也显示所有频道线路超时。因此已从公开订阅中撤下旧媒体直链，避免继续提供确定不可用的地址。

当前 M3U 文件列出 CCTV-1 至 CCTV-17、CCTV-5+ 的央视官网直播网页入口。这些是网页地址，不是 m3u8 媒体流，不能导入 APTV 后直接播放；请用浏览器或央视影音 App 打开。央视官网播放器自行调用的流可能受 DRM、地域和客户端限制。由于你需要 APTV 可直接播放的 m3u8，当前公开订阅暂时不能满足这个要求。

## APTV 订阅地址

以下地址保留旧订阅路径以便你打开检查，但不要导入 APTV 播放：文件内是官网网页入口，不是视频流。

| 版本 | 地址 | 内容 |
| --- | --- | --- |
| 整合版 | `https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv.m3u` | CCTV 官网网页入口，非可播放流 |
| IPv4 路径 | `https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv-ipv4.m3u` | 与整合版相同 |

仓库不提供 IPv6 直播地址。GitHub Raw 镜像只影响订阅文件下载，不能修复媒体流超时。

## 导入和覆盖

央视官网入口可在浏览器打开：[CCTV 直播大全](https://tv.cctv.com/live/m/)。例如 [CCTV-1 直播](https://tv.cctv.com/live/cctv1/)。APTV 需要的是兼容且仍有效的 m3u8；该官网网页地址不能替代它。

[诊断与覆盖记录](docs/testing/cctv-ipv4-coverage-2026-10-11.md)说明历史快照失效情况。

## 更新方式

稳定的 APTV 订阅需要在承德电信直连网络获取可刷新或无短时签名的 IPv4 流地址，并验证 APTV 实际画面和连续播放。浏览器打开官网成功不代表 APTV 可播放。仓库目前没有能可靠地将央视官网 DRM 播放接口转换成 APTV 兼容 m3u8 的方案。

本仓库整理公开直播候选，不存储或转发视频内容。请遵守平台条款与内容权利要求。
