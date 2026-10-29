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
def to_webp(data, dest, portrait_ok=False, size=None):
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
    out = ImageOps.fit(rgb, size or SIZE, Image.LANCZOS, centering=(0.5, 0.42 if w / h < 1 else 0.45))
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


def page_images(h, base, n=6):
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
    found += [u for _, _, u in sorted(imgs)[:n]]
    out = []
    for u in found:
        u = urljoin(base, html.unescape(u))
        if u.startswith('http') and not BAD_IMG.search(u) and u not in out: out.append(u)
    return out[:n]


USED_SRC = set()
GSIZE = (640, 400)   # extra photos (Insights gallery) are a bit smaller


def ahash(path):
    im = Image.open(path).convert('L').resize((16, 10)); b = im.tobytes(); m = sum(b) / len(b)
    return int(''.join('1' if x > m else '0' for x in b), 2)


def near(a, b): return bin(a ^ b).count('1') <= 12   # same picture at another size or crop


def gallery_from_site(v, rec):
    """Up to 9 more photos of this place from its own homepage, each different from the others."""
    site = v['web']
    if not allowed(site): return []
    h, code, final = fetch(site)
    if not h or code >= 400 or code == 0 or len(SPAM.findall(h)) >= 3: return []
    hashes = [ahash(os.path.join(ROOT, rec['f']))] if rec.get('f') and os.path.exists(os.path.join(ROOT, rec['f'])) else []
    out = []
    for u in page_images(h, final, n=20):
        if len(out) >= 9: break
        if u == rec.get('src') or u in USED_SRC: continue
        if not same_site(u, final) and not CDN.search(urlparse(u).netloc): continue
        if urlparse(u).netloc == urlparse(final).netloc and not allowed(u): continue
        data, err = download(u)
        if not data: continue
        dest = os.path.join(PH_DIR, f'{v["id"]}-{len(out) + 2}.webp')
        if to_webp(data, dest, size=GSIZE): continue
        hh = ahash(dest)
        if any(near(hh, x) for x in hashes): os.remove(dest); continue
        hashes.append(hh); USED_SRC.add(u)
        out.append({'f': f'img/ph/{v["id"]}-{len(out) + 2}.webp', 'src': u})
    return out


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


# ---------- 3) last resort: a name card that is different for every place (never a shared picture) ----------
TTF = os.path.join(HERE, 'ttf')
PALETTES = [((20, 52, 43), (38, 92, 72), (232, 196, 120)), ((58, 21, 30), (110, 34, 48), (244, 200, 150)), ((18, 32, 64), (34, 64, 120), (250, 190, 90)),
            ((12, 58, 64), (20, 104, 108), (250, 226, 170)), ((84, 38, 20), (150, 72, 36), (255, 222, 170)), ((44, 24, 64), (88, 46, 116), (246, 190, 220)),
            ((70, 56, 14), (130, 104, 30), (255, 238, 190)), ((22, 40, 30), (64, 96, 52), (238, 222, 150)), ((36, 36, 44), (74, 72, 92), (240, 180, 120)),
            ((10, 46, 82), (16, 92, 140), (190, 236, 250)), ((96, 20, 52), (160, 40, 82), (255, 214, 214)), ((30, 60, 20), (72, 118, 40), (240, 250, 190)),
            ((64, 30, 12), (120, 60, 26), (250, 210, 120)), ((16, 24, 40), (44, 60, 96), (164, 214, 255)), ((52, 44, 36), (100, 86, 70), (246, 226, 196)),
            ((8, 60, 52), (14, 118, 98), (255, 200, 150))]


