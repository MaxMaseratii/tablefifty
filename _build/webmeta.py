"""Reads each restaurant's own website homepage once (robots.txt respected) and keeps the short
description the restaurant wrote for search engines and link previews (meta description / og:description).
Output: src/web_meta.jsonl. Re-checks a site only if it's new or older than 30 days.
"""
import datetime, html, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from urllib import robotparser

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'src', 'web_meta.jsonl')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; restaurant info check)'
TODAY = datetime.date.today()
WORKERS = int(os.environ.get('WM_WORKERS', '6'))


def curl(url, maxtime=15):
    r = subprocess.run(['curl', '-sS', '-L', '--max-time', str(maxtime), '--max-filesize', '3000000', '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    return r.stdout if r.returncode == 0 else None


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


def one(site):
    rec = {'url': site, 'checked': TODAY.isoformat()}
    try:
        if not allowed(site):
            rec['skip'] = 'robots'; return rec
        h = curl(site)
        if not h:
            rec['err'] = 'fetch'; return rec
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
    todo = [s for s in sites if s not in old or (TODAY - datetime.date.fromisoformat(old[s]['checked'])).days > 30]
    print(f'{len(sites)} sites, {len(todo)} to check')
    with ThreadPoolExecutor(WORKERS) as ex:
        for r in ex.map(one, todo):
            old[r['url']] = r
    with open(OUT, 'w', encoding='utf-8') as f:
        for u in sorted(old):
            if u in sites: f.write(json.dumps(old[u], ensure_ascii=False, separators=(',', ':')) + '\n')
    print('with description:', sum(1 for u in sites if old.get(u, {}).get('desc')))


if __name__ == '__main__':
    src = os.path.join(HERE, 'src', 'deals.js')
    s = open(src, encoding='utf-8').read()
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', s, re.S).group(1))
    sites = sorted({v['web'] for v in deals if v.get('web', '').startswith('http')})
    main(sites)
