# APTV 导入测试说明

公开订阅入口：

- 整合版：`https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv.m3u`
- IPv4 版：`https://raw.githubusercontent.com/279458179/cctv-live/main/subscriptions/cctv-ipv4.m3u`

两份文件目前字节相同，均是承德电信 IPv4 测试快照，不含 IPv6。也可用仓库根目录的 `cctv-APTV-test.m3u` 本地导入。

这是 2026-10-11 检测生成的历史合集：56 条唯一线路，覆盖 16/18 个目标频道。检测时间已超过健康结果复用窗口，部分 URL 带有短时签名，当前可能已经失效；请把它用于 APTV 导入和客户端兼容性测试，不要当作当前稳定订阅。

频道覆盖为：CCTV1 4、CCTV2 6、CCTV3 4、CCTV4 中文国际 4、CCTV5 0、CCTV5+ 2、CCTV6 5、CCTV7 1、CCTV8 1、CCTV9 3、CCTV10 0、CCTV11 5、CCTV12 5、CCTV13 3、CCTV14 6、CCTV15 2、CCTV16 2、CCTV17 3。CCTV5 和 CCTV10 暂时跳过；只有 CCTV2、CCTV14 达到六条。

在 APTV 添加本地 M3U/文件订阅，或直接添加上方公开地址。可先测 CCTV1、CCTV4、CCTV5+、CCTV14 的画面和声音，并查看同名条目是否聚合。记录能播放的频道、声音、缓冲情况和播放器内核。播放中自动切备与晚高峰表现仍待实际验证。

[承德电信 IPv4 覆盖摘要](docs/testing/cctv-ipv4-coverage-2026-10-11.md)列出逐频道线路数与身份核验边界。原始机器报告含签名 URL，保存在本机忽略产物中，没有复制到仓库。