def card_label(v):
    m = v.get('mich')
    if m: lab = ['MICHELIN GUIDE', 'MICHELIN STAR', 'TWO MICHELIN STARS', 'THREE MICHELIN STARS'][m[0]] if m[0] else ('BIB GOURMAND' if m[1] else 'MICHELIN GUIDE')
    elif v.get('cl'): lab = 'BRITISH CLASSIC'
    elif v.get('k') == 'delivery': lab = 'DELIVERY DEAL'
    elif v.get('k') == 'grocery': lab = 'GROCERY SAVINGS'
    elif v.get('k') == 'coffee': lab = 'COFFEE & BAKERY DEAL'
    elif v.get('reg') == 'multi' or v.get('ct') == 'uk': lab = 'PUB DEAL' if v.get('pub') else 'CHAIN OFFER'
    else: lab = 'RESTAURANT'
    where = '' if v.get('reg') == 'multi' or v.get('ct') == 'uk' else (v.get('a') or '').split(',')[-1].strip()
    where = re.sub(r'\s+[A-Z]{1,2}\d[\dA-Z]?\s*\d[A-Z]{2}$', '', where)   # drop the postcode
    return lab, ('Across the UK' if not where else where)


def card_sig(v):
    return hashlib.md5(('|'.join([v['n'], *card_label(v)]) + '|v1').encode()).hexdigest()[:10]


def name_card(v, dest):
    from PIL import ImageDraw, ImageFont, ImageFilter
    h = hashlib.md5(v['id'].encode()).digest()
    c1, c2, acc = PALETTES[h[0] % len(PALETTES)]
    W, H = SIZE
    im = Image.new('RGB', SIZE, c1)
    px = im.load()
    ang = (h[1] % 4)
    for y in range(H):   # soft diagonal gradient, direction differs per place
        for x in range(0, W, 4):
            t = ((x / W) if ang == 0 else (y / H) if ang == 1 else ((x + y) / (W + H)) if ang == 2 else ((W - x + y) / (W + H)))
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            for dx in range(4): px[x + dx, y] = col
    ov = Image.new('RGBA', SIZE, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(3):   # three big soft rings, placed by the name
        cx, cy, r = h[2 + i * 3] / 255 * W, h[3 + i * 3] / 255 * H, 90 + h[4 + i * 3] % 220
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=acc + (38,), width=10 + h[5 + i] % 26)
    ov = ov.filter(ImageFilter.GaussianBlur(1.2))
    im = Image.alpha_composite(im.convert('RGBA'), ov)
    d = ImageDraw.Draw(im)
    lab, where = card_label(v)
    small = ImageFont.truetype(os.path.join(TTF, 'Figtree-Bold.ttf'), 22)
    d.text((48, 52), ' '.join(lab), font=small, fill=acc + (255,))
    name = re.sub(r'\s+', ' ', v['n']).strip()
    for size in (84, 76, 68, 60, 54, 48, 42, 38):
        f = ImageFont.truetype(os.path.join(TTF, 'BricolageGrotesque-ExtraBold.ttf'), size)
        words, lines, cur = name.split(' '), [], ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=f) <= W - 96: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) <= 3 and all(d.textlength(l, font=f) <= W - 96 for l in lines): break
    lh = int(size * 1.08); y0 = H - 70 - lh * len(lines)
    for i, l in enumerate(lines): d.text((46, y0 + i * lh), l, font=f, fill=(255, 250, 240, 255))
    d.text((48, H - 56), where, font=ImageFont.truetype(os.path.join(TTF, 'Figtree-Bold.ttf'), 24), fill=(255, 255, 255, 190))
    im.convert('RGB').save(dest, 'WEBP', quality=80, method=6)


