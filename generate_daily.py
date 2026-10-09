#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI HOT 晨报生成器：拉取当日日报 -> 生成单文件 HTML 仪表盘。
输出 index.html（最新一期）与 archives/YYYY-MM-DD.html（每日归档）。
仅用 Python 标准库，无第三方依赖。
"""
import json
import re
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

API = "https://aihot.virxact.com/api/v1"
UA = "aihot-skill/1.2.1 (+https://aihot.virxact.com/aihot-skill/)"
BJT = timezone(timedelta(hours=8))
WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

SECTIONS = [
    ("模型发布/更新", "🧠", "var(--c-model)", "大模型与基础模型的发布与版本更新"),
    ("产品发布/更新", "🚀", "var(--c-product)", "产品、工具与平台层面的新发布与功能更新"),
    ("行业动态", "📰", "var(--c-industry)", "融资、营收、政策与行业格局变化"),
    ("论文研究", "📄", "var(--c-paper)", "论文、研究成果与前沿实验"),
    ("技巧与观点", "💡", "var(--c-tips)", "实践技巧、工程经验与行业观点"),
]

HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 晨报 · __DATE_CN__</title>
<style>
  :root{
    --bg:#f5f7fa; --card:#ffffff; --ink:#1a2233; --ink-2:#5b6478; --ink-3:#8a92a6;
    --line:#e6eaf1; --accent:#2f6bff; --accent-soft:#eaf0ff;
    --chip-bg:#f0f3f8; --radius:14px;
    --c-model:#7c5cff; --c-product:#0ea56d; --c-industry:#2f6bff; --c-paper:#d97706; --c-tips:#e0447c;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    background:var(--bg);color:var(--ink);line-height:1.6}
  a{color:inherit}
  .hero{background:linear-gradient(135deg,#eef3ff 0%,#f7f9ff 55%,#fdf3f7 100%);
    border-bottom:1px solid var(--line);padding:44px 20px 36px}
  .hero-inner{max-width:1080px;margin:0 auto}
  .hero .kicker{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;
    color:var(--accent);background:var(--accent-soft);border:1px solid #d8e2ff;
    padding:4px 14px;border-radius:999px;margin-bottom:16px}
  .hero h1{font-size:clamp(26px,4vw,38px);font-weight:800;letter-spacing:.5px}
  .hero .meta{margin-top:8px;color:var(--ink-2);font-size:14px}
  .hero .meta b{color:var(--ink)}
  .stats{display:flex;flex-wrap:wrap;gap:12px;margin-top:22px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:12px;
    padding:10px 18px;min-width:118px;box-shadow:0 1px 3px rgba(20,30,60,.05)}
  .stat .num{font-size:24px;font-weight:800;line-height:1.2}
  .stat .lab{font-size:12.5px;color:var(--ink-2);margin-top:2px}
  .stat.total .num{color:var(--accent)}
  .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;vertical-align:1px}
  .lead-card{margin-top:22px;background:var(--card);border:1px solid var(--line);
    border-left:4px solid var(--accent);border-radius:12px;padding:16px 20px;
    box-shadow:0 1px 4px rgba(20,30,60,.06)}
  .lead-card .tag{font-size:12px;font-weight:700;color:var(--accent);letter-spacing:2px}
  .lead-card h2{font-size:17px;margin:6px 0 4px}
  .lead-card p{font-size:14px;color:var(--ink-2)}
  nav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);
    backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
  .nav-inner{max-width:1080px;margin:0 auto;display:flex;gap:4px;overflow-x:auto;padding:10px 20px}
  .nav-inner a{flex:none;text-decoration:none;font-size:13.5px;font-weight:600;color:var(--ink-2);
    padding:6px 14px;border-radius:999px;border:1px solid transparent;white-space:nowrap;transition:all .15s}
  .nav-inner a:hover{color:var(--accent);background:var(--accent-soft)}
  .nav-inner a.active{color:var(--accent);background:var(--accent-soft);border-color:#d8e2ff}
  .nav-inner a .n{font-weight:800;margin-left:5px;font-size:12px;color:var(--ink-3)}
  main{max-width:1080px;margin:0 auto;padding:32px 20px 24px}
  section{margin-bottom:40px;scroll-margin-top:70px}
  .sec-head{display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
  .sec-head h2{font-size:20px;font-weight:800}
  .sec-head .rule{flex:1;height:1px;background:var(--line)}
  .sec-desc{font-size:13px;color:var(--ink-3);margin-bottom:16px}
  .sec-accent{border-left:4px solid var(--sc,var(--accent));padding-left:12px}
  .grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
    padding:18px 18px 14px;display:flex;flex-direction:column;gap:10px;
    box-shadow:0 1px 3px rgba(20,30,60,.04);transition:transform .15s,box-shadow .15s}
  .card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(20,30,60,.09)}
  .card .top{display:flex;align-items:flex-start;gap:10px}
  .idx{flex:none;width:30px;height:30px;border-radius:9px;display:flex;align-items:center;
    justify-content:center;font-size:13.5px;font-weight:800;color:#fff;background:var(--sc,var(--accent))}
  .card h3{font-size:15.5px;font-weight:700;line-height:1.45}
  .card h3 a{text-decoration:none}
  .card h3 a:hover{color:var(--accent)}
  .card .summary{font-size:13.5px;color:var(--ink-2);flex:1}
  .card .foot{display:flex;align-items:center;justify-content:space-between;gap:10px;
    border-top:1px dashed var(--line);padding-top:10px;margin-top:auto}
  .chip{font-size:12px;color:var(--ink-2);background:var(--chip-bg);border:1px solid var(--line);
    border-radius:999px;padding:2px 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60%}
  .card .more{font-size:13px;font-weight:600;color:var(--accent);text-decoration:none;white-space:nowrap}
  .card .more:hover{text-decoration:underline}
  .empty{background:var(--card);border:1px dashed #cdd5e3;border-radius:var(--radius);
    padding:26px;text-align:center;color:var(--ink-3);font-size:14px}
  footer{border-top:1px solid var(--line);background:var(--card);
    padding:22px 20px 30px;text-align:center;color:var(--ink-3);font-size:13px}
  footer a{color:var(--accent);text-decoration:none}
  footer a:hover{text-decoration:underline}
  @media (max-width:560px){
    .grid{grid-template-columns:1fr}
    .stat{min-width:calc(50% - 6px)}
    .hero{padding:32px 16px 28px}
  }
</style>
</head>
<body>
"""

