#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCTV 直播订阅构建脚本 (APTV / Apple TV 专用)

原理:
  1. 央视官方 CDN ("央视影音"网页播放器同源) 提供免鉴权 HLS, 但仅 CCTV-1 / CCTV-13 开放,
     因此这两个频道以官方源作为主用线路 (5 家 CDN 互备), 社区源兜底。
  2. 其余频道从多个公开 m3u 仓库合并, 用 ffprobe 实测可用性/分辨率/响应速度并打分排序。
  3. 输出 IPv4 / IPv6 / 整合 三份订阅到 subscriptions/。

用法:
  python3 scripts/build.py                    # 全量 (含实测, 推荐)
  python3 scripts/build.py --no-probe         # 只合并去重, 不实测 (秒出)
  python3 scripts/build.py --timeout 8 --workers 32
"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, time
from urllib.error import URLError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "subscriptions")
DATA_DIR = os.path.join(ROOT, "scripts", "data")
SOURCES = os.path.join(ROOT, "scripts", "sources.json")

# ---------------------------------------------------------------- 频道定义
CHANNELS = {
    "CCTV1":   ("CCTV-1 综合",       "央视-综合"),
    "CCTV2":   ("CCTV-2 财经",       "央视-财经"),
    "CCTV3":   ("CCTV-3 综艺",       "央视-综艺"),
    "CCTV4":   ("CCTV-4 中文国际",   "央视-国际"),
    "CCTV5":   ("CCTV-5 体育",       "央视-体育"),
    "CCTV5+":  ("CCTV-5+ 体育赛事",  "央视-体育"),
    "CCTV6":   ("CCTV-6 电影",       "央视-电影"),
    "CCTV7":   ("CCTV-7 国防军事",   "央视-军事"),
    "CCTV8":   ("CCTV-8 电视剧",     "央视-电视剧"),
    "CCTV9":   ("CCTV-9 纪录",       "央视-纪录"),
    "CCTV10":  ("CCTV-10 科教",      "央视-科教"),
    "CCTV11":  ("CCTV-11 戏曲",      "央视-戏曲"),
    "CCTV12":  ("CCTV-12 社会与法",  "央视-社会与法"),
    "CCTV13":  ("CCTV-13 新闻",      "央视-新闻"),
    "CCTV14":  ("CCTV-14 少儿",      "央视-少儿"),
    "CCTV15":  ("CCTV-15 音乐",      "央视-音乐"),
    "CCTV16":  ("CCTV-16 奥林匹克",  "央视-体育"),
    "CCTV17":  ("CCTV-17 农业农村",  "央视-农业"),
    "CCTV4K":  ("CCTV-4K 超高清",    "央视-超高清"),
}

# ------------------------------------------------- 央视官方 CDN (最后兜底)
# 与 tv.cctv.com 网页播放器同源; 路径 /ldncctvwbcd/cdrmld{ch}_1/index.m3u8
# ⚠️ 注意: cdrmld = China DRM 加密流, 电脑/播放器通常只有声音、无画面。
#    因此这些源只作为「最后兜底」排在列表末尾, 不作为主线路。
OFFICIAL_CDNS = [
    ("txy", "ldncctvwbcdtxy.liveplay.myqcloud.com", "腾讯云"),
    ("cnc", "ldncctvwbcdcnc.v.wscdns.com",          "网宿"),
    ("ali", "ldncctvwbcdali.v.myalicdn.com",        "阿里云"),
    ("ks",  "ldncctvwbcdks.v.kcdnvip.com",          "金山云"),
    ("bd",  "ldncctvwbcdbd.a.bdydns.com",           "百度云"),
    ("hw",  "ldncctvwbcdhwy.cntv.myhwcdn.cn",       "华为云"),
]

def official_url(host, ch):
    """官方源主播放列表地址 (ch 为小写如 cctv1 / cctv5plus)"""
    return f"https://{host}/ldncctvwbcd/cdrmld{ch}_1/index.m3u8?b=200-2100"

def official_key(canon):
    """canonical -> 官方路径用的频道名"""
    return canon.lower().replace("+", "plus")

