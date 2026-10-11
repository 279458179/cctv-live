# APTV 兼容性说明

订阅地址（当前暂停提供直播线路，不要导入 APTV）：

- 整合版：`https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv.m3u`
- IPv4 版：`https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv-ipv4.m3u`

两份文件目前仅包含暂停说明，没有频道线路。根目录的 `cctv-APTV-test.m3u` 也已清理失效 URL。IPv6 媒体地址已移除。

旧版 56 条历史媒体直链已撤下。2026-10-11 在承德电信 IPv4 直连网络抽查 CCTV-1 地址时，三条抽查线路均返回 HTTP 403；APTV 截图也显示全部线路超时。旧地址含上游短时签名，不再可用。

央视官网的直播网页入口可在浏览器或央视影音 App 打开：[直播大全](https://tv.cctv.com/live/m/)。这些网页由官方播放器播放；网页底层接口并非可公开复用的普通 m3u8。官网播放器可能使用 DRM 或会变化的临时地址。

央视官网入口可在浏览器或央视影音 App 打开：[直播大全](https://tv.cctv.com/live/m/)。官网网页 URL 不能作为 APTV m3u8 使用。当前仓库没有有效、可验证的 APTV 直播放源；后续只有在获得公开可用或用户自有授权的兼容流，并验证连续解码后才恢复订阅。

[诊断记录](docs/testing/cctv-ipv4-coverage-2026-10-11.md)保留旧快照的频道覆盖和失效说明。原始机器报告包含签名 URL，没有公开。
