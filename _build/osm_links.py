"""Finds the website, Instagram, Facebook and phone of restaurants that have none yet, from OpenStreetMap
(free map data, ODbL licence; we keep only the links). One Overpass download of UK food places that list
a website or social page, then each of our venues is matched by name and distance (max 150 m).
Output: src/osm_links.json. Runs at most once a week, or sooner when 20+ new venues still need links.
Run: python _build/osm_links.py   (after build.py has written src/deals.js)
"""
import csv, datetime, io, json, math, os, re, subprocess, sys, time, unicodedata

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
HEAD = '[out:csv(' + ','.join(c if c.startswith('::') else f'"{c}"' for c in COLS) + ';true;"\\t")][timeout:180];\n'
KEYS = ['website', 'contact:website', 'url', 'instagram', 'contact:instagram', 'facebook', 'contact:facebook']


def query(bbox):
    b = ','.join(f'{x:.3f}' for x in bbox)
    return HEAD + '(\n' + ''.join(f'  nwr["amenity"~"{AMEN}"]["name"]["{k}"]({b});\n' for k in KEYS) + ');\nout center;\n'


def cells(venues, size=0.5):
    """Small map squares (about 55 x 35 km) around our venues, so each Overpass question stays quick."""
    out = {}
    for v in venues:
        a, b = math.floor(v['ll'][0] / size), math.floor(v['ll'][1] / size)
        out.setdefault(f'{a},{b}', ((a * size - 0.01, b * size - 0.01, (a + 1) * size + 0.01, (b + 1) * size + 0.01), []))[1].append(v)
    return out


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


def fetch_square(bbox):
    """One map square from Overpass. Returns CSV text or None (after trying each mirror once)."""
    last = ''
    for m in MIRRORS:
        r = subprocess.run(['curl', '-sS', '--max-time', '120', '-A', UA, '--data-urlencode', 'data@-', m],
                           input=query(bbox), capture_output=True, text=True, errors='replace')
        if r.returncode == 0 and r.stdout.startswith('@type'):
            return r.stdout, ''
        last = (r.stderr or r.stdout)[:160].replace('\n', ' ')
        time.sleep(3)
    return None, last


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
    """Works through the map squares a few at a time (time budget per run), saving after each one, so slow Overpass
    days still make progress. Each square is asked again after 7 days to catch new restaurants."""
    budget = int(os.environ.get('OSM_BUDGET', '900'))
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    links, done = old.get('links', {}), old.get('squares', {})
    groups = cells(needy(deals))
    todo = sorted((k for k in groups if (TODAY - datetime.date.fromisoformat(done.get(k, '2000-01-01'))).days >= 7),
                  key=lambda k: (done.get(k, ''), -len(groups[k][1])))
    print(f'{sum(len(v) for _, v in groups.values())} venues miss a website or Instagram, in {len(groups)} map squares; {len(todo)} squares due', flush=True)
    t0, ok, bad, last = time.time(), 0, 0, ''
    for k in todo:
        if time.time() - t0 > budget: break
        text, err = fetch_square(groups[k][0])
        if text is None:
            bad += 1; last = err; continue
        found = match(groups[k][1], parse(text))
        links.update(found); done[k] = TODAY.isoformat(); ok += 1
        print(f'  square {k}: {len(groups[k][1])} venues, {len(found)} matched', flush=True)
        json.dump({'checked': TODAY.isoformat(), 'squares': dict(sorted(done.items())), 'links': dict(sorted(links.items()))},
                  open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
        time.sleep(2)
    left = len(todo) - ok
    print(f'::notice title=OpenStreetMap lookup::{ok} squares done today, {left} left for the next runs | matched so far {len(links)}: website {sum(1 for x in links.values() if x.get("web"))}, '
          f'instagram {sum(1 for x in links.values() if x.get("ig"))}, facebook {sum(1 for x in links.values() if x.get("fb"))}')
    if bad: print(f'::warning title=OpenStreetMap lookup::{bad} map squares failed today (they will be retried). Last error: {last}')
    json.dump({'date': TODAY.isoformat(), 'squares_done_today': ok, 'squares_failed': bad, 'squares_left': left, 'matched_total': len(links),
               'last_error': last[:300]}, open(os.path.join(SRC, 'osm_status.json'), 'w'), indent=1)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:   # never break the daily job, but leave a note we can read
        import traceback
        tb = traceback.format_exc()
        print('::warning title=OpenStreetMap lookup crashed::' + ' | '.join(tb.strip().splitlines()[-3:])[:600])
        json.dump({'date': TODAY.isoformat(), 'error': tb[-1500:]}, open(os.path.join(SRC, 'osm_status.json'), 'w'), indent=1)