# ------------------------------------------------- 人工核验白名单
# 逐条抓帧目视确认过「台标/内容确实是对应频道」的源。
# 这些源优先于自动检测结果, 用于杜绝两类事故:
#   1) 名不符实 (上游把 CCTV-13 的流标成 CCTV1)
#   2) 无信号 (测试卡 / 广告 / 404 页面)
# 格式: 频道 -> [(url, 说明)]
VERIFIED = {
    # (url, 分辨率, 延迟ms, 归属地)
    # 注: 这批源为美国机房 IP, 走国际出口; 国内电信家宽可通但有延迟。
    "CCTV1": [
        ("http://38.75.136.137:98/gslb/dsdqbv/cctv1hd.m3u8?auth=test20251009", 1280, 720, 4513, "海外"),
        ("http://74.91.26.218:82/live/cctv1hd.m3u8", 1280, 720, 4290, "海外"),
        ("http://107.150.60.122/live/cctv1hd.m3u8", 1280, 720, 3707, "海外"),
        ("http://198.204.228.26/live/cctv1hd.m3u8", 1280, 720, 4962, "海外"),
        ("http://173.208.212.130:8181/720p/cctv1.m3u8", 1280, 720, 4303, "海外"),
    ],
    "CCTV13": [
        ("http://74.91.26.218:82/live/cctv13hd.m3u8", 1280, 720, 4289, "海外"),
        ("http://38.75.136.137:98/gslb/dsdqbv/cctv13hd.m3u8?auth=test20251009", 1280, 720, 4613, "海外"),
        ("http://107.150.60.122/live/cctv13hd.m3u8", 1280, 720, 3800, "海外"),
        ("http://63.141.230.178:82/gslb/zbdq5.m3u8?id=cctv13hd", 1280, 720, 3100, "海外"),
        ("http://go.bkpcp.top/mg/cctv13", 1280, 720, 2200, "海外"),
    ],
}

# 明确「名不符实」的黑名单 (实测台标与标注频道不符 / 无信号)
BLACKLIST = (
    "ali-m-l.cztv.com/channels/lantian/channel21",  # 实为 CCTV-13 中国蓝新闻, 被误标为 CCTV1
    "event.pull.hebtv.com/jishi/cp1",              # TVU networks 测试卡, 静止无信号
    "bztv.tvbus.cc",                               # 全部频道返回 404 HTML
    "ldncctvwbcd", "ldncctvwbnd",                  # 央视官方 DRM 加密: 只有声音无画面
)

# ---------------------------------------------------------------- 工具函数
def canon_of(name):
    """把各种频道写法归一到 canonical key, 失败返回 None"""
    if not name:
        return None
    n = name.upper()
    n = n.replace("CCTV-", "CCTV").replace("CCTV_", "CCTV").replace("CCTV ", "CCTV")
    n = n.replace("中央广播电视总台", "CCTV").replace("央视", "CCTV")
    n = re.sub(r"[（(].*?[)）]", "", n)
    n = re.sub(r"[\s\-_·]+", "", n)
    n = n.replace("PLUS", "+")
    m = re.search(r"CCTV(\d{1,2})\+", n)
    if m:
        return "CCTV%s+" % m.group(1)
    m = re.search(r"CCTV(\d{1,2})K", n)
    if m and m.group(1) == "4":
        return "CCTV4K"
    m = re.search(r"CCTV(\d{1,2})", n)
    if m:
        cid = "CCTV" + str(int(m.group(1)))
        if cid in CHANNELS:
            return cid
    return None

def is_ipv6(url):
    return "://[" in url

def fetch(url, timeout=40):
    if url.startswith("file://"):
        return open(os.path.join(ROOT, url[7:]), encoding="utf-8").read()
    try:
        p = subprocess.run(["curl", "-sL", "--max-time", str(timeout),
                            "-A", "Mozilla/5.0 (CCTV-IPTV-Builder)", url],
                           capture_output=True, text=True, timeout=timeout + 10)
        if p.returncode != 0 or not p.stdout:
            raise RuntimeError(p.stderr.strip() or "empty response")
        return p.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError("timeout")

def parse_m3u(text):
    """返回 [(name, url, attrs_str)]"""
    out, cur = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            cur = line
        elif line and not line.startswith("#") and cur is not None:
            url = line.split("$")[0].strip()
            if url.startswith("http"):
                out.append((cur.split(",")[-1], url, cur))
            cur = None
    return out