# ---------- main ----------
def main():
    t0 = time.time()
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    os.makedirs(PH_DIR, exist_ok=True)
    state = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    wd = json.load(open(WD_OUT, encoding='utf-8')) if os.path.exists(WD_OUT) else {}
    # everyone: every card with no platform photo (restaurants, chains, pubs, coffee, delivery, groceries)
    everyone = [v for v in deals if not (v.get('img') or v.get('imgx')) and v['id'] not in REMOVE
                and (not v.get('imgl') or v['imgl'].startswith('img/ph/'))]
    need = [v for v in everyone if v.get('k') == 'dine' and v.get('ct') != 'uk' and v.get('reg') != 'multi']   # single places

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
    pf = os.path.join(SRC, 'photo_files.json')   # Commons photos picked by hand (file name)
    PICKED = json.load(open(pf, encoding='utf-8')) if os.path.exists(pf) else {}
    for k, f in PICKED.items():
        WM.setdefault(k, {})['img'] = f
    pu = os.path.join(SRC, 'photo_urls.json')    # photos picked by hand from the place's own website (image address + page)
    PURL = json.load(open(pu, encoding='utf-8')) if os.path.exists(pu) else {}
    real = lambda s: bool(s and s.get('f') and s.get('from') != 'card')

    def fail(vid, **kw):   # remember why there is no photo, but keep a name card if the place has one
        s = state.get(vid) or {}
        keep = {k: s[k] for k in ('f', 'from', 'sig') if s.get('from') == 'card' and k in s}
        state[vid] = {**keep, 't': TODAY.isoformat(), **kw}

    def due(v):
        s = state.get(v['id'])
        if not s: return True
        if real(s): return not os.path.exists(os.path.join(ROOT, s['f']))
        if s.get('from_tried') != bool(v.get('web')) or (s.get('wd') != bool(WM.get(v['id'], {}).get('img'))): return True   # new source since
        return (TODAY - datetime.date.fromisoformat(s.get('t', '2000-01-01'))).days >= 14

    USED_SRC.update(s['src'] for s in state.values() if real(s) and s.get('src'))
    USED_SRC.update(x['src'] for s in state.values() for x in s.get('g', []) if x.get('src'))

    # 0) photos picked by hand from the place's own website
    got_pick = 0
    for v in everyone:
        p = PURL.get(v['id'])
        if not p: continue
        s = state.get(v['id'])
        if real(s) and s.get('src') == p['url'] and os.path.exists(os.path.join(ROOT, s['f'])): continue
        if not allowed(p['url']): fail(v['id'], none='picked photo blocked by robots'); continue
        data, err = download(p['url'])
        bad = to_webp(data, os.path.join(PH_DIR, v['id'] + '.webp'), portrait_ok=True) if data else err
        if bad: fail(v['id'], none='picked photo: ' + bad); continue
        page = p.get('page') or p['url']
        state[v['id']] = {'f': f'img/ph/{v["id"]}.webp', 'from': 'pick', 'src': p['url'], 'by': urlparse(page).netloc.lower().removeprefix('www.'),
                          'page': page, 't': TODAY.isoformat()}
        USED_SRC.add(p['url']); got_pick += 1

    todo = [v for v in need if due(v) and not real(state.get(v['id']))]
    print(f'{len(everyone)} cards have no platform photo ({len(need)} single places); {len(todo)} places to try today', flush=True)

    # 1) the restaurant website's preview image, a few at a time
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
                fail(vid, none=why, from_tried=True)
                if why == 'spam site': state[vid]['spam'] = next(v['web'] for v in web_todo if v['id'] == vid)

    # 2) Wikimedia Commons (one by one, politely): Wikidata matches and photos picked by hand
    rest = [v for v in everyone if (v in todo or v['id'] in PICKED) and due(v) and not real(state.get(v['id'])) and WM.get(v['id'], {}).get('img')]
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
                fail(v['id'], none=prev.get('none', 'no free photo'), from_tried=bool(v.get('web')), wd=True); continue
            if ci['thumb'] in USED_SRC: fail(v['id'], none='same photo as another place', from_tried=bool(v.get('web')), wd=True); continue
            data, err = download(ci['thumb']); time.sleep(1)
            bad = to_webp(data, os.path.join(PH_DIR, v['id'] + '.webp'), portrait_ok=v['id'] in PICKED) if data else err
            if bad:   # a refused download (busy server) is tried again next run; a bad picture waits 14 days
                fail(v['id'], none=bad, from_tried=bool(v.get('web')))
                if data: state[v['id']]['wd'] = True
                else: commons_seen.discard(v['id']); time.sleep(4)
                continue
            state[v['id']] = {'f': f'img/ph/{v["id"]}.webp', 'from': 'commons', 'src': ci['thumb'], 'by': f'{ci["by"]}, {ci["lic"]}',
                              'page': ci['page'], 't': TODAY.isoformat()}
            USED_SRC.add(ci['thumb']); commons_ok += 1
        time.sleep(1)
    for v in todo + rest:   # remember what we looked at, so we wait 14 days before trying again
        s = state.get(v['id'])
        if s and not real(s):
            s.setdefault('from_tried', bool(v.get('web')))
            if v['id'] in commons_seen or not WM.get(v['id'], {}).get('img'): s['wd'] = bool(WM.get(v['id'], {}).get('img'))
            else: s.pop('wd', None)   # Commons not reached today: try again next run

    # 2b) more photos (gallery, up to 10 in all) for places whose photo came from their own website; re-checked monthly
    gal_new = 0
    gtodo = [v for v in everyone if v.get('web') and real(state.get(v['id'])) and not rejected(v['id'])
             and (TODAY - datetime.date.fromisoformat(state[v['id']].get('gt', '2000-01-01'))).days >= 30]
    def gone_and_get(v):
        if time.time() - t0 > BUDGET * 0.9: return v['id'], None
        try: return v['id'], gallery_from_site(v, state[v['id']])
        except Exception: return v['id'], []
    with ThreadPoolExecutor(6) as ex:
        for vid, g in ex.map(gone_and_get, gtodo):
            if g is None: continue
            old = {x['f'] for x in state[vid].get('g', [])} - {x['f'] for x in g}
            for f in old:
                if os.path.exists(os.path.join(ROOT, f)): os.remove(os.path.join(ROOT, f))
            state[vid]['g'] = g; state[vid]['gt'] = TODAY.isoformat(); gal_new += len(g)

    # 3) everyone still without a photo gets a name card of its own
    cards = 0
    for v in everyone:
        s = state.get(v['id']) or {}
        if real(s) and os.path.exists(os.path.join(ROOT, s['f'])): continue
        dest = os.path.join(PH_DIR, v['id'] + '.webp'); sig = card_sig(v)
        if s.get('from') == 'card' and s.get('sig') == sig and os.path.exists(dest): continue
        name_card(v, dest)
        state[v['id']] = {**{k: x for k, x in s.items() if k not in ('f', 'from', 'sig', 'src', 'by', 'page')},
                          'f': f'img/ph/{v["id"]}.webp', 'from': 'card', 'sig': sig, 't': s.get('t', TODAY.isoformat())}
        cards += 1

    # drop venues we no longer list, and files nobody uses
    ids = {v['id'] for v in deals}
    for k in [k for k in state if k not in ids or k in REMOVE]: state.pop(k)
    used = {os.path.basename(s['f']) for s in state.values() if s.get('f')} | {os.path.basename(x['f']) for s in state.values() for x in s.get('g', [])}
    for fn in os.listdir(PH_DIR):
        if fn.endswith('.webp') and fn not in used: os.remove(os.path.join(PH_DIR, fn))
    json.dump(dict(sorted(state.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
    have = sum(1 for v in everyone if real(state.get(v['id'])))
    print(f'::notice title=Photos::today: {got_pick} picked, {len(got_web)} from websites, {commons_ok} from Wikimedia Commons, {gal_new} extra gallery photos, {cards} name cards | '
          f'{have} of {len(everyone)} cards without a platform photo have a real photo; the rest have their own name card')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        print('::warning title=Photos crashed::' + ' | '.join(traceback.format_exc().strip().splitlines()[-3:])[:600])
