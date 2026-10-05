"""Reads each restaurant's own website homepage once (robots.txt respected) and keeps:
- the short description the restaurant wrote for search engines (meta description / og:description)
- its Instagram, TikTok and Facebook pages and its menu link, when the homepage links to them
- whether the site still works ("fail" counts failed checks in a row; build_data drops a site after 2)
Output: src/web_meta.jsonl. Re-checks a site if it's new, older than 30 days, or read by an older version.
"""
import datetime, html, json, os, re, subprocess, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urljoin
from urllib import robotparser

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'src', 'web_meta.jsonl')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; restaurant info check)'
TODAY = datetime.date.today()
WORKERS = int(os.environ.get('WM_WORKERS', '6'))
VERSION = 2


def curl(url, maxtime=15):
    r = subprocess.run(['curl', '-sS', '-L', '--max-time', str(maxtime), '--max-filesize', '3000000', '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    return r.stdout if r.returncode == 0 else None


def fetch(url, maxtime=15):
    """Body, HTTP status and final address (after redirects). Status 0 = no answer (DNS, timeout, TLS)."""
    r = subprocess.run(['curl', '-sS', '-L', '--max-time', str(maxtime), '--max-filesize', '3000000', '-A', UA,
                        '-w', '\n@@T50@@%{http_code} %{url_effective}', url], capture_output=True, text=True, errors='replace')
    body, _, tail = r.stdout.rpartition('\n@@T50@@')
    code, _, final = tail.partition(' ')
    try: code = int(code)
    except ValueError: code = 0
    return body, code, final.strip() or url


def alive(url):
    r = subprocess.run(['curl', '-sS', '-L', '-o', '/dev/null', '--max-time', '12', '-r', '0-2048', '-A', UA, '-w', '%{http_code}', url],
                       capture_output=True, text=True, errors='replace')
    try: return 200 <= int(r.stdout.strip() or 0) < 400
    except ValueError: return False


IG_SKIP = {'p', 'reel', 'reels', 'explore', 'accounts', 'stories', 'tv', 'share', '_u', 'instagram', 'about', 'legal', 'developer', 'direct', 'web'}
FB_SKIP = {'sharer', 'sharer.php', 'share', 'plugins', 'dialog', 'tr', 'login', 'facebook', 'policies', 'help', 'groups', 'events', 'watch', 'business', 'profile.php', 'pages'}


def socials(h):
    """Most-linked Instagram / TikTok / Facebook page on the homepage."""
    out = {}
    ig = Counter(m.lower() for m in re.findall(r'instagram\.com/([A-Za-z0-9_.]{2,30})(?=[/"\'?#\s])', h) if m.lower() not in IG_SKIP)
    if ig: out['ig'] = f'https://www.instagram.com/{ig.most_common(1)[0][0]}/'
    tt = Counter(m.lower() for m in re.findall(r'tiktok\.com/@([A-Za-z0-9_.]{2,30})(?=[/"\'?#\s])', h))
    if tt: out['tt'] = f'https://www.tiktok.com/@{tt.most_common(1)[0][0]}'
    fb = Counter(m for m in re.findall(r'facebook\.com/([A-Za-z0-9.\-]{3,60})(?=[/"\'?#\s])', h)
                 if m.lower() not in FB_SKIP and m.lower() != 'people' and re.search(r'[A-Za-z]', m) and not m.lower().endswith('.php'))
    if fb: out['fb'] = fb.most_common(1)[0][0]
    return out


def find_menu(h, base):
    """A link to the menu: the link text or address says 'menu' (PDFs welcome)."""
    best = None
    for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', h, re.I | re.S):
        attrs, text = m.group(1), re.sub(r'<[^>]+>|\s+', ' ', m.group(2)).strip().lower()
        hm = re.search(r'href\s*=\s*["\']([^"\'#][^"\']*)["\']', attrs, re.I)
        if not hm: continue
        href = html.unescape(hm.group(1)).strip()
        if re.match(r'(?i)(mailto|tel|javascript|whatsapp):', href): continue
        url = urljoin(base, href)
        if not url.startswith('http') or url.rstrip('/') == base.rstrip('/'): continue
        if re.search(r'(?i)(instagram|facebook|tiktok|twitter|x\.com|deliveroo|ubereats|just-eat|opentable|firsttable|thefork|resy|sevenrooms|tripadvisor|google\.)', urlparse(url).netloc):
            continue
        path = urlparse(url).path.lower()
        score = 0
        if re.search(r'menu', path): score += 3
        if re.search(r'\bmenus?\b', text) and len(text) <= 40: score += 2
        if path.endswith('.pdf') and score: score += 1
        if re.search(r'(?i)(wedding|event|party|parties|function|christmas|festive|gift|voucher|job|career|group-booking)', path + ' ' + text): continue
        if re.search(r'(?i)(drink|wine|cocktail|kids|allergen|dessert)', path + ' ' + text): score -= 1
        if score >= 2 and (best is None or score > best[0]): best = (score, url)
    return best[1] if best else None


def allowed(url):
    u = urlparse(url)
    txt = curl(f'{u.scheme}://{u.netloc}/robots.txt', 8)
    if not txt or '<html' in txt[:200].lower():
        return True
    rp = robotparser.RobotFileParser()
    rp.parse(txt.splitlines())
    return rp.can_fetch(UA, url) and rp.can_fetch('*', url)


def meta(h, *names):
    for n in names:
        for tag in re.findall(r'<meta\b[^>]*>', h, re.I | re.S):
            if not re.search(r'(?:name|property)\s*=\s*["\']' + re.escape(n) + r'["\']', tag, re.I):
                continue
            m = re.search(r'content\s*=\s*"([^"]{20,600})"', tag, re.S) or re.search(r"content\s*=\s*'([^']{20,600})'", tag, re.S)
            if m:
                return re.sub(r'\s+', ' ', html.unescape(m.group(1))).strip()
    return None


JUNK = re.compile(r'(wix\.com|squarespace|wordpress|just another|coming soon|under construction|lorem ipsum|default description|cookie)', re.I)


def one(args):
    site, prev = args
    rec = {'url': site, 'checked': TODAY.isoformat(), 'v': VERSION}
    try:
        if not allowed(site):
            rec['skip'] = 'robots'; return rec
        h, code, final = fetch(site)
        if code in (404, 410) and urlparse(site).path.strip('/'):
            root = f'{urlparse(site).scheme}://{urlparse(site).netloc}/'
            h2, code2, final2 = fetch(root)
            if 200 <= code2 < 400 and h2: rec['home'] = final2; h, code, final = h2, code2, final2
        if code == 0 or code in (404, 410) or (code >= 500 and not h.strip()):
            rec['err'] = f'http {code}'; rec['fail'] = (prev or {}).get('fail', 0) + 1; return rec
        if not h or code >= 400:
            rec['err'] = f'http {code}'; return rec
        rec.update(socials(h))
        mu = find_menu(h, final)
        if mu and (urlparse(mu).netloc != urlparse(final).netloc or allowed(mu)) and alive(mu): rec['menu'] = mu
        d = meta(h, 'description', 'og:description', 'twitter:description')
        if d and not JUNK.search(d) and len(d) >= 40:
            rec['desc'] = d[:300]
        t = re.search(r'<title[^>]*>([^<]{3,160})</title>', h, re.I)
        if t: rec['title'] = re.sub(r'\s+', ' ', html.unescape(t.group(1))).strip()
    except Exception as e:
        rec['err'] = str(e)[:80]
    return rec


def main(sites):
    old = {}
    if os.path.exists(OUT):
        for l in open(OUT, encoding='utf-8'):
            r = json.loads(l); old[r['url']] = r
    todo = [s for s in sites if s not in old or old[s].get('v', 1) < VERSION or old[s].get('fail')
            or (TODAY - datetime.date.fromisoformat(old[s]['checked'])).days > 30]
    limit = int(os.environ.get('WM_LIMIT', '0'))
    if limit: todo = todo[:limit]
    print(f'{len(sites)} sites, {len(todo)} to check')
    def save():
        with open(OUT + '.tmp', 'w', encoding='utf-8') as f:
            for u in sorted(old):
                if u in sites: f.write(json.dumps(old[u], ensure_ascii=False, separators=(',', ':')) + '\n')
        os.replace(OUT + '.tmp', OUT)
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, r in enumerate(ex.map(one, [(t, old.get(t)) for t in todo]), 1):
            old[r['url']] = r
            if i % 100 == 0: save(); print(f'  {i}/{len(todo)}', flush=True)
    save()
    print('with description:', sum(1 for u in sites if old.get(u, {}).get('desc')),
          '| instagram:', sum(1 for u in sites if old.get(u, {}).get('ig')), '| menu:', sum(1 for u in sites if old.get(u, {}).get('menu')),
          '| failing:', sum(1 for u in sites if old.get(u, {}).get('fail')))


if __name__ == '__main__':
    src = os.path.join(HERE, 'src', 'deals.js')
    s = open(src, encoding='utf-8').read()
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', s, re.S).group(1))
    sites = sorted({v['web'] for v in deals if v.get('web', '').startswith('http')})
    main(sites)
