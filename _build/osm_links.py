"""Finds the website, Instagram, Facebook and phone of restaurants that have none yet, from OpenStreetMap
(free map data, ODbL licence; we keep only the links). One Overpass download of UK food places that list
a website or social page, then each of our venues is matched by name and distance (max 150 m).
Output: src/osm_links.json. Runs at most once a week, or sooner when 20+ new venues still need links.
Run: python _build/osm_links.py   (after build.py has written src/deals.js)
"""
import csv, datetime, io, json, math, os, re, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
OUT = os.path.join(SRC, 'osm_links.json')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; restaurant links from OpenStreetMap)'
TODAY = datetime.date.today()
MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
           'https://overpass.kumi.systems/api/interpreter']
COLS = ['::type', '::id', '::lat', '::lon', 'name', 'brand', 'website', 'contact:website', 'url', 'instagram', 'contact:instagram',
        'facebook', 'contact:facebook', 'phone', 'contact:phone']
AMEN = '^(restaurant|pub|bar|cafe|fast_food|biergarten|food_court)$'
QUERY = ('[out:csv(' + ','.join(c if c.startswith('::') else f'"{c}"' for c in COLS) + ';true;"\\t")][timeout:900][maxsize:1073741824];\n'
         'area["ISO3166-1"="GB"][admin_level=2]->.gb;\n(\n' +
         ''.join(f'  nwr["amenity"~"{AMEN}"]["name"]["{k}"](area.gb);\n'
                 for k in ['website', 'contact:website', 'url', 'instagram', 'contact:instagram', 'facebook', 'contact:facebook']) +
         ');\nout center;\n')

STOP = {'the', 'restaurant', 'restaurants', 'bar', 'kitchen', 'cafe', 'and', 'ltd', 'limited', 'co', 'grill', 'dining', 'room', 'by', 'at', 'of',
        'london', 'uk', 'eatery', 'house', 'bistro'}
BAD_WEB = re.compile(r'(?i)(facebook\.com|instagram\.com|tiktok\.com|twitter\.com|x\.com|tripadvisor|linktr\.ee|deliveroo|just-eat|ubereats|'
                     r'opentable|thefork|firsttable|google\.|yell\.com|bit\.ly)')


def norm_tokens(name):
    s = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    s = s.replace('&', ' and ').replace("'", '').replace('’', '')
    s = s.split(' - ')[0]
    toks = [t for t in re.split(r'[^a-z0-9]+', s) if t]
    core = [t for t in toks if t not in STOP]
    return set(core or toks), ''.join(toks)


def sim(a, b):
    (ta, ca), (tb, cb) = a, b
    if not ta or not tb: return 0.0
    if ca == cb: return 1.0
    if len(ca) >= 5 and len(cb) >= 5 and (ca in cb or cb in ca): return 0.95
    return len(ta & tb) / min(len(ta), len(tb)) if min(len(ta), len(tb)) >= 1 else 0.0


def metres(a, b):
    R = 6371000; la1, la2 = math.radians(a[0]), math.radians(b[0])
    dla, dlo = la2 - la1, math.radians(b[1] - a[1])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def clean_web(u):
    u = (u or '').strip().split(';')[0].strip()
    if not u: return None
    if not re.match(r'^https?://', u): u = 'https://' + u.lstrip('/')
    m = re.match(r'^https?://([^/\s]+)', u)
    if not m or '.' not in m.group(1) or ' ' in u or BAD_WEB.search(m.group(1)): return None
    return u


def clean_ig(u):
    u = (u or '').strip().split(';')[0].strip()
    m = re.search(r'instagram\.com/([A-Za-z0-9_.]{2,30})', u) or re.fullmatch(r'@?([A-Za-z0-9_.]{2,30})', u)
    if not m or m.group(1).lower() in ('p', 'reel', 'explore', 'accounts', 'stories'): return None
    return f'https://www.instagram.com/{m.group(1)}/'


def clean_fb(u):
    u = (u or '').strip().split(';')[0].strip()
    m = re.search(r'facebook\.com/([A-Za-z0-9.\-]{3,60})', u) or re.fullmatch(r'([A-Za-z0-9.\-]{3,60})', u)
    if not m or not re.search(r'[A-Za-z]', m.group(1)) or m.group(1).lower() in ('people', 'pages', 'profile.php', 'groups', 'sharer'): return None
    return m.group(1)


