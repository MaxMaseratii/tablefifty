"""Finds the SAME picture used by two branches of a chain (each branch uploads its own copy to First Table / EatClub,
so the addresses differ but the photo is the same). Run after build.py; build_data.py then keeps each picture on one card only.

Only cards whose name starts like another card's ("Franco Manca Brixton", "Franco Manca Soho") are checked.
Each photo is fetched once, shrunk to a tiny fingerprint and remembered in src/photo_prints.json, so later runs only fetch
new photos. Output: src/photo_dupes.json  {photo address: id of the card that keeps it}.
"""
import collections, io, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, 'src')
PRINTS = os.path.join(SRC, 'photo_prints.json'); OUT = os.path.join(SRC, 'photo_dupes.json')
UA = 'TableFiftyBot/1.0 (+https://tablefifty.co.uk; photo check)'
BUDGET = int(os.environ.get('PD_BUDGET', '900'))
try:
    from PIL import Image, ImageOps
except ImportError:
    print('::warning title=Photo repeats::Pillow missing, skipped'); sys.exit(0)


def brand(n):
    t = re.findall(r'[a-z0-9]+', (n or '').lower().replace("'", ''))
    return ' '.join(t[:2]) if len(t) >= 2 else (t[0] if t else '')


def fetch_url(u):
    if u.startswith('public/'): return 'https://images.firsttable.net/320x180/' + u   # small copy straight from their CDN
    return u


ROOT = os.path.dirname(HERE)


def fingerprint(u):
    if u.startswith('img/'):   # our own photo, already on disk
        try: im = Image.open(os.path.join(ROOT, u)).convert('L')
        except Exception: return None
    else:
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '25', '-A', UA, fetch_url(u)], capture_output=True)
        if r.returncode or not r.stdout: return None
        try:
            im = Image.open(io.BytesIO(r.stdout)).convert('L')
        except Exception:
            return None
    a = ImageOps.fit(im, (17, 16)); px = a.load()   # difference hash 16x16 on a centre crop
    bits = ''.join('1' if px[x, y] > px[x + 1, y] else '0' for y in range(16) for x in range(16))
    b = ImageOps.fit(im, (12, 8)).tobytes(); m = sum(b) / len(b)
    return [int(bits, 2), int(''.join('1' if x > m else '0' for x in b), 2)]


def same(p, q):
    return bin(p[0] ^ q[0]).count('1') <= 26 and bin(p[1] ^ q[1]).count('1') <= 14


def main():
    t0 = time.time()
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    prints = json.load(open(PRINTS)) if os.path.exists(PRINTS) else {}
    groups = collections.defaultdict(list)
    for v in deals:
        if (v.get('img') or v.get('imgx') or v.get('imgl')) and not v.get('phc'): groups[brand(v['n'])].append(v)
    groups = {k: vs for k, vs in groups.items() if len(vs) >= 2 and k}
    main_of = lambda v: v.get('img') or v.get('imgx') or v.get('imgl')
    urls = {u for vs in groups.values() for v in vs for u in [main_of(v)] + v.get('g', [])
            if u and (u.startswith('public/') or u.startswith('https://eccdn.com.au/') or u.startswith('img/ph/'))}
    own_mt = {u: int(os.path.getmtime(os.path.join(ROOT, u))) for u in urls if u.startswith('img/') and os.path.exists(os.path.join(ROOT, u))}
    todo = sorted(u for u in urls if u not in prints or (u in own_mt and prints[u][2:3] != [own_mt[u]]))
    print(f'{len(groups)} chain names, {len(urls)} photos; {len(todo)} new to fingerprint', flush=True)
    def one(u):
        if time.time() - t0 > BUDGET: return u, None
        return u, fingerprint(u)
    with ThreadPoolExecutor(8) as ex:
        for i, (u, fp) in enumerate(ex.map(one, todo), 1):
            if fp: prints[u] = fp + ([own_mt[u]] if u in own_mt else [])
            if i % 200 == 0:
                json.dump(prints, open(PRINTS, 'w'), separators=(',', ':')); print(f'  {i}/{len(todo)}', flush=True)
    prints = {u: p for u, p in prints.items() if u in urls}   # forget photos no longer listed
    json.dump(dict(sorted(prints.items())), open(PRINTS, 'w'), separators=(',', ':'))
    ids = {v['id'] for v in deals}
    # keep earlier findings: the build already took those photos off the other branches, so they are no longer listed here
    dupes = {u: o for u, o in (json.load(open(OUT)) if os.path.exists(OUT) else {}).items() if o in ids}
    for k, vs in groups.items():
        seen = []   # (print, owner id), in id order: the first card keeps the picture
        for v in sorted(vs, key=lambda x: x['id']):
            for u in [main_of(v)] + v.get('g', []):
                p = prints.get(u)
                if not p: continue
                if u in dupes: continue
                own = next((o for q, o in seen if o != v['id'] and same(p, q)), None)
                if own: dupes[u] = own
                else: seen.append((p, v['id']))
    # our own photos that repeat another card's photo: turn them down, so photos.py finds another one (or a name card)
    own = {u: o for u, o in dupes.items() if u.startswith('img/ph/')}
    if own:
        PH = os.path.join(SRC, 'photos.json'); RJ = os.path.join(SRC, 'photo_rejects.json')
        st = json.load(open(PH, encoding='utf-8')); rj = json.load(open(RJ, encoding='utf-8')) if os.path.exists(RJ) else {}
        for vid, rec in st.items():
            if rec.get('f') in own and rec.get('from') != 'card':
                if rec.get('src'): rj[rec['src']] = f'same picture as {own[rec["f"]]}'
                st[vid] = {'none': 'repeat of another card', 't': '2000-01-01', 'g': rec.get('g', [])}
            if rec.get('g'):
                keep = [x for x in rec['g'] if x['f'] not in own]
                for x in rec['g']:
                    if x['f'] in own: rj[x['src']] = f'same picture as {own[x["f"]]}'
                st[vid]['g'] = keep
        json.dump(dict(sorted(st.items())), open(PH, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
        json.dump(dict(sorted(rj.items())), open(RJ, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    dupes = {u: o for u, o in dupes.items() if not u.startswith('img/ph/')}
    json.dump(dict(sorted(dupes.items())), open(OUT, 'w'), indent=0)
    if own: print(f'::notice title=Photo repeats::{len(own)} of our own photos repeated another card and were turned down')
    cards = {v['id'] for vs in groups.values() for v in vs if (v.get('img') or v.get('imgx')) in dupes}
    print(f'::notice title=Photo repeats::{len(dupes)} chain photos repeat another branch\'s photo ({len(cards)} cards lose their main photo to the first branch and get the next own one)')


if __name__ == '__main__':
    main()