HTML_TAIL = """<script>
  (function(){
    var links=document.querySelectorAll('#nav a');
    var map={};
    links.forEach(function(a){map[a.getAttribute('href').slice(1)]=a;});
    var io=new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(e.isIntersecting){
          links.forEach(function(a){a.classList.remove('active');});
          if(map[e.target.id])map[e.target.id].classList.add('active');
        }
      });
    },{rootMargin:'-30% 0px -60% 0px'});
    document.querySelectorAll('main section').forEach(function(s){io.observe(s);});
  })();
</script>
</body>
</html>
"""


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_daily():
    """返回 (report, note)。note 非空表示当日未生成、用了回退。"""
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    try:
        return http_get_json(f"{API}/dailies/{today}")["report"], ""
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    try:
        return http_get_json(f"{API}/dailies/latest")["report"], "当日日报尚未生成，以下为最近一期"
    except urllib.error.HTTPError:
        pass
    idx = http_get_json(f"{API}/dailies?limit=7")
    reports = idx.get("reports") or idx.get("items") or idx.get("data") or []
    if not reports:
        raise RuntimeError("日报索引为空，无法回退")
    date = reports[0].get("date") or reports[0].get("reportDate")
    return http_get_json(f"{API}/dailies/{date}")["report"], f"当日日报尚未生成，以下为最近一期（{date}）"


def bj_fmt(iso_str):
    """ISO 时间 -> 北京时间人话格式，如 10月9日 08:00"""
    if not iso_str:
        return ""
    s = iso_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(BJT)
    return f"{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}"


def trim60(text, n=60):
    """压缩到 n 字以内：优先在标点处截断。"""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[: n - 1]
    for p in "。！？；，、：,.;: ":
        pos = cut.rfind(p)
        if pos >= 30:
            cut = cut[:pos]
            break
    return cut.rstrip("。，、；：,.;: ") + "…"


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def chip_name(source_name):
    """source.name 取全角冒号前部分作为来源 chip"""
    return (source_name or "未知来源").split("：")[0].split(":")[0].strip()


