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
# ---------- One small page per restaurant: tablefifty.co.uk/r/<id>/ (shareable link with photo preview) ----------
import html as _h, json as _j, re as _re, shutil as _sh
_deals = _j.loads(_re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), _re.S).group(1))
CZIMG = {'korean': 'korean', 'indian': 'indian', 'steak': 'steak-house', 'pizza': 'pizza', 'chicken': 'chicken', 'caribbean': 'caribbean', 'ramen': 'ramen',
         'sushi': 'sushi', 'chinese': 'dumplings', 'thai': 'thai', 'italian': 'pasta', 'burger': 'burger', 'mezze': 'mezze', 'mexican': 'mexican',
         'british': 'british', 'fine': 'fine', 'tapas': 'tapas', 'vietnamese': 'vietnamese', 'kebab': 'kebab', 'cocktails': 'cocktails',
         'breakfast': 'breakfast', 'coffee': 'coffee', 'grocery': 'grocery', 'delivery': 'delivery'}
PLAT = {'firsttable': 'First Table', 'thefork': 'TheFork', 'eatclub': 'EatClub', 'code': 'Code', 'tastecard': 'tastecard', 'deliveroo': 'Deliveroo',
        'ubereats': 'Uber Eats', 'justeat': 'Just Eat', 'opentable': 'OpenTable'}
def head_en(o):
    h, n = o.get('h'), o.get('n', 0)
    return {'ft_d': '50% off food', 'ft_l': '50% off lunch', 'ft_b': '50% off breakfast', 'ft_bl': '50% off breakfast & lunch',
            'pct_food': f'{n}% off food', 'upto_food': f'Up to {n}% off food', 'pct_bill': f'{n}% off the bill', 'upto_bill': f'Up to {n}% off the bill',
            'pct_drinks': f'{n}% off drinks', 'two41': '2-for-1 or 25% off', 'nodeal': 'In the MICHELIN Guide'}.get(h) or o.get('x') or 'Deal'
def img_for(v):
    if v.get('imgl'): return BASE + v['imgl']
    if v.get('img'): return 'https://images.firsttable.net/1170x655/' + v['img']
    if v.get('imgx'): return v['imgx']
    return BASE + 'img/' + CZIMG.get(v.get('c'), 'restaurant') + '.jpg'
rdir = os.path.join(ROOT, 'r')
_sh.rmtree(rdir, ignore_errors=True)
rurls = []
for v in _deals:
    if v.get('k') != 'dine' or v.get('ct') == 'uk' and not v.get('pub'): continue
    o = max(v['o'], key=lambda x: x.get('n') or 0)
    plat = o.get('pn') or PLAT.get(o.get('p'), '')
    deal = head_en(o) + (f' with {plat}' if plat and o.get('h') != 'nodeal' else '')
    sc = f" TableFifty Score {v['sc'][0]}/10 from {v['sc'][1]:,} diner reviews." if v.get('sc') else ''
    mich = ''
    if v.get('mich'):
        st, bib, gr, sel = v['mich']
        mich = ' ' + ' · '.join(x for x in [f'{st} MICHELIN Star' + ('s' if st > 1 else '') if st else '', 'Bib Gourmand' if bib else '', 'Green Star' if gr else '', 'In the MICHELIN Guide' if sel and not (st or bib or gr) else ''] if x) + '.'
    title = f"{v['n']} – {deal} | TableFifty"
    desc = f"{deal} at {v['n']}, {v.get('a', '')}.{sc}{mich} See every deal and book on TableFifty."
    url = f"{BASE}r/{v['id']}/"
    ld = {'@context': 'https://schema.org', '@type': 'Restaurant', 'name': v['n'], 'url': url, 'image': img_for(v),
          'address': {'@type': 'PostalAddress', 'addressLocality': v.get('a', ''), 'addressCountry': 'GB'}}
    if v.get('ll'): ld['geo'] = {'@type': 'GeoCoordinates', 'latitude': v['ll'][0], 'longitude': v['ll'][1]}
    E = lambda x: _h.escape(str(x), quote=True)
    ld_json = _j.dumps(ld, ensure_ascii=False).replace('</', '<\\/')
    page = f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(url)}"><link rel="icon" href="{fav}">
<meta property="og:type" content="website"><meta property="og:site_name" content="TableFifty"><meta property="og:title" content="{E(v['n'] + ' · ' + deal)}">
<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(url)}"><meta property="og:image" content="{E(img_for(v))}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0f172a">
<script type="application/ld+json">{ld_json}</script>
<style>body{{margin:0;background:#0f172a;color:#e8eef8;font:16px/1.5 system-ui,sans-serif}}main{{max-width:640px;margin:0 auto;padding:40px 16px}}img{{width:100%;border-radius:16px}}a{{color:#10b981}}</style>
<script>location.replace("/?r={v['id']}" + location.hash);</script></head>
<body><main><img src="{E(img_for(v))}" alt="{E(v['n'])}"><h1>{E(v['n'])}</h1><p>{E(v.get('a', ''))}</p><p><strong>{E(deal)}</strong>{E(sc + mich)}</p>
<p><a href="/?r={E(v['id'])}">See this deal on TableFifty</a></p></main></body></html>
"""
    os.makedirs(os.path.join(rdir, v['id']), exist_ok=True)
    open(os.path.join(rdir, v['id'], 'index.html'), 'w', encoding='utf-8').write(page)
    rurls.append(url)
print('restaurant pages:', len(rurls))

open(os.path.join(ROOT,'robots.txt'),'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n')
open(os.path.join(ROOT,'sitemap.xml'),'w').write(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{BASE}</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}privacy.html</loc><lastmod>{TODAY}</lastmod></url>
''' + ''.join(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n' for u in rurls) + f'''</urlset>
''')
print('site built', len(index))
