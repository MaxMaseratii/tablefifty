"""Builds the TableFifty site into the repo root: index.html, privacy.html, robots.txt, sitemap.xml.
Run: python _build/build.py   (after refresh.py for fresh First Table data)"""
import datetime, os, runpy
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
ROOT = os.path.dirname(HERE)
runpy.run_path(os.path.join(SRC, 'build_data.py'), run_name='__main__')
s = open(os.path.join(SRC, 'page.html'), encoding='utf-8').read()
for tag, f in [('/*__I18N__*/', 'i18n.js'), ('/*__I18N_EXTRA__*/', 'i18n_extra.js'), ('/*__I18N_LOC__*/', 'i18n_loc.js'), ('/*__DEALS__*/', 'deals.js')]:
    assert tag in s, tag
    s = s.replace(tag, open(os.path.join(SRC, f), encoding='utf-8').read())
TODAY = datetime.date.today().isoformat()
BRAND='TableFifty'; DOMAIN='tablefifty.co.uk'; BASE=f'https://{DOMAIN}/'
about=open(os.path.join(SRC, 'about-content.html'),encoding='utf-8').read()
fav="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='32' fill='%23f59e0b'/%3E%3Ctext x='32' y='42' font-family='Arial,sans-serif' font-size='28' font-weight='800' text-anchor='middle' fill='%232b1a01'%3E50%3C/text%3E%3C/svg%3E"
desc=f"Every table. Half the bill. {BRAND} finds half-price restaurant, takeaway, surplus food and grocery deals near any UK postcode, from First Table, TheFork, Too Good To Go, Deliveroo, Uber Eats, Just Eat and the big chains."
title=f"{BRAND} | Half-price restaurant and takeaway deals near you, UK-wide"
head=f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{desc}">
<meta name="theme-color" content="#0f172a">
<link rel="canonical" href="{BASE}">
<link rel="icon" href="{fav}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{BASE}">
<meta property="og:image" content="{BASE}img/hero.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"{BRAND}","url":"{BASE}","description":"{desc}"}}</script>
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}[hidden]{{display:none!important}}</style>
'''
i=s.index('</style>')+len('</style>')
index=head+s[:i].replace(f'<title>{BRAND}</title>',f'<title>{title}</title>')+'\n</head>\n<body>\n'+s[i:]+'\n</body>\n</html>\n'
open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8').write(index)
privacy=f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Privacy policy | {BRAND}</title>
<meta name="description" content="How {BRAND} works, how it makes money, and what it does with your data.">
<link rel="canonical" href="{BASE}privacy.html">
<link rel="icon" href="{fav}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Figtree:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root{{color-scheme:dark;--bg:#0f172a;--text:#e8eef8;--muted:#9dadc4;--faint:#6f809b;--accent:#10b981;--amber:#f59e0b;--amber-ink:#2b1a01;
    --f-display:"Bricolage Grotesque","Avenir Next","Segoe UI",system-ui,sans-serif;--f-body:"Figtree","Segoe UI",system-ui,-apple-system,sans-serif;
    padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
  *{{box-sizing:border-box}}
  html,body{{background:var(--bg);color:var(--text)}}
  body{{margin:0;font-family:var(--f-body);font-size:16px;line-height:1.6}}
  .wrap{{max-width:720px;margin:0 auto;padding:32px 16px 64px}}
  a{{color:var(--accent)}}
  .top{{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--text);margin-bottom:28px}}
  .mark{{width:34px;height:34px;border-radius:50%;background:var(--amber);color:var(--amber-ink);display:grid;place-items:center;font-family:var(--f-display);font-weight:800;font-size:15px;letter-spacing:-.02em}}
  .top b{{font-family:var(--f-display);font-weight:800;font-size:20px}} .top b span{{color:var(--accent)}}
  h1{{font-family:var(--f-display);font-weight:800;font-size:clamp(30px,5vw,40px);line-height:1.1;margin:0 0 8px}}
  .about{{display:grid;gap:12px;color:var(--muted)}}
  .about h3{{margin:14px 0 0;font-family:var(--f-display);font-size:20px;color:var(--text)}}
  .about p,.about ul{{margin:0}} .about ul{{padding-left:22px;display:grid;gap:6px}} .about strong{{color:var(--text)}}
  .adtag{{font-size:11px;font-weight:800;letter-spacing:.06em;padding:1px 6px;border-radius:5px;background:var(--amber);color:var(--amber-ink)}}
</style>
</head>
<body>
  <main class="wrap">
    <a class="top" href="index.html"><span class="mark" aria-hidden="true">50</span><b>Table<span>Fifty</span></b></a>
    <h1>About &amp; privacy</h1>
    <div class="about">
{about}    </div>
    <p style="margin-top:32px"><a href="index.html">← Back to the deals</a></p>
  </main>
</body>
</html>
'''
open(os.path.join(ROOT,'privacy.html'),'w',encoding='utf-8').write(privacy)
open(os.path.join(ROOT,'robots.txt'),'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n')
open(os.path.join(ROOT,'sitemap.xml'),'w').write(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{BASE}</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}privacy.html</loc><lastmod>{TODAY}</lastmod></url>
</urlset>
''')
print('site built', len(index))
