"""Gives every restaurant that has no photo from a deal platform its own picture.

Where the picture comes from, in this order:
1. The restaurant's own website: the image it sets for link previews (og:image / twitter:image). robots.txt respected.
   Credit: "Photo: <their website>", linking to it.
2. Wikimedia Commons, through Wikidata (free licences only: CC0, public domain, CC BY, CC BY-SA).
   Credit: photographer + licence, linking to the file page (as the licences ask).
Logos, icons and graphics are skipped (too small, see-through, or too few colours). Each photo is cropped to 16:10,
shrunk to 720x450 and saved as WebP in img/ph/, so pages stay fast and visitors never load other sites.

Wikidata also gives some places their official website and exact map position (CC0 data); saved in src/wikidata.json.
Output: src/photos.json (+ img/ph/*.webp). Run after build.py:  python _build/photos.py
Owners can ask for a photo to be changed or removed: add the venue id to REMOVE below.
"""
import datetime, hashlib, html, io, json, math, os, re, subprocess, sys, tempfile, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webmeta import allowed, fetch   # same robots.txt check and fetcher as the website reader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, 'src')
OUT = os.path.join(SRC, 'photos.json')
WD_OUT = os.path.join(SRC, 'wikidata.json')
PH_DIR = os.path.join(ROOT, 'img', 'ph')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; hello@tablefifty.co.uk)'
TODAY = datetime.date.today()
BUDGET = int(os.environ.get('PH_BUDGET', '900'))
REMOVE = set()          # venue ids whose owner asked us not to show a photo
# website photo checked by eye and not right (poster, logo, job ad, not the place): we try other sources instead
REJECT_WEB = {   # exact venue ids
    'cl-arments-pie-mash-london': 'Halloween poster', 'cl-e-pellicci-london': 'mostly blank collage', 'cl-the-rock-sole-plaice-london': 'sea photo',
    'mich-cadet-london': 'job advert', 'mich-elsa-london': 'logo', 'mich-kolae-london': 'logo', 'mich-dinner-by-heston-blumenthal-london': 'a fan',
    'mich-the-harwood-arms-london': 'a deer', 'mich-walnut-tree-llanddewi-skirrid': 'awards photo', 'the-sushi-co-lewisham': 'promo banner',
    'mich-condita-edinburgh': 'close-up texture', 'ana-turkish-restaurant-and-bar': 'logo', 'el-inca-plebeyo': 'text banner', 'mich-ardfern-leith': 'book cover',
    'mich-charlton-arms-ludlow': 'text banner', 'mich-ed-belfast': 'website banner', 'mich-el-gato-negro-manchester': 'text banner',
    'mich-hitchen-s-barn-oakham': 'guide logo', 'mich-loch-bay-isle-of-skye': 'logo', 'mich-lyla-edinburgh': 'sky photo', 'mich-mountain-london': 'field photo',
    'mich-noto-edinburgh': 'logo', 'mich-plaquemine-lock-london': 'illustration', 'mich-sketch-the-lecture-room-library-london': 'graphic',
    'mich-tamila-london': 'graphic', 'mich-the-samling-ambleside': 'hotel bedroom', 'mich-tropea-birmingham': 'logo',
    'mich-where-the-light-gets-in-stockport': 'logo', 'stereo-covent-garden': 'text banner', 'amor-gastronomia': 'city skyline',
    'mich-pulpo-negro-new-alresford': 'brick wall', 'mich-ugly-butterfly-by-adam-handling-newquay': 'same photo as Frog'}
SPAM = re.compile(r'(?i)(casino|betting|bookmaker|slot games|free spins|login bonus|poker|viagra|payday loan|escort)')
CDN = re.compile(r'(?i)(imgix\.net|squarespace(-cdn)?\.com|wixstatic\.com|cloudinary\.com|shopify\.com|website-files\.com|amazonaws\.com|'
                 r'cloudfront\.net|googleusercontent\.com|ctfassets\.net|sanity\.io|storyblok\.com|prismic\.io|wp\.com|b-cdn\.net|'
                 r'hubspotusercontent|cdn\.|images\.|media\.|static\.|assets\.)')


def rejected(vid):
    return vid in REJECT_WEB


def same_site(a, b):
    da, db = (urlparse(x).netloc.lower().removeprefix('www.') for x in (a, b))
    base = lambda d: '.'.join(d.split('.')[-3:]) if re.search(r'\.(co|org|ac|gov)\.uk$', d) else '.'.join(d.split('.')[-2:])
    return base(da) == base(db)