def probe_health(url, timeout, ua="Mozilla/5.0 (AppleTV; APTV)"):
    """真实解码检测: 实际解出一段画面, 统计解码错误率 + 帧间变化。
    DRM 加密流 / 死流 / 静止测试卡 都会在这里被识别出来。"""
    t0 = time.time()
    frames = 24
    try:
        p = subprocess.run(
            ["ffmpeg", "-v", "error", "-rw_timeout", str(timeout * 1000000),
             "-user_agent", ua, "-i", url,
             "-frames:v", str(frames), "-vf", "scale=64:36",
             "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True, timeout=timeout + 20)
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": (timeout + 20) * 1000, "timeout": True}
    except Exception as e:
        return {"ok": False, "ms": int((time.time() - t0) * 1000), "err": str(e)}

    ms = int((time.time() - t0) * 1000)
    errs = len(re.findall(
        rb"error while decoding|top block unavailable|non-existing SPS|Reference \d+ >=|corrupt",
        p.stderr))
    fsz = 64 * 36
    data = p.stdout
    nf = len(data) // fsz
    if nf < 4:
        return {"ok": False, "ms": ms, "why": f"frames={nf}"}
    prev, diffs = None, []
    for i in range(nf):
        f = data[i * fsz:(i + 1) * fsz]
        if prev is not None:
            diffs.append(sum(abs(a - b) for a, b in zip(f, prev)) / fsz)
        prev = f
    mean_diff = sum(diffs) / len(diffs) if diffs else 0
    err_rate = errs / nf
    ok = err_rate < 1.0 and mean_diff > 0.15
    return {"ok": ok, "ms": ms, "errs": errs, "frames": nf,
            "err_rate": round(err_rate, 2), "fdiff": round(mean_diff, 2),
            "why": "" if ok else ("drm/static" if mean_diff <= 0.15 else "decode-errors")}


def probe(url, timeout, ua="Mozilla/5.0 (AppleTV; APTV)"):
    """ffprobe 只读元数据: 分辨率 / 编码 / 响应耗时 (粗筛)"""
    t0 = time.time()
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-rw_timeout", str(timeout * 1000000),
             "-user_agent", ua,
             "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name",
             "-of", "default=noprint_wrappers=1", url],
            capture_output=True, text=True, timeout=timeout + 8)
        d = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
        ms = int((time.time() - t0) * 1000)
        if "width" in d:
            return {"ok": True, "w": int(d.get("width") or 0), "h": int(d.get("height") or 0),
                    "codec": d.get("codec_name", ""), "ms": ms}
        return {"ok": False, "ms": ms}
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": (timeout + 8) * 1000, "timeout": True}
    except Exception as e:
        return {"ok": False, "ms": int((time.time() - t0) * 1000), "err": str(e)}

# ---------------------------------------------------------------- 归属地识别
CN_DOMAIN_HINTS = (
    ".cn", "alicdn.com", "myalicdn.com", "cztv.com", "hebtv.com", "bkpcp.top",
    "cmvideo.cn", "chinamobile.com", "cctv.cn", "cctv.com", "cntv.cn", "cntv.com",
    "miguvideo.com", "gitv.tv", "kcdnvip.com", "ysp.cctv.cn", "wasu.cn",
    "smcloud.com", "bestv.com.cn", "voole.com", "chinaunicom", "189.cn",
    "myqcloud.com", "wscdns.com", "bdydns.com", "tcdnlive.com", "dcloudlive.com",
)

def host_of(url):
    return url.split("//", 1)[-1].split("/")[0]

def pre_geo(url):
    """无需联网即可判定的归属: cn / overseas / None"""
    h = host_of(url)
    if h.startswith("["):
        v6 = h.strip("[]")
        if v6[:4] in ("2409", "240e", "2408", "240e"):
            return "cn"
        return "overseas"
    hl = h.lower()
    for d in CN_DOMAIN_HINTS:
        if d in hl:
            return "cn"
    return None

