"""Copies the website's fonts from Google Fonts into /fonts once, so visitors' browsers never contact Google
(no visitor IP address goes to Google = one less data transfer to mention in the privacy policy).
Run: python _build/fonts.py   (only needed again if the fonts change)"""
import os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'fonts'); os.makedirs(os.path.join(OUT, 'files'), exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
SETS = {
    'main': 'Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500',
    'arabic': 'Noto+Naskh+Arabic:wght@400;600;700',
    'gurmukhi': 'Noto+Sans+Gurmukhi:wght@400;600;700',
    'bengali': 'Noto+Sans+Bengali:wght@400;600;700',
}
def get(url, binary=False):
    r = subprocess.run(['curl', '-sSfL', '--max-time', '60', '-A', UA, url], capture_output=True)
    if r.returncode: raise SystemExit(f'download failed: {url}')
    return r.stdout if binary else r.stdout.decode()
for name, fam in SETS.items():
    css = get(f'https://fonts.googleapis.com/css2?family={fam}&display=swap')
    def local(m):
        url = m.group(1); fn = re.sub(r'[^A-Za-z0-9_.-]', '_', url.split('/s/', 1)[-1])
        path = os.path.join(OUT, 'files', fn)
        if not os.path.exists(path): open(path, 'wb').write(get(url, True))
        return f'url(files/{fn})'
    css = re.sub(r'url\((https://fonts\.gstatic\.com/[^)]+)\)', local, css)
    open(os.path.join(OUT, f'{name}.css'), 'w').write('/* Self-hosted copy of Google Fonts (SIL Open Font License). */\n' + css)
    print(name, css.count('@font-face'), 'faces')