def clean_ph(p):
    p = (p or '').split(';')[0].strip()
    d = re.sub(r'[^\d+]', '', p)
    if d.startswith('+44'): d = '0' + d[3:]
    if not re.fullmatch(r'0\d{9,10}', d): return None
    return d[:3] + ' ' + d[3:7] + ' ' + d[7:] if d.startswith('02') else d[:5] + ' ' + d[5:]


def download():
    for m in MIRRORS:
        print('Overpass:', m, flush=True)
        r = subprocess.run(['curl', '-sS', '--max-time', '1000', '-A', UA, '--data-urlencode', 'data@-', m],
                           input=QUERY, capture_output=True, text=True, errors='replace')
        if r.returncode == 0 and r.stdout.startswith('@type') and r.stdout.count('\n') > 1000:
            return r.stdout
        print('  failed:', r.returncode, (r.stderr or r.stdout)[:200].replace('\n', ' '), flush=True)
    return None


def parse(text):
    rows = []
    for r in csv.DictReader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE):
        try: ll = (float(r['@lat']), float(r['@lon']))
        except (TypeError, ValueError): continue
        web = clean_web(r.get('website')) or clean_web(r.get('contact:website')) or clean_web(r.get('url'))
        ig = clean_ig(r.get('contact:instagram')) or clean_ig(r.get('instagram'))
        for k in ('website', 'contact:website', 'url'):
            if not ig and 'instagram.com' in (r.get(k) or ''): ig = clean_ig(r.get(k))
        fb = clean_fb(r.get('contact:facebook')) or clean_fb(r.get('facebook'))
        ph = clean_ph(r.get('phone')) or clean_ph(r.get('contact:phone'))
        if web or ig or fb:
            rows.append({'osm': r['@type'][0] + r['@id'], 'name': r.get('name') or '', 'll': ll, 'web': web, 'ig': ig, 'fb': fb, 'ph': ph,
                         'tok': norm_tokens(r.get('name'))})
    return rows


def match(venues, rows):
    grid = {}
    for r in rows:
        grid.setdefault((round(r['ll'][0], 2), round(r['ll'][1], 2)), []).append(r)
    found = {}
    for v in venues:
        ll = v['ll']; vt = norm_tokens(v['n']); best = None
        for dy in (-0.01, 0, 0.01):
            for dx in (-0.01, 0, 0.01):
                for r in grid.get((round(ll[0] + dy, 2), round(ll[1] + dx, 2)), []):
                    s = sim(vt, r['tok'])
                    if s < 0.6: continue
                    d = metres(ll, r['ll'])
                    if d > (150 if s >= 0.95 else 80): continue
                    key = (s, -d)
                    if best is None or key > best[0]: best = (key, r, d)
        if best:
            r = best[1]
            found[v['id']] = {k: r[k] for k in ('web', 'ig', 'fb', 'ph') if r[k]} | {'osm': r['osm'], 'm': round(best[2])}
    return found


def needy(deals):
    return [v for v in deals if v.get('k') == 'dine' and v.get('ll') and v.get('reg') != 'multi' and v.get('ct') != 'uk'
            and not (v.get('web') and v.get('ig'))]


def main():
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {'checked': '2000-01-01', 'tried': [], 'links': {}}
    want = needy(deals)
    fresh = [v for v in want if v['id'] not in set(old.get('tried', []))]
    age = (TODAY - datetime.date.fromisoformat(old['checked'])).days
    print(f'{len(want)} venues miss a website or Instagram; {len(fresh)} never looked up; last download {age} days ago')
    if age < 7 and len(fresh) < 20 and '--force' not in sys.argv:
        print('Nothing to do today.'); return
    text = download()
    if not text:
        print('Overpass unavailable, keeping old links.'); return
    rows = parse(text)
    print(len(rows), 'OpenStreetMap food places with a website or social page')
    links = {**old.get('links', {}), **match(want, rows)}
    out = {'checked': TODAY.isoformat(), 'osm_places': len(rows), 'tried': sorted(v['id'] for v in want),
           'links': dict(sorted(links.items()))}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
    print('matched', len(links), '| website', sum(1 for x in links.values() if x.get('web')), '| instagram', sum(1 for x in links.values() if x.get('ig')),
          '| facebook', sum(1 for x in links.values() if x.get('fb')))


if __name__ == '__main__':
    main()