SIZE = (720, 450)

try:
    from PIL import Image, ImageOps, ImageStat
except ImportError:
    print('::warning title=Photos::Pillow is not installed, skipping'); sys.exit(0)


def km(a, b):
    la1, la2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def nk(n):
    s = unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower().replace('&', ' and ').replace("'", '').replace('’', '')
    s = re.sub(r'\([^)]*\)', ' ', s)
    return ''.join(t for t in re.findall(r'[a-z0-9]+', s) if t not in ('the', 'restaurant', 'and'))


# ---------- picture checks ----------
def to_webp(data, dest, portrait_ok=False):
    """Checks the image is a real photo and saves it cropped/shrunk. Returns None if fine, else the reason."""
    try:
        im = Image.open(io.BytesIO(data)); im.load()
    except Exception:
        return 'not an image'
    w, h = im.size
    if w < 480 or h < 280: return f'too small {w}x{h}'
    if not (0.5 if portrait_ok else 0.9) <= w / h <= 2.8: return f'odd shape {w}x{h}'   # hand-picked shop fronts may be tall
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        a = im.convert('RGBA').getchannel('A').resize((64, 64))
        if sum(1 for x in a.tobytes() if x < 250) > 64 * 64 * 0.03: return 'see-through (logo)'
    rgb = im.convert('RGB')
    small = rgb.resize((48, 48))
    b = small.tobytes()
    if len({b[i:i + 3] for i in range(0, len(b), 3)}) < 400: return 'too few colours (logo or graphic)'
    g = small.convert('L')
    if ImageStat.Stat(g).stddev[0] < 22: return 'flat image'
    if sum(1 for x in g.tobytes() if x > 235) > 48 * 48 * 0.45: return 'mostly blank'
    out = ImageOps.fit(rgb, SIZE, Image.LANCZOS, centering=(0.5, 0.42 if w / h < 1 else 0.45))
    out.save(dest, 'WEBP', quality=72, method=6)
    return None


def download(url, maxbytes=12_000_000):
    with tempfile.NamedTemporaryFile() as f:
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '25', '--max-filesize', str(maxbytes), '-A', UA, '-o', f.name,
                            '-w', '%{http_code}', url], capture_output=True, text=True)
        try: code = int(r.stdout.strip() or 0)
        except ValueError: code = 0
        if r.returncode != 0 or not 200 <= code < 300: return None, f'http {code or r.returncode}'
        return open(f.name, 'rb').read(), ''


# ---------- 1) the restaurant's own website ----------
BAD_IMG = re.compile(r'(?i)(logo|icon|favicon|sprite|placeholder|default[-_]?(share|og|image)|blank|spacer|avatar|badge|award|tripadvisor|'
                     r'opentable|google|facebook|instagram|wix\.com/.*/v1/fill/w_\d{2,3},h_\d{2,3}|\.svg(\?|$)|\.gif(\?|$))')


