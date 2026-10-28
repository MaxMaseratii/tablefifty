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
# Browser safety settings for every page (GitHub Pages can't send headers, so they go in <meta> tags):
# no plugins, no <base> hijack, forms may only post to us or FormSubmit, always HTTPS, and other sites only see our domain.
SEC_META = ('<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="object-src \'none\'; base-uri \'self\'; '
            'form-action \'self\' https://formsubmit.co; upgrade-insecure-requests">\n<meta name="referrer" content="strict-origin-when-cross-origin">')
def secure(h): return h.replace('<meta charset="utf-8">', SEC_META, 1)
BRAND='TableFifty'; DOMAIN='tablefifty.co.uk'; BASE=f'https://{DOMAIN}/'
CONTACT = 'info@tablefifty.co.uk'
# Spotlight payment links from Stripe. Empty = the "For restaurants" page shows an email button instead.
STRIPE_TRIAL = 'https://buy.stripe.com/5kQ5kFd6k5hjdUh17X9Ve00'      # "Spotlight trial - 1 month", £19, one-off
STRIPE_MONTHLY = 'https://buy.stripe.com/9B63cx1nCbFH8zXeYN9Ve01'    # "Spotlight - monthly", £49, repeats monthly
# Google Search Console "HTML tag" code (only the content="..." part). Empty = no tag.
GSC_TOKEN = ''
about=open(os.path.join(SRC, 'about-content.html'),encoding='utf-8').read().replace('hello@tablefifty.co.uk', CONTACT)
fav="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='32' fill='%23f59e0b'/%3E%3Ctext x='32' y='42' font-family='Arial,sans-serif' font-size='28' font-weight='800' text-anchor='middle' fill='%232b1a01'%3E50%3C/text%3E%3C/svg%3E"
desc=f"Every table. Half the bill. {BRAND} finds half-price restaurant, takeaway, surplus food and grocery deals near any UK postcode, from First Table, TheFork, Too Good To Go, Deliveroo, Uber Eats, Just Eat and the big chains."
title=f"{BRAND} | Half-price restaurant and takeaway deals near you, UK-wide"
gsc_meta = f'\n<meta name="google-site-verification" content="{GSC_TOKEN}">' if GSC_TOKEN else ''
head=f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{desc}">
<meta name="theme-color" content="#0f172a">
<link rel="canonical" href="{BASE}">
<link rel="icon" href="{fav}">{gsc_meta}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{BASE}">
<meta property="og:image" content="{BASE}img/hero.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"{BRAND}","url":"{BASE}","description":"{desc}"}}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization","name":"{BRAND}","url":"{BASE}","logo":"{BASE}img/hero.jpg","sameAs":["https://www.instagram.com/tablefifty50/","https://www.facebook.com/tablefifty50"]}}</script>
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}[hidden]{{display:none!important}}</style>
'''
i=s.index('</style>')+len('</style>')
index=head+s[:i].replace(f'<title>{BRAND}</title>',f'<title>{title}</title>')+'\n</head>\n<body>\n'+s[i:]+'\n</body>\n</html>\n'
open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8').write(secure(index))
PAGE_CSS=f'''<style>
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
  .story{{border:1px solid #27365a;border-radius:16px;padding:16px 18px;background:linear-gradient(160deg,rgba(245,158,11,.10),rgba(16,185,129,.06));display:grid;gap:10px}}
  .story h3{{margin:0}} .story p{{color:var(--text)}} .story .sig{{color:var(--amber);font-weight:700}}
  .adtag{{font-size:11px;font-weight:800;letter-spacing:.06em;padding:1px 6px;border-radius:5px;background:var(--amber);color:var(--amber-ink)}}
</style>'''
privacy=f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Privacy policy | {BRAND}</title>
<meta name="description" content="How {BRAND} works, how it makes money, and what it does with your data.">
<link rel="canonical" href="{BASE}privacy.html">
<link rel="icon" href="{fav}">
<link href="/fonts/main.css" rel="stylesheet">
{PAGE_CSS}
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
open(os.path.join(ROOT,'privacy.html'),'w',encoding='utf-8').write(secure(privacy))
terms_body = open(os.path.join(SRC, 'terms-content.html'), encoding='utf-8').read().replace('hello@tablefifty.co.uk', CONTACT)
terms = (privacy.replace('<title>Privacy policy | ', '<title>Terms of use | ').replace(f'href="{BASE}privacy.html"', f'href="{BASE}terms.html"')
         .replace(f'content="How {BRAND} works, how it makes money, and what it does with your data."', f'content="The rules for using {BRAND}."')
         .replace('<h1>About &amp; privacy</h1>', '<h1>Terms of use</h1>').replace(about, terms_body))
assert terms_body in terms
open(os.path.join(ROOT,'terms.html'),'w',encoding='utf-8').write(secure(terms))
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
            'pct_drinks': f'{n}% off drinks', 'two41': '2-for-1 or 25% off', 'nodeal': 'In the MICHELIN Guide', 'classic': 'A British classic'}.get(h) or o.get('x') or 'Deal'
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
    deal = head_en(o) + (f' with {plat}' if plat and o.get('h') not in ('nodeal', 'classic') else '')
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
<script>var h="";try{{h=new URL(document.referrer).hostname}}catch(e){{}}location.replace("/?r={v['id']}"+(location.search?"&"+location.search.slice(1):"")+(h&&h!==location.hostname?"&rf="+encodeURIComponent(h):"")+location.hash);</script></head>
<body><main><img src="{E(img_for(v))}" alt="{E(v['n'])}"><h1>{E(v['n'])}</h1><p>{E(v.get('a', ''))}</p><p><strong>{E(deal)}</strong>{E(sc + mich)}</p>
<p><a href="/?r={E(v['id'])}">See this deal on TableFifty</a></p></main></body></html>
"""
    os.makedirs(os.path.join(rdir, v['id']), exist_ok=True)
    open(os.path.join(rdir, v['id'], 'index.html'), 'w', encoding='utf-8').write(page)
    rurls.append(url)
print('restaurant pages:', len(rurls))

# ---------- "For restaurants" page: tablefifty.co.uk/restaurants/ ----------
# A short enquiry form only. Prices and payment links (STRIPE_TRIAL / STRIPE_MONTHLY) are sent by email
# to restaurants that ask, never shown publicly. Form posts go to CONTACT through FormSubmit (formsubmit.co).
n_offers = sum(len(v.get('o', [])) for v in _deals)
n_places = sum(1 for v in _deals if v.get('k') == 'dine' and not v.get('nodeal'))
rest_css = PAGE_CSS.replace('</style>', """  form{display:grid;gap:14px;margin-top:6px}
  label{display:grid;gap:6px;font-weight:600;color:var(--text);font-size:15px}
  label small{font-weight:400;color:var(--faint)}
  input,select,textarea{font:inherit;font-size:16px;color:var(--text);background:#131d33;border:1px solid #34466b;border-radius:12px;padding:12px 14px;width:100%}
  textarea{min-height:110px;resize:vertical}
  input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
  fieldset{border:1px solid #34466b;border-radius:12px;padding:12px 14px;display:grid;gap:8px;margin:0}
  legend{font-weight:600;color:var(--text);padding:0 6px}
  .chk{display:flex;gap:10px;align-items:flex-start;font-weight:500;color:var(--muted)}
  .chk input{width:18px;height:18px;margin-top:3px;flex:none}
  .row2{display:grid;gap:14px} @media (min-width:640px){.row2{grid-template-columns:1fr 1fr}}
  .btn{justify-self:start;background:var(--amber);color:var(--amber-ink);font:inherit;font-weight:800;border:0;padding:13px 20px;border-radius:12px;cursor:pointer}
  .btn[disabled]{opacity:.6;cursor:wait}
  .msg{margin:0;font-weight:600} .msg.ok{color:var(--accent)} .msg.warn{color:var(--amber)}
  .hp{position:absolute;left:-5000px}
  .small{font-size:14px;color:var(--faint);margin:0}
  .stats{display:flex;flex-wrap:wrap;gap:10px 22px;color:var(--text);font-weight:700}
</style>""")
restaurants = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>For restaurants | {BRAND}</title>
<meta name="description" content="Restaurant owner or manager? Contact {BRAND} to reach more UK diners, join a deals platform, or update your listing.">
<link rel="canonical" href="{BASE}restaurants/">
<link rel="icon" href="{fav}">
<meta property="og:title" content="{BRAND} for restaurants"><meta property="og:url" content="{BASE}restaurants/"><meta property="og:image" content="{BASE}img/hero.jpg">
<link href="/fonts/main.css" rel="stylesheet">
{rest_css}
</head>
<body>
  <main class="wrap">
    <a class="top" href="/"><span class="mark" aria-hidden="true">50</span><b>Table<span>Fifty</span></b></a>
    <h1>For restaurants</h1>
    <div class="about">
      <p>{BRAND} shows UK diners the best restaurant, pub and takeaway deals near them, checked every morning.</p>
      <div class="stats"><span>{n_offers:,} live offers</span><span>{n_places:,} restaurants and pubs</span><span>9 languages</span></div>
      <p>Restaurant owner or manager? Tell us what you need. We reply within 1 working day with the details.</p>

      <form id="enq" novalidate>
        <div class="row2">
          <label>Restaurant name<input name="restaurant" required maxlength="100" autocomplete="organization"></label>
          <label>Town or city<input name="town" required maxlength="60" autocomplete="address-level2"></label>
        </div>
        <div class="row2">
          <label>Your name<input name="name" required maxlength="80" autocomplete="name"></label>
          <label>Your role<select name="role"><option>Owner</option><option>Manager</option><option>Marketing</option><option>Other</option></select></label>
        </div>
        <div class="row2">
          <label>Email<input name="email" type="email" required maxlength="120" autocomplete="email"></label>
          <label>Phone <small>(optional)</small><input name="phone" type="tel" maxlength="30" autocomplete="tel"></label>
        </div>
        <fieldset>
          <legend>I'm interested in</legend>
          <label class="chk"><input type="checkbox" name="interest" value="More diners from TableFifty">More diners from {BRAND}</label>
          <label class="chk"><input type="checkbox" name="interest" value="Joining a deals platform (First Table)">Filling quiet tables with a deals platform</label>
          <label class="chk"><input type="checkbox" name="interest" value="Update or remove our listing">Updating or removing our listing</label>
          <label class="chk"><input type="checkbox" name="interest" value="Something else">Something else</label>
        </fieldset>
        <label>Message <small>(optional)</small><textarea name="message" maxlength="2000"></textarea></label>
        <input class="hp" type="text" name="_honey" tabindex="-1" autocomplete="off" aria-hidden="true">
        <label class="chk"><input type="checkbox" name="consent" required>I agree that {BRAND} can contact me about this request.</label>
        <label class="chk"><input type="checkbox" name="share_first_table">If we're interested in a deals platform, you may share my name, email and phone with First Table.</label>
        <button class="btn" type="submit" id="send">Send</button>
        <p class="msg" id="msg" aria-live="polite"></p>
      </form>

      <p class="small">{BRAND} is independent and is not linked to, or approved by, the platforms it lists. Your message is sent to {CONTACT} and used only to answer you. <a href="/privacy.html">About &amp; privacy</a>.</p>
    </div>
    <p style="margin-top:32px"><a href="/">← Back to the deals</a></p>
    <p class="small">TableFifty · Pavilion, 64 Knightsbridge, London SW1X 7JF · {CONTACT}</p>
  </main>
<script>
(function () {{
  var f = document.getElementById("enq"), msg = document.getElementById("msg"), btn = document.getElementById("send");
  function say(t, c) {{ msg.textContent = t; msg.className = "msg " + (c || ""); }}
  f.addEventListener("submit", function (e) {{
    e.preventDefault();
    var d = new FormData(f);
    if (d.get("_honey")) return;
    var email = String(d.get("email") || "").trim();
    if (!String(d.get("restaurant") || "").trim() || !String(d.get("town") || "").trim() || !String(d.get("name") || "").trim()) {{ say("Please fill in the restaurant, town and your name.", "warn"); return; }}
    if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{{2,}}$/.test(email)) {{ say("Please enter a valid email address.", "warn"); return; }}
    if (!d.get("consent")) {{ say("Please tick the box so we can reply to you.", "warn"); return; }}
    var body = {{
      _subject: "TableFifty restaurant enquiry: " + d.get("restaurant") + " (" + d.get("town") + ")",
      _template: "table", _captcha: "false",
      restaurant: d.get("restaurant"), town: d.get("town"), name: d.get("name"), role: d.get("role"),
      email: email, phone: d.get("phone") || "", interest: d.getAll("interest").join(", ") || "Not ticked",
      message: d.get("message") || "", share_with_first_table: d.get("share_first_table") ? "Yes" : "No",
      _replyto: email
    }};
    btn.disabled = true; say("Sending...");
    fetch("https://formsubmit.co/ajax/{CONTACT}", {{ method: "POST", headers: {{ "Content-Type": "application/json", "Accept": "application/json" }}, body: JSON.stringify(body) }})
      .then(function (r) {{ return r.json().catch(function () {{ return {{}}; }}).then(function (j) {{ return {{ ok: r.ok, j: j }}; }}); }})
      .then(function (x) {{
        if (x.ok && String(x.j.success) === "true") {{ f.reset(); say("Thank you! We have your message and will reply within 1 working day.", "ok"); }}
        else {{ say("Sorry, that didn't send. Please email us at {CONTACT}.", "warn"); }}
      }})
      .catch(function () {{ say("Sorry, that didn't send. Please email us at {CONTACT}.", "warn"); }})
      .then(function () {{ btn.disabled = false; }});
  }});
}})();
</script>
</body>
</html>
"""
os.makedirs(os.path.join(ROOT, 'restaurants'), exist_ok=True)
open(os.path.join(ROOT, 'restaurants', 'index.html'), 'w', encoding='utf-8').write(secure(restaurants))

# ---------- Private stats page: tablefifty.co.uk/stats/ (not linked, not indexed) ----------
# Reads the anonymous totals in Firestore "clicks/{YYYY-MM}" (visits per day/source, deal clicks per platform/day/source).
_stats = open(os.path.join(SRC, 'stats.html'), encoding='utf-8').read()
_cfg = _re.search(r'apiKey: "([^"]+)"[\s\S]*?projectId: "([^"]+)"', open(os.path.join(SRC, 'page.html'), encoding='utf-8').read())
_stats = (_stats.replace('__CSS__', PAGE_CSS).replace('__FAV__', fav).replace('__APIKEY__', _cfg.group(1)).replace('__PROJECT__', _cfg.group(2))
          .replace('__PLAT__', _j.dumps(dict(PLAT, tastecard='tastecard', code='Code'), ensure_ascii=False)))
os.makedirs(os.path.join(ROOT, 'stats'), exist_ok=True)
open(os.path.join(ROOT, 'stats', 'index.html'), 'w', encoding='utf-8').write(secure(_stats))
# ---------- Guide pages: tablefifty.co.uk/michelin/ and tablefifty.co.uk/british-classics/ (shareable, found on Google) ----------
GUIDE_CSS = PAGE_CSS.replace('</style>', """  .wrap{max-width:860px}
  .lead{color:var(--muted);font-size:17px;margin:0 0 8px}
  h2{font-family:var(--f-display);font-size:22px;margin:30px 0 10px}
  .list{display:grid;gap:10px;padding:0;margin:0;list-style:none}
  .item{background:#131d33;border:1px solid #27365a;border-radius:14px;padding:14px 16px;display:grid;gap:6px}
  .item h3{margin:0;font-family:var(--f-display);font-size:18px} .item h3 a{color:var(--text);text-decoration:none} .item h3 a:hover{text-decoration:underline}
  .item p{margin:0;color:var(--muted)} .item .where{font-size:14px;color:var(--faint)}
  .chips{display:flex;flex-wrap:wrap;gap:6px}
  .chip{font-size:12px;font-weight:800;border-radius:999px;padding:3px 10px;background:#22304f;color:var(--text)}
  .chip.mich{background:#b0102c;color:#fff} .chip.cl{background:#1d4d36;color:#f5ecd2} .chip.deal{background:var(--amber);color:var(--amber-ink)}
  .item .links{display:flex;flex-wrap:wrap;gap:14px;font-size:14px;font-weight:600}
  .toc{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0} .toc a{font-size:14px;font-weight:700;padding:6px 12px;border:1px solid #34466b;border-radius:999px;text-decoration:none}
  .small{font-size:13px;color:var(--faint)}
</style>""")
def _esc(x): return _h.escape(str(x), quote=True)
def guide_page(slug_, title, desc, h1, body):
    return secure(f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(desc)}">
<link rel="canonical" href="{BASE}{slug_}/">
<link rel="icon" href="{fav}">
<meta property="og:title" content="{_esc(title)}"><meta property="og:description" content="{_esc(desc)}"><meta property="og:url" content="{BASE}{slug_}/"><meta property="og:image" content="{BASE}img/hero.jpg">
<link href="/fonts/main.css" rel="stylesheet">
{GUIDE_CSS}
</head>
<body>
  <main class="wrap">
    <a class="top" href="/"><span class="mark" aria-hidden="true">50</span><b>Table<span>Fifty</span></b></a>
    <h1>{h1}</h1>
{body}
    <p style="margin-top:32px"><a href="/">← All deals on TableFifty</a></p>
    <p class="small">TableFifty · Pavilion, 64 Knightsbridge, London SW1X 7JF · {CONTACT}</p>
  </main>
</body>
</html>
""")
def _town(v): return (v.get('a') or '').split(',')[0].strip() or (v.get('ct') or '').title()
def _deal_of(v):
    real = [o for o in v['o'] if o.get('h') not in ('nodeal', 'classic')]
    if not real: return ''
    o = max(real, key=lambda x: x.get('n') or 0)
    plat = o.get('pn') or PLAT.get(o.get('p'), '')
    return head_en(o) + (f' with {plat}' if plat else '')
def _mich_label(v):
    st, bib, gr, sel = (v['mich'] + [0, 0, 0, 0])[:4]
    out = []
    if st: out.append(f"{'✦' * st} {st} MICHELIN Star{'s' if st > 1 else ''}")
    if bib: out.append('Bib Gourmand')
    if gr: out.append('Green Star')
    if not out and sel: out.append('In the MICHELIN Guide')
    return out
def _item(v, chips, text=''):
    deal = _deal_of(v)
    links = [f'<a href="/r/{_esc(v["id"])}/">See on TableFifty</a>']
    if v.get('web'): links.append(f'<a href="{_esc(v["web"])}" rel="noopener" target="_blank">Website</a>')
    links.append(f'<a href="https://www.google.com/maps/search/?api=1&query={_esc(urllib.parse.quote_plus(v["n"] + " " + (v.get("a") or "")))}" rel="noopener" target="_blank">Map</a>')
    ch = ''.join(f'<span class="chip {c}">{_esc(t)}</span>' for c, t in chips) + (f'<span class="chip deal">{_esc(deal)}</span>' if deal else '')
    return f"""      <li class="item"><h3><a href="/r/{_esc(v['id'])}/">{_esc(v['n'])}</a></h3><p class="where">{_esc(v.get('a') or '')}</p>
        <div class="chips">{ch}</div>{f'<p>{_esc(text)}</p>' if text else ''}<div class="links">{' · '.join(links)}</div></li>"""
import urllib.parse
_mv = [v for v in _deals if v.get('mich') and v.get('k') == 'dine']
_mv.sort(key=lambda v: (-(v['mich'][0]), -(v['mich'][1]), _town(v), v['n']))
_with = [v for v in _mv if _deal_of(v)]
groups = [('three', 'Three MICHELIN Stars', lambda v: v['mich'][0] == 3), ('two', 'Two MICHELIN Stars', lambda v: v['mich'][0] == 2),
          ('one', 'One MICHELIN Star', lambda v: v['mich'][0] == 1), ('bib', 'Bib Gourmand: good food at a fair price', lambda v: not v['mich'][0] and v['mich'][1]),
          ('guide', 'Also in the Guide', lambda v: not v['mich'][0] and not v['mich'][1])]
body = [f"""    <p class="lead">{len(_mv)} restaurants from the MICHELIN Guide Great Britain &amp; Ireland 2026, and the ones you can book with a discount today. We check First Table, EatClub and TheFork every morning.</p>
    <div class="toc">{'<a href="#deals">With a deal today</a>' if _with else ''}{''.join(f'<a href="#{k}">{_esc(t.split(":")[0])}</a>' for k, t, f in groups if any(f(v) for v in _mv))}</div>"""]
if _with:
    body.append(f'    <h2 id="deals">MICHELIN with a deal today ({len(_with)})</h2>\n    <ul class="list">\n' + '\n'.join(_item(v, [('mich', x) for x in _mich_label(v)], v.get('ds') if not str(v.get('ds', '')).startswith(('One-MICHELIN', 'Two-MICHELIN', 'Three-MICHELIN', 'Bib Gourmand restaurant', 'Restaurant listed in')) else '') for v in _with) + '\n    </ul>')
for k, t, f in groups:
    vs = [v for v in _mv if f(v) and v not in _with]
    if not vs: continue
    body.append(f'    <h2 id="{k}">{_esc(t)} ({len(vs)})</h2>\n    <ul class="list">\n' + '\n'.join(_item(v, [('mich', x) for x in _mich_label(v)]) for v in vs) + '\n    </ul>')
body.append('    <p class="small" style="margin-top:24px">Stars, Bib Gourmands and Green Stars come from the MICHELIN Guide Great Britain &amp; Ireland 2026. MICHELIN is a trademark of Michelin; TableFifty is not linked to the Guide.</p>')
os.makedirs(os.path.join(ROOT, 'michelin'), exist_ok=True)
open(os.path.join(ROOT, 'michelin', 'index.html'), 'w', encoding='utf-8').write(guide_page('michelin', 'MICHELIN restaurants in the UK, with today\'s deals | TableFifty',
    f'All {len(_mv)} MICHELIN-starred and Bib Gourmand restaurants we track in the UK, with the ones you can book at a discount today first.',
    'MICHELIN restaurants, for less', '\n'.join(body)))
CL_TYPES = [('hist', 'Historic dining rooms'), ('pie', 'Pie and mash'), ('fish', 'Fish and chips'), ('tea', 'Tea rooms'), ('caff', 'Classic caffs'),
            ('pub', 'Historic pubs'), ('bakery', 'Bakeries')]
CL_LABEL = {'hist': 'Historic dining room', 'pie': 'Pie and mash', 'fish': 'Fish and chips', 'tea': 'Tea room', 'caff': 'Classic caff', 'pub': 'Historic pub', 'bakery': 'Bakery'}
_cv = [v for v in _deals if v.get('cl')]
if _cv:
    _cv.sort(key=lambda v: (v.get('fd') or 3000, v['n']))
    body = [f"""    <p class="lead">{len(_cv)} much-loved places for proper British food: pie and mash, fish and chips, cream teas, full English breakfasts and roast dinners. Most aren't on any deal app. We list them because they're worth a visit at full price.</p>
    <div class="toc">{''.join(f'<a href="#{k}">{_esc(t)}</a>' for k, t in CL_TYPES if any(v['cl'] == k for v in _cv))}</div>"""]
    for k, t in CL_TYPES:
        vs = [v for v in _cv if v['cl'] == k]
        if not vs: continue
        def _txt(v):
            sig = v.get('sig') or []
            return (v.get('ds') or '') + (f" Known for: {', '.join(sig)}." if sig else '')
        body.append(f'    <h2 id="{k}">{_esc(t)} ({len(vs)})</h2>\n    <ul class="list">\n' + '\n'.join(
            _item(v, [('cl', CL_LABEL[k] + (f" · since {v['fd']}" if v.get('fd') else ''))], _txt(v)) for v in vs) + '\n    </ul>')
    body.append('    <p class="small" style="margin-top:24px">Opening times and prices change. Check the place\'s own website before you go. Know a classic we should add? Email ' + CONTACT + '.</p>')
    os.makedirs(os.path.join(ROOT, 'british-classics'), exist_ok=True)
    open(os.path.join(ROOT, 'british-classics', 'index.html'), 'w', encoding='utf-8').write(guide_page('british-classics', 'Traditional British food: classic places to eat | TableFifty',
        f'{len(_cv)} classic British places to eat: pie and mash, fish and chips, tea rooms, caffs and historic dining rooms, and what makes each one special.',
        'British classics', '\n'.join(body)))
print('guide pages: michelin', len(_mv), '| british classics', len(_cv))

# ---------- Owner-only admin page: tablefifty.co.uk/admin/ (newsletter + member lists; Firestore rules allow only the owner) ----------
_pg = open(os.path.join(SRC, 'page.html'), encoding='utf-8').read()
_fbcfg = _re.search(r'firebase: (\{[^}]*\})', _pg).group(1)
_fbcfg = _j.dumps(dict(_re.findall(r'(\w+): "([^"]*)"', _fbcfg)))
_fbver = _re.search(r'const FB_VER = "([^"]+)"', _pg).group(1)
_admin = (open(os.path.join(SRC, 'admin.html'), encoding='utf-8').read().replace('__CSS__', PAGE_CSS).replace('__FAV__', fav)
          .replace('__FBCFG__', _fbcfg).replace('__FBVER__', _fbver))
os.makedirs(os.path.join(ROOT, 'admin'), exist_ok=True)
open(os.path.join(ROOT, 'admin', 'index.html'), 'w', encoding='utf-8').write(secure(_admin))
open(os.path.join(ROOT,'robots.txt'),'w').write(f'User-agent: *\nAllow: /\nDisallow: /stats/\nDisallow: /admin/\n\nSitemap: {BASE}sitemap.xml\n')
open(os.path.join(ROOT,'sitemap.xml'),'w').write(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{BASE}</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}privacy.html</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}terms.html</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}michelin/</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}british-classics/</loc><lastmod>{TODAY}</lastmod></url>
  <url><loc>{BASE}restaurants/</loc><lastmod>{TODAY}</lastmod></url>
''' + ''.join(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n' for u in rurls) + f'''</urlset>
''')
print('site built', len(index))
