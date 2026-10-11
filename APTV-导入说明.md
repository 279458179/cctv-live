# APTV 导入测试说明

文件：仓库根目录 `cctv-APTV-test.m3u`，可在 APTV 中通过本地 M3U/文件方式导入。

这是 2026-10-11 承德电信直连 IPv4 检测生成的历史测试合集：56 条唯一线路，覆盖 16/18 个目标频道，不含 IPv6 字面地址。检测时间已超过健康结果复用窗口，部分 URL 带有短时签名，当前可能已经失效；请把它用于 APTV 导入和客户端兼容性测试，不要当作当前稳定订阅。

频道覆盖为：CCTV1 4、CCTV2 6、CCTV3 4、CCTV4 中文国际 4、CCTV5 0、CCTV5+ 2、CCTV6 5、CCTV7 1、CCTV8 1、CCTV9 3、CCTV10 0、CCTV11 5、CCTV12 5、CCTV13 3、CCTV14 6、CCTV15 2、CCTV16 2、CCTV17 3。CCTV5 和 CCTV10 暂时跳过；只有 CCTV2、CCTV14 达到六条。

在 APTV 添加本地 M3U/文件订阅并选择 `cctv-APTV-test.m3u`。先测 CCTV1、CCTV4、CCTV5+、CCTV14 的画面和声音，并查看同名条目是否聚合。记录可播放频道、是否有声、缓冲情况和 APTV 播放器内核。播放中自动切备、晚高峰表现仍待实际验证。

[承德电信 IPv4 覆盖摘要](docs/testing/cctv-ipv4-coverage-2026-10-11.md)列出逐频道线路数与核验边界。含完整签名 URL 的原始机器报告保留在本机忽略产物中，未放入仓库。该 M3U 是本地测试文件，不是已发布的公网订阅链接；`subscriptions/` 正式文件没有修改。