def page_images(h, base):
    """Image addresses the page offers for previews, best first."""
    found = []
    for tag in re.findall(r'<meta\b[^>]*>', h, re.I | re.S):
        m = re.search(r'(?:property|name)\s*=\s*["\'](og:image(?::secure_url|:url)?|twitter:image(?::src)?)["\']', tag, re.I)
        c = re.search(r'content\s*=\s*["\']([^"\']{5,600})["\']', tag, re.I | re.S)
        if m and c: found.append(html.unescape(c.group(1)).strip())
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.I | re.S):
        for m in re.finditer(r'"image"\s*:\s*(?:\[\s*)?(?:\{[^}]*?"url"\s*:\s*)?"([^"]{5,600})"', block):
            found.append(m.group(1).replace('\\/', '/'))
    # no preview image set: the big photos on the homepage (hero / slider / gallery), best guesses first
    imgs = []
    for m in re.finditer(r'<img\b[^>]*>', h, re.I | re.S):
        tag = m.group(0)
        srcs = re.findall(r'(?:data-src|data-lazy-src|src)\s*=\s*["\']([^"\']+\.(?:jpe?g|webp|png)(?:\?[^"\']*)?)["\']', tag, re.I)
        ss = re.search(r'srcset\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if ss:   # widest candidate in srcset
            parts = [p.strip().rsplit(' ', 1) for p in ss.group(1).split(',') if p.strip()]
            parts = [(int(p[1][:-1]) if len(p) == 2 and p[1][:-1].isdigit() else 0, p[0]) for p in parts]
            if parts: srcs.insert(0, max(parts)[1])
        if not srcs: continue
        hint = 3 if re.search(r'(?i)(hero|banner|slide|carousel|gallery|header|cover|interior|food|dish|restaurant|dining|home)', tag) else 0
        w = re.search(r'\bwidth\s*=\s*["\']?(\d+)', tag)
        if w and int(w.group(1)) < 400: continue
        if w and int(w.group(1)) >= 800: hint += 2
        imgs.append((-hint, m.start(), srcs[0]))
    found += [u for _, _, u in sorted(imgs)[:6]]
    out = []
    for u in found:
        u = urljoin(base, html.unescape(u))
        if u.startswith('http') and not BAD_IMG.search(u) and u not in out: out.append(u)
    return out[:6]


USED_SRC = set()


def from_website(v):
    site = v['web']
    if not allowed(site): return None, 'robots'
    h, code, final = fetch(site)
    if not h or code >= 400 or code == 0: return None, f'site http {code}'
    if len(SPAM.findall(h)) >= 3: return None, 'spam site'   # old domain taken over: build_data hides this link
    why = 'no preview image'
    for u in page_images(h, final):
        if not same_site(u, final) and not CDN.search(urlparse(u).netloc): why = 'image on another website'; continue
        if u in USED_SRC: why = 'same photo as another place'; continue   # e.g. a group site showing one picture for every branch
        if urlparse(u).netloc == urlparse(final).netloc and not allowed(u): why = 'image blocked by robots'; continue
        data, err = download(u)
        if not data: why = err; continue
        dest = os.path.join(PH_DIR, v['id'] + '.webp')
        bad = to_webp(data, dest)
        if bad: why = bad; continue
        dom = urlparse(final).netloc.lower().removeprefix('www.')
        USED_SRC.add(u)
        return {'f': f'img/ph/{v["id"]}.webp', 'from': 'web', 'src': u, 'by': dom, 'page': site, 't': TODAY.isoformat()}, ''
    return None, why


# ---------- 2) Wikidata + Wikimedia Commons ----------
WD_QUERY = '''SELECT ?item ?itemLabel ?img ?web ?coord WHERE {
  VALUES ?cls { wd:Q11707 wd:Q212198 wd:Q30022 wd:Q1501295 wd:Q2001305 wd:Q274393 wd:Q2140703 wd:Q1137809 wd:Q5307737 }
  ?item wdt:P31 ?cls ; wdt:P17 wd:Q145 .
  OPTIONAL { ?item wdt:P18 ?img } OPTIONAL { ?item wdt:P856 ?web } OPTIONAL { ?item wdt:P625 ?coord }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }'''


def wikidata_rows():
    r = subprocess.run(['curl', '-sS', '--max-time', '120', '-A', UA, '-H', 'Accept: application/sparql-results+json',
                        '--data-urlencode', 'query=' + WD_QUERY, 'https://query.wikidata.org/sparql'], capture_output=True, text=True)
    try: rows = json.loads(r.stdout)['results']['bindings']
    except Exception: return None
    out = {}
    for x in rows:
        q = x['item']['value'].rsplit('/', 1)[1]
        o = out.setdefault(q, {'q': q, 'n': x['itemLabel']['value'], 'k': nk(x['itemLabel']['value'])})
        if 'coord' in x and 'll' not in o:
            m = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', x['coord']['value'])
            if m: o['ll'] = [round(float(m.group(2)), 5), round(float(m.group(1)), 5)]
        if 'img' in x and 'img' not in o: o['img'] = unquote(x['img']['value'].rsplit('/', 1)[1]).replace('_', ' ')
        if 'web' in x and 'web' not in o and x['web']['value'].startswith('http'): o['web'] = x['web']['value']
    return [o for o in out.values() if o.get('ll') and o['k']]


def match_wikidata(venues, rows):
    by = {}
    for r in rows: by.setdefault(r['k'], []).append(r)
    # (a venue known only by its town is matched only if no other UK place in Wikidata has that name)
    found = {}
    for v in venues:
        cands = by.get(nk(v['n'])) or []
        if not cands or not v.get('ll'): continue
        if v.get('llx') or v.get('llw'):   # only the town is known (llw: spot came from Wikidata itself)
            if len(cands) == 1 and km(v['ll'], cands[0]['ll']) < 8 and not COMMON.search(v['n']): found[v['id']] = cands[0]
        else:
            near = sorted((km(v['ll'], r['ll']), i, r) for i, r in enumerate(cands))
            if near and near[0][0] < 0.25: found[v['id']] = near[0][2]
    return {k: {x: r[x] for x in ('q', 'img', 'web', 'll') if r.get(x)} for k, r in found.items()}


COMMON = re.compile(r'(?i)\b(arms|inn|tavern|horseshoes?|crown|swan|plough|bell|lion|hart|oak|head|star|anchor|ship|george|fox|bull|'
                    r'wheatsheaf|rose|angel|bear|chequers|cross keys|feathers|globe|greyhound|hare|hound|kings?|queens?|railway|'
                    r'red|white|black|green|royal|victoria|wellington|nelson|cricketers|coach|horses?|plume|pheasant|duck|cock|hop)\b')
FREE = re.compile(r'(?i)^(cc0|public domain|pd\b|pd-|cc[ -]by(-sa)?[ -]\d)')


def commons_info(files):
    """Thumbnail address, author and licence for up to 50 Commons files."""
    titles = '|'.join('File:' + f.replace('_', ' ') for f in files)
    r = subprocess.run(['curl', '-sS', '--max-time', '40', '-A', UA, '--get', 'https://commons.wikimedia.org/w/api.php',
                        '--data-urlencode', 'action=query', '--data-urlencode', 'format=json', '--data-urlencode', 'prop=imageinfo',
                        '--data-urlencode', 'iiprop=url|extmetadata', '--data-urlencode', 'iiurlwidth=960',
                        '--data-urlencode', 'titles=' + titles], capture_output=True, text=True)
    try: pages = json.loads(r.stdout)['query']['pages'].values()
    except Exception: return None
    norm = {}
    try:
        for n in json.loads(r.stdout)['query'].get('normalized', []): norm[n['to']] = n['from']
    except Exception: pass
    out = {}
    for p in pages:
        ii = (p.get('imageinfo') or [None])[0]
        if not ii: continue
        md = ii.get('extmetadata', {})
        lic = (md.get('LicenseShortName') or {}).get('value', '')
        if not FREE.search(lic): continue
        artist = re.sub(r'<[^>]+>', '', html.unescape((md.get('Artist') or {}).get('value', ''))).strip()
        artist = re.sub(r'\s+', ' ', artist)[:60] or 'Unknown author'
        title = norm.get(p['title'], p['title'])[5:].replace(' ', '_')
        out[title] = {'thumb': ii.get('thumburl') or ii.get('url'), 'page': ii.get('descriptionurl'), 'by': artist, 'lic': lic}
    return out


# ---------- main ----------
def main():
    t0 = time.time()
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    os.makedirs(PH_DIR, exist_ok=True)
    state = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    wd = json.load(open(WD_OUT, encoding='utf-8')) if os.path.exists(WD_OUT) else {}
    need = [v for v in deals if v.get('k') == 'dine' and not (v.get('img') or v.get('imgx')) and v.get('ct') != 'uk' and v.get('reg') != 'multi'
            and v['id'] not in REMOVE and (not v.get('imgl') or v['imgl'].startswith('img/ph/'))]

    # Wikidata once a week (one download for the whole UK)
    if (TODAY - datetime.date.fromisoformat(wd.get('checked', '2000-01-01'))).days >= 7:
        rows = wikidata_rows()
        if rows:
            wd = {'checked': TODAY.isoformat(), 'm': match_wikidata([v for v in deals if v.get('k') == 'dine'], rows)}
            json.dump(wd, open(WD_OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
            print(f'Wikidata: {len(rows)} UK places, {len(wd["m"])} matched to our venues '
                  f'({sum(1 for x in wd["m"].values() if x.get("img"))} with a photo, {sum(1 for x in wd["m"].values() if x.get("web"))} with a website)')
        else:
            print('::warning title=Photos::Wikidata did not answer today')
    WM = {k: dict(x) for k, x in wd.get('m', {}).items()}
    pf = os.path.join(SRC, 'photo_files.json')   # Commons photos we picked by hand for a venue (file name)
    PICKED = json.load(open(pf, encoding='utf-8')) if os.path.exists(pf) else {}
    for k, f in PICKED.items():
        WM.setdefault(k, {})['img'] = f

    def due(v):
        s = state.get(v['id'])
        if not s: return True
        if s.get('f'): return not os.path.exists(os.path.join(ROOT, s['f']))
        if s.get('from_tried') != bool(v.get('web')) or (s.get('wd') != bool(WM.get(v['id'], {}).get('img'))): return True   # new source since
        return (TODAY - datetime.date.fromisoformat(s.get('t', '2000-01-01'))).days >= 14

    USED_SRC.update(s['src'] for s in state.values() if s.get('f') and s.get('src'))
    todo = [v for v in need if due(v)]
    print(f'{len(need)} venues have no platform photo; {len(todo)} to try today', flush=True)

    # 1) websites, a few at a time
    web_todo = [v for v in todo if v.get('web') and not rejected(v['id'])]
    got_web = {}
    def one(v):
        if time.time() - t0 > BUDGET * 0.6: return v['id'], None, 'time'
        try: rec, why = from_website(v)
        except Exception as e: rec, why = None, str(e)[:60]
        return v['id'], rec, why
    with ThreadPoolExecutor(6) as ex:
        for vid, rec, why in ex.map(one, web_todo):
            if rec: state[vid] = rec; got_web[vid] = 1
            elif why != 'time':
                state[vid] = {'none': why, 't': TODAY.isoformat(), 'from_tried': True}
                if why == 'spam site': state[vid]['spam'] = next(v['web'] for v in web_todo if v['id'] == vid)

    # 2) Commons for the rest (one by one, politely)
    rest = [v for v in todo if v['id'] not in got_web and WM.get(v['id'], {}).get('img')]
    commons_ok = 0; commons_seen = set()
    for i in range(0, len(rest), 50):
        if time.time() - t0 > BUDGET: break
        batch = rest[i:i + 50]
        info = commons_info([WM[v['id']]['img'] for v in batch])
        if info is None:
            print('::warning title=Photos::Wikimedia Commons did not answer (will retry next run)'); break
        for v in batch:
            commons_seen.add(v['id'])
            f = WM[v['id']]['img']
            key = f.replace(' ', '_'); ci = info.get(key) or info.get(key[:1].upper() + key[1:])
            prev = state.get(v['id'], {})
            if not ci or not ci.get('thumb'):
                state[v['id']] = {**prev, 'none': prev.get('none', 'no free photo'), 't': TODAY.isoformat(), 'from_tried': bool(v.get('web')), 'wd': True}; continue
            data, err = download(ci['thumb']); time.sleep(1)
            bad = to_webp(data, os.path.join(PH_DIR, v['id'] + '.webp'), portrait_ok=v['id'] in PICKED) if data else err
            if bad:   # a refused download (busy server) is tried again next run; a bad picture waits 14 days
                state[v['id']] = {'none': bad, 't': TODAY.isoformat(), 'from_tried': bool(v.get('web'))}
                if data: state[v['id']]['wd'] = True
                else: commons_seen.discard(v['id']); time.sleep(4)
                continue
            state[v['id']] = {'f': f'img/ph/{v["id"]}.webp', 'from': 'commons', 'src': ci['thumb'], 'by': f'{ci["by"]}, {ci["lic"]}',
                              'page': ci['page'], 't': TODAY.isoformat()}
            commons_ok += 1
        time.sleep(1)
    for v in todo:   # remember what we looked at, so we wait 14 days before trying again
        s = state.get(v['id'])
        if s and not s.get('f'):
            s.setdefault('from_tried', bool(v.get('web')))
            if v['id'] in commons_seen or not WM.get(v['id'], {}).get('img'): s['wd'] = bool(WM.get(v['id'], {}).get('img'))
            else: s.pop('wd', None)   # Commons not reached today: try again next run

    # drop photos of venues we no longer list, and files nobody uses
    ids = {v['id'] for v in deals}
    for k in [k for k in state if k not in ids or k in REMOVE]: state.pop(k)
    used = {os.path.basename(s['f']) for s in state.values() if s.get('f')}
    for fn in os.listdir(PH_DIR):
        if fn.endswith('.webp') and fn not in used: os.remove(os.path.join(PH_DIR, fn))
    json.dump(dict(sorted(state.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
    have = sum(1 for v in need if state.get(v['id'], {}).get('f'))
    print(f'::notice title=Photos::{len(got_web)} new from restaurant websites, {commons_ok} from Wikimedia Commons today | '
          f'{have} of {len(need)} venues without a platform photo now have their own')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        print('::warning title=Photos crashed::' + ' | '.join(traceback.format_exc().strip().splitlines()[-3:])[:600])