def build_html(report, note):
    date = report["date"]
    dt = datetime.strptime(date, "%Y-%m-%d")
    date_cn = f"{dt.year}年{dt.month}月{dt.day}日 {WEEKDAYS[dt.weekday()]}"
    gen_cn = bj_fmt(report.get("generatedAt"))
    win_s, win_e = bj_fmt(report.get("windowStart")), bj_fmt(report.get("windowEnd"))

    # 按固定五版块归组
    by_label = {}
    for sec in report.get("sections", []):
        by_label.setdefault(sec["label"], []).extend(sec.get("items", []))

    grouped, total, gi = {}, 0, 0
    for label, _, _, _ in SECTIONS:
        items = []
        for it in by_label.get(label, []):
            gi += 1
            total += 1
            items.append({**it, "_idx": gi})
        grouped[label] = items

    # ---- Hero ----
    stats = [f'<div class="stat total"><div class="num">{total}</div><div class="lab">总条数</div></div>']
    for label, _, color, _ in SECTIONS:
        cnt = len(grouped[label])
        stats.append(
            f'<div class="stat"><div class="num" style="color:{color}">{cnt}</div>'
            f'<div class="lab"><span class="dot" style="background:{color}"></span>{label}</div></div>'
        )

    lead = report.get("lead") or {}
    lead_html = ""
    if lead.get("title"):
        lead_link = None
        for label, *_ in SECTIONS:
            for it in grouped[label]:
                if it["title"] == lead["title"] and it["links"].get("aihot"):
                    lead_link = it["links"]["aihot"]
                    break
        lead_title = esc(lead["title"])
        if lead_link:
            lead_title = f'<a href="{esc(lead_link)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none">{lead_title}</a>'
        lead_html = f"""<div class="lead-card"><span class="tag">今日头条</span>
<h2>{lead_title}</h2><p>{esc(trim60(lead.get("leadParagraph", ""), 90))}</p></div>"""

    note_html = f'<p style="margin-top:6px;color:#b45309;font-size:13px">⚠ {esc(note)}</p>' if note else ""

    # ---- Nav ----
    nav = "".join(
        f'<a href="#sec-{i}"><span class="dot" style="background:{color}"></span>{label}'
        f'<span class="n">{len(grouped[label])}</span></a>'
        for i, (label, _, color, _) in enumerate(SECTIONS)
    )

    # ---- Sections & cards ----
    body = ""
    for i, (label, emoji, color, desc) in enumerate(SECTIONS):
        cards = []
        for it in grouped[label]:
            link_title = it["links"].get("aihot") or it["links"].get("original") or "#"
            link_orig = it["links"].get("original") or it["links"].get("aihot") or "#"
            cards.append(f"""<article class="card">
<div class="top"><span class="idx">{it['_idx']}</span>
<h3><a href="{esc(link_title)}" target="_blank" rel="noopener noreferrer">{esc(it['title'])}</a></h3></div>
<p class="summary">{esc(trim60(it.get('summary', '')))}</p>
<div class="foot"><span class="chip">{esc(chip_name(it.get('source', {}).get('name')))}</span>
<a class="more" href="{esc(link_orig)}" target="_blank" rel="noopener noreferrer">阅读原文 →</a></div>
</article>""")
        grid = f'<div class="grid">{"".join(cards)}</div>' if cards else '<div class="empty">今日该版块暂无精选条目</div>'
        body += f"""<section id="sec-{i}" style="--sc:{color}">
<div class="sec-head sec-accent"><h2>{emoji} {label}</h2><div class="rule"></div></div>
<p class="sec-desc">{desc}</p>
{grid}
</section>"""

    daily_url = (report.get("attribution") or {}).get("url") or report.get("links", {}).get("aihot") or "https://aihot.news"

    return (HTML_HEAD.replace("__DATE_CN__", esc(date_cn)) + f"""<header class="hero">
<div class="hero-inner">
<span class="kicker">☀ AI HOT 晨报 · 每日精选</span>
<h1>AI 晨报 · {esc(date_cn)}</h1>
<p class="meta">共收录 <b>{total}</b> 条精选动态 · 统计窗口 {esc(win_s)} – {esc(win_e)}（北京时间）· 生成于 {esc(gen_cn)}</p>
{note_html}
<div class="stats">{''.join(stats)}</div>
{lead_html}
</div>
</header>
<nav><div class="nav-inner" id="nav">{nav}</div></nav>
<main>
{body}
</main>
<footer>
<p>本日报共收录 <b>{total}</b> 条 · 数据来源：<a href="{esc(daily_url)}" target="_blank" rel="noopener noreferrer">AI HOT 日报（{esc(date)}）</a> · <a href="archives/{esc(date)}.html">本期归档链接</a></p>
<p style="margin-top:4px">各条目版权归原作者所有 · 生成时间：{esc(gen_cn)}（北京时间）</p>
</footer>
""" + HTML_TAIL)


def main():
    report, note = fetch_daily()
    date = report["date"]
    html = build_html(report, note)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(f"archives/{date}.html", "w", encoding="utf-8") as f:
        f.write(html)
    counts = {s["label"]: len(s["items"]) for s in report.get("sections", [])}
    total = sum(counts.values())
    print(f"OK {date} 共{total}条 {counts} note={note or '无'}")


if __name__ == "__main__":
    sys.exit(main())
