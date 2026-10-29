"""Finds the has.restaurant page of our places (e.g. regencycafe.has.restaurant, epellicci.has.restaurant).

has.restaurant gives many eateries their own small site with a menu, reviews and photo albums. There is no public list,
so we try the address made from the place's name (a name that does not exist simply does not answer) and keep a page
only when it shows the same name AND the same street, postcode or town. Run before photos.py; photos.py then takes
gallery photos from it. Output: src/hasr.json  {"checked": {id: date}, "m": {id: "https://<name>.has.restaurant/"}}
robots.txt of has.restaurant allows everything except /wp-admin/.
"""
import datetime, html, json, os, re, subprocess, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, 'src')
OUT = os.path.join(SRC, 'hasr.json')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; photo check)'
BUDGET = int(os.environ.get('HR_BUDGET', '600'))
TODAY = datetime.date.today()
STOP = {'the', 'and', 'restaurant', 'cafe', 'bar', 'kitchen', 'grill', 'london', 'ltd', 'co', 'of', 'at', 'by', 'a', 'on', 'in', 'pub'}


def toks(s):
    s = unicodedata.normalize('NFKD', (s or '').lower()).encode('ascii', 'ignore').decode()
    return re.findall(r'[a-z0-9]+', s.replace('&', ' and ').replace("'", '').replace('’', ''))


def slugs(v):
    t = toks(v['n'])
    if not t: return []
    base = [t, t[1:] if t[0] == 'the' else t, [x for x in t if x != 'and']]
    out = []
    for b in base:
        if b: out.append(''.join(b))
    core = [x for x in (t[1:] if t[0] == 'the' else t) if x not in ('restaurant',)]
    if len(core) >= 3: out.append(''.join(core[:2]))
    key = [x for x in t if x not in STOP]
    if key: out.append(''.join(key))   # "Pierino Restaurant" -> pierino
    if v.get('ct') and v['ct'] not in ('uk',): out.append(''.join(t[1:] if t[0] == 'the' else t) + v['ct'].replace('-', ''))
    seen, res = set(), []
    for s in out:
        if 3 <= len(s) <= 63 and s not in seen: seen.add(s); res.append(s)
    return res[:6]


def get(url):
    r = subprocess.run(['curl', '-sS', '-L', '--max-time', '12', '-A', UA, '-w', '\n%{http_code}', url], capture_output=True)
    if r.returncode or not r.stdout: return None, 0
    body, _, code = r.stdout.rpartition(b'\n')
    try: return body.decode('utf-8', 'ignore'), int(code)
    except ValueError: return None, 0


def text(h):
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', h)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t))).lower()


def same_place(v, h, contact):
    """Same name near the top of the page, and the same street, postcode or town somewhere on it (or its contact page)."""
    top = ' '.join(toks(text(h)[:600]))
    key = [x for x in toks(v['n']) if x not in STOP] or toks(v['n'])
    if not all(re.search(rf'\b{re.escape(k)}\b', top) for k in key): return False
    body = text(h) + ' ' + text(contact or '')
    a = (v.get('a') or '').lower()
    pc = re.search(r'\b([a-z]{1,2}\d[a-z\d]?)\s*\d[a-z]{2}\b', a)
    if pc and re.search(rf'\b{pc.group(1)}\s*\d[a-z]{{2}}\b', body): return True
    street = re.match(r'\s*(?:\d+[a-z]?\s*[-,]?\s*)?([a-z\' ]+?)\s+(road|street|lane|row|place|square|avenue|hill|way|parade|terrace|walk|yard|market|grove|gardens)\b', a)
    if street and f'{street.group(1).strip()} {street.group(2)}' in body: return True
    town = v.get('ct') if v.get('ct') not in ('london', 'uk', None) else None
    if town and re.search(rf'\b{re.escape(town.replace("-", " "))}\b', body): return True
    # the area in our address ("Camberwell, London") named on their page
    for part in a.split(','):
        part = part.strip()
        if part and not re.search(r'\d', part) and part not in ('london', 'uk', 'england', 'united kingdom') and len(part) >= 4 \
                and re.search(rf'\b{re.escape(part)}\b', body):
            return True
    return False


def check(v):
    for s in slugs(v):
        url = f'https://{s}.has.restaurant/'
        h, code = get(url)
        if not h or code != 200: continue
        c, _ = get(url + 'contact/')
        if same_place(v, h, c): return v['id'], url
    return v['id'], None


def main():
    t0 = time.time()
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    st = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {'checked': {}, 'm': {}}
    ids = {v['id'] for v in deals}
    st['checked'] = {k: d for k, d in st['checked'].items() if k in ids}
    st['m'] = {k: u for k, u in st['m'].items() if k in ids}
    todo = [v for v in deals if v.get('k') == 'dine' and v.get('reg') != 'multi' and v.get('ct') != 'uk'
            and (TODAY - datetime.date.fromisoformat(st['checked'].get(v['id'], '2000-01-01'))).days >= 90]
    print(f'has.restaurant: {len(todo)} places to check', flush=True)
    found = 0
    def one(v):
        if time.time() - t0 > BUDGET: return v['id'], 'time'
        try: return check(v)
        except Exception: return v['id'], 'time'
    with ThreadPoolExecutor(16) as ex:
        for i, (vid, url) in enumerate(ex.map(one, todo), 1):
            if url == 'time': continue
            st['checked'][vid] = TODAY.isoformat()
            if url: st['m'][vid] = url; found += 1; print('  found', vid, url, flush=True)
            if i % 500 == 0:
                json.dump(st, open(OUT, 'w', encoding='utf-8'), indent=0, sort_keys=True); print(f'  {i}/{len(todo)}', flush=True)
    json.dump(st, open(OUT, 'w', encoding='utf-8'), indent=0, sort_keys=True)
    print(f'::notice title=has.restaurant::{found} new pages found; {len(st["m"])} places have one')


if __name__ == '__main__':
    try: main()
    except Exception as e: print('::warning title=has.restaurant::' + str(e)[:300])
