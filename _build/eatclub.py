"""Daily EatClub check for TableFifty.

EatClub (eatclub.co.uk) is a free app with up-to-50%-off time-slot deals.
robots.txt allows everything except query-string pages (?q=, ?page= ...), so we only read
/sitemap-html pages (their public venue index) and /venue/<slug> pages. One request at a time, with a pause.
Output: src/ec_pages.jsonl (one venue per line).
"""
import datetime, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'src', 'ec_pages.jsonl')
BASE = 'https://eatclub.co.uk'
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; daily deal check)'
PAUSE = float(os.environ.get('EC_PAUSE', '0.8'))
WORKERS = int(os.environ.get('EC_WORKERS', '2'))
TODAY = datetime.date.today().isoformat()


def get(path):
    last = None
    for attempt in range(3):
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '25', '-A', UA, '-H', 'Accept-Language: en-GB', BASE + path],
                           capture_output=True, text=True, errors='replace')
        if r.returncode == 0 and r.stdout:
            return r.stdout
        last = RuntimeError(r.stderr.strip()[:120] or 'empty response')
        time.sleep(3 * (attempt + 1))
    raise last


def links(html, prefix):
    return sorted(set(re.findall(r'href="(' + re.escape(prefix) + r'[^"?#]*)"', html)))


def flight(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    return ''.join(json.loads('"' + c + '"') for c in chunks)


def grab(s, key):
    i = s.find('"' + key + '":')
    if i < 0:
        return None
    j = i + len(key) + 3
    try:
        return json.JSONDecoder().raw_decode(s[j:])[0]
    except Exception:
        return None


def venue(slug):
    html = get('/venue/' + slug)
    s = flight(html)
    v = grab(s, 'venue') or {}
    deals = grab(s, 'deals') or []
    rating = re.search(r'\\?"ratingValue\\?":([0-9.]+),\\?"reviewCount\\?":(\d+)', s)
    ds = []
    for d in deals:
        m = re.match(r'(\d+)', str(d.get('discount', '')))
        if not m:
            continue
        ds.append([int(d.get('dayOfWeek') or 0), int(d.get('startTime') or 0), int(d.get('endTime') or 0), int(m.group(1)), d.get('type') or ''])
    return {
        'slug': slug, 'checked': TODAY, 'name': v.get('name'), 'region': v.get('region'), 'area': v.get('city'),
        'address': ', '.join(x for x in [v.get('address1'), v.get('address2')] if x), 'postcode': v.get('postcode'),
        'lat': v.get('latitude'), 'lng': v.get('longitude'), 'cuisines': v.get('cuisines') or [], 'image': v.get('imageLink'),
        'phone': v.get('phone'), 'website': v.get('website'), 'menu': v.get('pdfMenu'),
        'rating': float(rating.group(1)) if rating else None, 'reviews': int(rating.group(2)) if rating else 0,
        'deals': ds,
    }


def main():
    top = get('/sitemap-html')
    cities = [l for l in links(top, '/sitemap-html/') if l.count('/') == 2]
    areas = []
    for c in cities:
        time.sleep(PAUSE)
        areas += [l for l in links(get(c), c + '/') if l.count('/') == 4]
    slugs, seen_pages = set(), set()
    queue = list(areas)
    while queue:
        page = queue.pop(0)
        if page in seen_pages:
            continue
        seen_pages.add(page)
        time.sleep(PAUSE)
        try:
            html = get(page)
        except Exception:
            continue
        slugs.update(l[len('/venue/'):] for l in links(html, '/venue/'))
        base = page.rsplit('/', 1)[0]
        queue += [l for l in links(html, base + '/') if re.match(re.escape(base) + r'/\d+$', l) and l not in seen_pages]
    print(f'{len(cities)} cities, {len(seen_pages)} index pages, {len(slugs)} venues')
    if len(slugs) < 200:
        sys.exit('Too few EatClub venues found - keeping yesterday\'s data.')

    part = OUT + '.part'
    done = {}
    if os.path.exists(part):
        for line in open(part, encoding='utf-8'):
            r = json.loads(line)
            if r.get('checked') == TODAY: done[r['slug']] = r
    fh = open(part, 'a', encoding='utf-8')
    def one(slug):
        if slug in done: return done[slug]
        time.sleep(PAUSE)
        try:
            r = venue(slug)
        except Exception as e:
            return {'slug': slug, 'err': str(e)[:80]}
        fh.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n'); fh.flush()
        return r
    with ThreadPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(one, sorted(slugs)))
    fh.close()
    good = [r for r in rows if not r.get('err') and r.get('name')]
    if len(good) < len(rows) * 0.6:
        sys.exit(f'Too many failures ({len(rows) - len(good)}/{len(rows)}) - not saving.')
    with open(OUT, 'w', encoding='utf-8') as f:
        for r in good:
            f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    os.remove(part)
    print(f'saved {len(good)} EatClub venues ({sum(1 for r in good if r["deals"])} with deals)')


if __name__ == '__main__':
    main()
