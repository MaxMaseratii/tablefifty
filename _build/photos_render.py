"""One-off helper (run by hand, not in the daily job): for places whose website has no usable preview image,
open the homepage in a real browser (robots.txt respected, same TableFifty user agent) and take the biggest photo
shown on it (hero / slider / gallery). Same checks as photos.py (logos, banners, other websites are skipped).
Needs Playwright with Chromium.  Run after build.py:  python _build/photos_render.py
"""
import datetime, json, os, re, sys, time
from urllib.parse import urlparse, urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import photos as P
from webmeta import allowed

RETRY = re.compile(r'(no preview image|too small|odd shape|see-through|too few colours|mostly blank|flat image|image on another website|http 4\d\d$)')
JS = r'''() => { const out = [];
  for (const i of document.images) { const r = i.getBoundingClientRect();
    if (i.naturalWidth >= 600 && i.naturalHeight >= 300 && r.width >= 280) out.push([r.width * r.height + i.naturalWidth, i.currentSrc || i.src]); }
  for (const el of document.querySelectorAll('section,div,header,figure,a,li')) {
    const bg = getComputedStyle(el).backgroundImage; const m = bg && bg.match(/url\(["']?(.*?)["']?\)/);
    if (m) { const r = el.getBoundingClientRect(); if (r.width >= 500 && r.height >= 250) out.push([r.width * r.height, m[1]]); } }
  const seen = new Set(); return out.sort((a, b) => b[0] - a[0]).map(x => x[1]).filter(u => u && !u.startsWith('data:') && !seen.has(u) && seen.add(u)).slice(0, 8); }'''


def main():
    from playwright.sync_api import sync_playwright
    deals = json.loads(re.search(r'const DEALS = (\[.*\]);', open(os.path.join(P.SRC, 'deals.js'), encoding='utf-8').read(), re.S).group(1))
    state = json.load(open(P.OUT, encoding='utf-8'))
    todo = [v for v in deals if v.get('k') == 'dine' and v.get('web') and not (v.get('img') or v.get('imgx') or v.get('imgl'))
            and v.get('ct') != 'uk' and v.get('reg') != 'multi' and not P.rejected(v['id']) and v['id'] not in P.REMOVE
            and RETRY.search(str(state.get(v['id'], {}).get('none', 'no preview image'))) and not state.get(v['id'], {}).get('rendered')]
    print(len(todo), 'websites to open in a browser')
    got = 0
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(user_agent=P.UA, viewport={'width': 1366, 'height': 900})
        t0 = time.time(); budget = int(os.environ.get('PR_BUDGET', '1300'))
        save = lambda: json.dump(dict(sorted(state.items())), open(P.OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
        for n, v in enumerate(todo, 1):
            if time.time() - t0 > budget: print('time budget used, stopping (run again to continue)'); break
            if n % 10 == 0: save(); print(f'  {n}/{len(todo)}, {got} new', flush=True)
            rec = state.get(v['id'], {})
            try:
                if not allowed(v['web']): continue
                pg = ctx.new_page()
                pg.goto(v['web'], timeout=30000, wait_until='domcontentloaded'); pg.wait_for_timeout(3500)
                final = pg.url
                if len(P.SPAM.findall(pg.content())) >= 3: pg.close(); continue
                urls = [urljoin(final, u) for u in pg.evaluate(JS)]
                pg.close()
            except Exception as e:
                rec.update({'rendered': 1}); state[v['id']] = rec; continue
            why = 'no photo on page'
            for u in urls:
                if P.BAD_IMG.search(u): continue
                if not P.same_site(u, final) and not P.CDN.search(urlparse(u).netloc): why = 'image on another website'; continue
                data, err = P.download(u)
                if not data: why = err; continue
                bad = P.to_webp(data, os.path.join(P.PH_DIR, v['id'] + '.webp'))
                if bad: why = bad; continue
                state[v['id']] = {'f': f'img/ph/{v["id"]}.webp', 'from': 'web', 'src': u, 'by': urlparse(final).netloc.lower().removeprefix('www.'),
                                  'page': v['web'], 't': P.TODAY.isoformat()}
                got += 1; why = ''; break
            if why: state[v['id']] = {**rec, 'none': why, 'rendered': 1, 't': P.TODAY.isoformat()}
        br.close()
    json.dump(dict(sorted(state.items())), open(P.OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ':'))
    print(got, 'new photos from rendered pages')


if __name__ == '__main__':
    main()