def load_geo_cache():
    p = os.path.join(DATA_DIR, "geo_cache.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_geo_cache(c):
    json.dump(c, open(os.path.join(DATA_DIR, "geo_cache.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

def resolve_geo(urls, cache):
    hosts = sorted({host_of(u) for u in urls
                    if pre_geo(u) is None and host_of(u) not in cache})
    for i in range(0, len(hosts), 100):
        batch = hosts[i:i + 100]
        payload = json.dumps([{"query": x.split(":")[0]} for x in batch])
        try:
            p = subprocess.run(
                ["curl", "-s", "--max-time", "25", "-X", "POST",
                 "http://ip-api.com/batch?fields=query,countryCode",
                 "-H", "Content-Type: application/json", "-d", payload],
                capture_output=True, text=True, timeout=30)
            for r in json.loads(p.stdout):
                cache[r.get("query", "")] = "cn" if r.get("countryCode") == "CN" else "overseas"
        except Exception as e:
            print("   geo 查询失败:", e)
    for h in hosts:
        base = h.split(":")[0]
        if h not in cache and base in cache:
            cache[h] = cache[base]
    return cache

def geo_of(url, cache):
    g = pre_geo(url)
    if g:
        return g
    h = host_of(url)
    return cache.get(h) or cache.get(h.split(":")[0]) or "unknown"

def score(res, geo="unknown", official=False):
    """分辨率 + 速度 + 线路加成 (官方 DRM 源不加分, 仅兜底)"""
    h = res.get("h", 0)
    ms = max(res.get("ms", 9999), 1)
    res_score = (100 if h >= 1080 else 80 if h >= 720 else 55 if h >= 540
                 else 45 if h >= 480 else 30 if h >= 360 else 15)
    speed = max(0, 60 - ms / 200.0)
    geo_bonus = {"cn": 500, "unknown": 0, "overseas": -80}.get(geo, 0)
    return res_score + speed + geo_bonus

# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probe", action="store_true")
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    cfg = json.load(open(SOURCES, encoding="utf-8"))

    # ---- 1) 官方源 ----
    # 实测结论: 央视官方 CDN 的 cdrmld 路径是 China DRM 加密流, 只有声音无画面,
    # 因此这里不再探测, 也不把它们放进订阅 (避免用户看到「有声音没画面」)。
    print("== 央视官方 CDN: 已确认为 DRM 加密(仅声音), 跳过 ==")
    pool = {}          # canonical -> {url: meta}
    official_hits = {}  # canonical -> [meta]  真实可解码的官方源
    drm_fallback = {}   # canonical -> [meta]  DRM 加密的官方源 (仅兜底)
    off_tasks = []
    if False:
        with cf.ThreadPoolExecutor(16) as ex:
            for c, tag, host, name, u, r in ex.map(test_official, off_tasks):
                if r["ok"]:
                    # 真实可解码 -> 正常线路
                    official_hits.setdefault(c, []).append(
                        {"url": u, "src": f"央视官方CDN·{name}", "official": True,
                         "hint": "ipv4", "cdn": tag, **r,
                         "geo": "cn", "score": score(r, "cn")})
                elif r.get("why") in ("drm/static",):
                    # DRM 加密: 只有声音没画面 -> 仅作最后兜底
                    drm_fallback.setdefault(c, []).append(
                        {"url": u, "src": f"央视官方CDN·{name}(DRM)", "official": True,
                         "drm": True, "hint": "ipv4", "cdn": tag,
                         "ok": True, "w": r.get("w", 1280), "h": r.get("h", 720),
                         "ms": r.get("ms", 0), "geo": "cn", "score": 1})
        for c, lst in official_hits.items():
            print(f"   官方源[可解码]: {c:8s} {len(lst)} 条")
        for c, lst in drm_fallback.items():
            print(f"   官方源[DRM仅兜底]: {c:8s} {len(lst)} 条 (只有声音无画面, 排末尾)")
    else:
        # 不实测时, 官方源一律按 DRM 兜底处理 (不确认可解码就不作为主线路)
        for c in ("CCTV1", "CCTV13"):
            for tag, host, name in OFFICIAL_CDNS:
                drm_fallback.setdefault(c, []).append(
                    {"url": official_url(host, official_key(c)),
                     "src": f"央视官方CDN·{name}(DRM)", "official": True, "drm": True,
                     "hint": "ipv4", "cdn": tag, "ok": True, "w": 1280, "h": 720,
                     "ms": 0, "geo": "cn", "score": 1})

    # ---- 2) 上游社区源 ----
    print("== 拉取上游源 ==")
    for s in cfg["upstream"]:
        try:
            ent = parse_m3u(fetch(s["url"]))
            cnt = 0
            for nm, url, attrs in ent:
                c = canon_of(nm)
                if not c:
                    continue
                if any(b in url for b in BLACKLIST):
                    continue
                pool.setdefault(c, {})
                if url not in pool[c]:
                    pool[c][url] = {"attrs": attrs, "src": s["name"],
                                    "hint": s.get("hint", "mixed")}
                    cnt += 1
            print(f"  {s['name']:30s} -> {len(ent):5d} 条, 新增 CCTV {cnt}")
        except Exception as e:
            print(f"  !! {s['name']:28s} 拉取失败: {e}")

    # 官方源不进候选池, 直接使用首轮实测结果 (避免并发二次实测误伤)
    total = sum(len(v) for v in pool.values())
    print(f"== 合并后 {total} 条候选, 覆盖 {len(pool)} 个频道 ==")

    # ---- 3) 实测 + 打分 ----
    results = {}
    # 人工核验过的源: 直接置顶 (已确认频道内容正确, 免检测)
    for c, items in VERIFIED.items():
        results.setdefault(c, [])
        for url, w, h, ms, gname in items:
            geo = "cn" if gname == "国内" else "overseas"
            results[c].append({
                "url": url, "src": "人工核验", "verified": True,
                "hint": "ipv4", "ok": True, "w": w, "h": h, "ms": ms,
                "geo": geo, "score": 900,
            })
    print(f"== 载入人工核验源 {sum(len(v) for v in VERIFIED.values())} 条 ==")
    if args.no_probe:
        for c, urls in pool.items():
            results[c] = [{"url": u, **m, "ok": True, "w": 0, "h": 0, "ms": 0, "score": 0}
                          for u, m in urls.items()]
        for c, lst in official_hits.items():
            results.setdefault(c, [])
            for it in lst:
                if not any(x["url"] == it["url"] for x in results[c]):
                    results[c].insert(0, dict(it))
    else:
        # 先把官方源放入结果 (首轮已实测通过, 跳过二次探测)
        for c, lst in official_hits.items():
            results.setdefault(c, [])
            for it in lst:
                if not any(x["url"] == it["url"] for x in results[c]):
                    results[c].append(dict(it))

        tasks = [(c, u, m) for c, urls in pool.items() for u, m in urls.items()]
        geo = load_geo_cache()
        geo = resolve_geo([u for _, u, _ in tasks], geo)
        save_geo_cache(geo)
        print(f"== 实测 {len(tasks)} 条 (真实解码检测, 并发 {args.workers}, 超时 {args.timeout}s) ==")
        done = 0
        with cf.ThreadPoolExecutor(args.workers) as ex:
            fut = {ex.submit(probe_health, u, args.timeout): (c, u, m) for c, u, m in tasks}
            for f in cf.as_completed(fut):
                c, u, m = fut[f]
                r = f.result()
                done += 1
                if done % 60 == 0:
                    print(f"   进度 {done}/{len(tasks)}")
                if r.get("ok"):
                    # 解码通过 -> 再取分辨率
                    meta = probe(u, args.timeout)
                    if not meta.get("ok"):
                        continue
                    g = geo_of(u, geo)
                    results.setdefault(c, []).append(
                        {"url": u, **m, "w": meta["w"], "h": meta["h"],
                         "codec": meta.get("codec", ""), "ms": r["ms"],
                         "err_rate": r.get("err_rate"), "fdiff": r.get("fdiff"),
                         "geo": g, "score": score(meta, g)})
        # 本机无法直连的 IPv6 运营商源: 保留上游可信源, 标记为待验证
        keep = 0
        for c, u, m in tasks:
            if is_ipv6(u) and m.get("hint") == "ipv6":
                if not any(x["url"] == u for x in results.get(c, [])):
                    results.setdefault(c, []).append(
                        {"url": u, **m, "ok": True, "w": 0, "h": 0, "ms": 0,
                         "unverified": True, "geo": "cn", "score": 60})
                    keep += 1
        if keep:
            print(f"== 保留未经实测的 IPv6 源 {keep} 条 (本机不可达, 上游可信) ==")

        # 本机实测未通过、但归属国内的源: 用户网络(电信家宽)可能可通, 补为兜底
        # 这条策略对弱频道(CCTV5/5+/16/4K 等)尤其重要, 避免只剩海外源
        MINSRC = 4
        added = 0
        for c, urls in pool.items():
            have = {x["url"] for x in results.get(c, [])}
            if len(have) >= MINSRC:
                continue
            cands = []
            for u, m in urls.items():
                if u in have:
                    continue
                if pre_geo(u) != "cn":
                    continue
                cands.append((u, m))
            for u, m in cands[:MINSRC - len(have)]:
                results.setdefault(c, []).append(
                    {"url": u, **m, "ok": True, "w": 0, "h": 0, "ms": 0,
                     "unverified": True, "geo": "cn", "score": 55})
                added += 1
        if added:
            print(f"== 为弱频道补充国内兜底源 {added} 条 (本机未通过, 电信网络可试) ==")

        # DRM 官方源: 只有声音没画面, 仅作最后兜底 (排到列表末尾)
        for c, lst in drm_fallback.items():
            results.setdefault(c, [])
            for it in lst:
                if not any(x["url"] == it["url"] for x in results[c]):
                    results[c].append(dict(it))

        # 排序: 人工核验 > 可解码(国内优先) > 未验证兜底 > 海外 > DRM
        def rank(x):
            return (0 if x.get("verified") else 1,
                    1 if x.get("drm") else 0,
                    0 if x.get("geo") == "cn" else 1,
                    0 if not x.get("unverified") else 1,
                    -x.get("score", 0))
        for c in results:
            results[c].sort(key=rank)
        print(f"== 可用 {sum(len(v) for v in results.values())} 条 ==")

    # ---- 4) 生成订阅 ----
    def emit(path, label, filt):
        lines = ["#EXTM3U",
                 "# ===== CCTV 直播订阅 (自动生成, 请勿手动编辑) =====",
                 f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                 f"# 线路范围: {label}",
                 "# APTV 导入: 设置 -> 订阅 -> 添加订阅 -> 粘贴本文件 raw 地址",
                 ""]
        n = 0
        for c in CHANNELS:
            items = [it for it in results.get(c, [])
                     if filt(it) and not any(b in it["url"] for b in BLACKLIST)]
            if not items:
                continue
            disp, grp = CHANNELS[c]
            for i, it in enumerate(items[:6]):
                tag = "主" if i == 0 else f"备{i}"
                gtag = {"cn": "国内", "overseas": "海外", "unknown": "未知"}.get(it.get("geo"), "")
                if it.get("drm"):
                    extra = " [DRM加密·仅声音·兜底]"
                    tag = "兜底"
                elif it.get("unverified"):
                    extra = f" [IPv6·{gtag}]"
                elif it.get("h"):
                    extra = f" [{it['w']}x{it['h']}|{it['ms']}ms|{gtag}]"
                else:
                    extra = f" [{gtag}]"
                if it.get("verified"):
                    extra += " ✓已核验"
                elif it.get("official") and not it.get("drm"):
                    extra += " ★官方"
                lines.append(f'#EXTINF:-1 tvg-id="{c}" tvg-name="{disp}" tvg-logo="" '
                             f'group-title="{grp}",{disp} [{tag}]{extra}')
                lines.append(it["url"])
                n += 1
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        return n

    n4 = emit(os.path.join(OUT_DIR, "cctv-ipv4.m3u"), "仅 IPv4",
              lambda it: not is_ipv6(it["url"]))
    n6 = emit(os.path.join(OUT_DIR, "cctv-ipv6.m3u"), "仅 IPv6",
              lambda it: is_ipv6(it["url"]))
    nall = emit(os.path.join(OUT_DIR, "cctv.m3u"), "IPv4 + IPv6 整合",
                lambda it: True)

    json.dump({c: v[:12] for c, v in results.items()},
              open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n== 输出 ==")
    print(f"  subscriptions/cctv.m3u        {nall:3d} 条 (整合)")
    print(f"  subscriptions/cctv-ipv4.m3u   {n4:3d} 条 (IPv4)")
    print(f"  subscriptions/cctv-ipv6.m3u   {n6:3d} 条 (IPv6)")
    for c in CHANNELS:
        if results.get(c):
            print(f"  {c:8s} {len(results[c]):2d} 条")

if __name__ == "__main__":
    main()
