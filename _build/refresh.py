"""Daily First Table check for TableFifty.

Reads First Table's public sitemap (robots.txt allows it; only /api/, /auth/, /profile/, /preview are disallowed),
then re-checks, one page at a time:
  * restaurants that are new in the sitemap,
  * restaurants whose sitemap "lastmod" date changed,
  * the oldest-checked restaurants (a rolling batch), so every page is re-verified about once a week.
Restaurants that leave the sitemap are dropped. Results go to src/ft_pages.jsonl.
"""
import datetime, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'src', 'ft_pages.jsonl')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; daily deal check)'
ROLLING = int(os.environ.get('FT_ROLLING', '320'))   # extra oldest pages to re-check per run
MAX_CHECKS = int(os.environ.get('FT_MAX', '900'))    # safety cap per run
PAUSE = float(os.environ.get('FT_PAUSE', '1.0'))     # seconds between requests (be polite)
TODAY = datetime.date.today().isoformat()


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-GB'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # network hiccup: wait and retry
            last = e
            time.sleep(4 * (attempt + 1))
    raise last


def pick(page):
    tags = [e['node'] for e in (page.get('cuisines') or {}).get('edges', [])]
    return {
        'title': page.get('title'), 'status': page.get('status'), 'show': page.get('showOnFrontend'),
        'ft': page.get('offersFirstTable'), 'meta': page.get('metaTitleFormatted'), 'metaDesc': page.get('metaDescription'),
        'city': page.get('city'), 'suburb': (page.get('suburb') or {}).get('menuTitle'), 'region': (page.get('region') or {}).get('menuTitle'),
        'street': page.get('street'), 'zip': page.get('zip'), 'lat': page.get('lat'), 'lng': page.get('lng'),
        'rating': page.get('rating'), 'reviews': page.get('approvedReviewsCount') or page.get('reviewsCount'),
        'sessions': page.get('firstTableSessionTypes') or page.get('sessionTypes'), 'mains': page.get('mainsPriceRange'),
        'tags': [(t.get('category'), t.get('title')) for t in tags if t.get('active', True)],
        'instagram': page.get('instagram'), 'website': page.get('website'), 'tiktok': page.get('tiktok'), 'facebook': page.get('facebook'),
        'phone': page.get('phone'), 'hours': page.get('openHours'),
        'subs': [[r.get('title'), round(r.get('average') or 0, 2)] for r in (page.get('ratingSummaries') or []) if r.get('title') and r.get('average')],
        'photos': [u for u in ([page.get('gallery')] + [(e.get('node') or {}).get('url') for e in (page.get('images') or {}).get('edges', [])[:3]]) if u][:3],
        'menus': [img['node']['url'] for m in (page.get('menus') or {}).get('edges', [])
                  for img in ((m.get('node') or {}).get('menuImages') or {}).get('edges', [])[:4] if (img.get('node') or {}).get('url')][:6],
    }


def restaurant_paths(xml, depth=0):
    """Restaurant pages from the sitemap. Handles a sitemap index (list of child sitemaps), a missing <lastmod>,
    CDATA, extra spaces and the address with or without "www"."""
    out = {}
    if '<sitemapindex' in xml[:2000] and depth < 2:
        for child in re.findall(r'<loc>\s*(?:<!\[CDATA\[)?\s*([^<\]\s]+)', xml):
            if re.search(r'(?i)(magazine|blog|news|image)', child): continue
            try: out.update(restaurant_paths(get(child), depth + 1))
            except Exception as e: print('  child sitemap failed:', child, str(e)[:80])
            time.sleep(PAUSE)
        return out
    for block in re.findall(r'<url>(.*?)</url>', xml, re.S):
        m = re.search(r'<loc>\s*(?:<!\[CDATA\[)?\s*https://(?:www\.)?firsttable\.co\.uk/([^<\]\s]+)', block)
        if not m: continue
        lm = re.search(r'<lastmod>\s*([^<\s]+)', block)
        p = m.group(1).split('?')[0].strip('/').split('/')
        if (p[0] == 'london' and len(p) == 4) or (p[0] not in ('london', 'magazine') and len(p) == 3):
            out['/'.join(p)] = lm.group(1) if lm else ''
    return out


def main():
    old = {}
    if os.path.exists(DATA):
        for line in open(DATA, encoding='utf-8'):
            r = json.loads(line)
            old[r['path']] = r
    xml = get('https://www.firsttable.co.uk/sitemap.xml')
    sm = restaurant_paths(xml)
    if len(sm) < 500:
        head = re.sub(r'\s+', ' ', xml[:400])
        sys.exit(f'Sitemap looks wrong ({len(sm)} restaurants, {len(xml)} bytes) - keeping yesterday\'s data. Start: {head}')

    new = [p for p in sm if p not in old]
    changed = [p for p in sm if p in old and old[p].get('lastmod') != sm[p]]
    rest = sorted((p for p in sm if p in old and p not in changed), key=lambda p: old[p].get('checked') or '')
    todo = (new + changed + rest[:ROLLING])[:MAX_CHECKS]
    print(f'sitemap {len(sm)} | new {len(new)} | changed {len(changed)} | checking {len(todo)}')

    result = {p: old[p] for p in sm if p in old}       # pages gone from the sitemap are dropped
    ok = fail = 0
    for p in todo:
        rec = {'path': p, 'lastmod': sm[p], 'checked': TODAY}
        try:
            html = get('https://www.firsttable.co.uk/' + p)
            d = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S).group(1))
            page = d['props']['pageProps']['page']
            if page.get('__typename') == 'Restaurant':
                rec.update(pick(page)); ok += 1
            else:
                rec['err'] = 'not restaurant: ' + str(page.get('__typename'))
        except Exception as e:
            fail += 1
            if p in old:                                  # keep the last good copy if one page fails today
                result[p] = old[p]; time.sleep(PAUSE); continue
            rec['err'] = str(e)[:100]
        result[p] = rec
        time.sleep(PAUSE)
    if todo and fail > len(todo) * 0.5:
        sys.exit(f'Too many failures ({fail}/{len(todo)}) - not saving.')
    with open(DATA, 'w', encoding='utf-8') as f:
        for p in sorted(result):
            f.write(json.dumps(result[p], ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'checked ok {ok}, failed {fail}, dropped {len(old) - len([p for p in old if p in sm])}')


if __name__ == '__main__':
    main()
