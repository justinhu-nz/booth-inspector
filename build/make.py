"""Inline data into the page template.
  python3 build/make.py TEMPLATE DATA COAST BOUNDS OUT [--basemap]
--basemap adds Leaflet + CARTO street tiles (works when opened from your computer; the published artifact blocks outside tiles)."""
import sys, pathlib
tpl, data, coast, bounds, out = map(pathlib.Path, sys.argv[1:6])
basemap = '--basemap' in sys.argv
t = tpl.read_text(encoding='utf-8')
safe = lambda p: p.read_text(encoding='utf-8').replace('</', '<\\/') if p.exists() else 'null'
t = t.replace('/*DATA*/', safe(data), 1).replace('/*COAST*/', safe(coast), 1).replace('/*BOUNDS*/', safe(bounds), 1)
if basemap:
    head = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">\n'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>\n'
            '<script src="carto-key.js"></script>\n'   # sets window.BI_CARTO_KEY; kept out of this file on purpose
            '<script>window.BI_BASEMAP = true;</script>\n')
    t = t.replace('<style>', head + '<style>', 1)
if '--doc' in sys.argv:  # standalone file for opening from disk: full document with doctype + charset
    t = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
         '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n' + t + '\n</body>\n</html>\n')
out.write_text(t, encoding='utf-8'); print(out, len(t.encode()), 'basemap' if basemap else '')
# syntax-check the page's inline scripts (needs node); fails the build on a parse error
import re, subprocess, tempfile, shutil
if shutil.which('node'):
    for i, js in enumerate(re.findall(r'<script>([\s\S]*?)</script>', t)):
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write('(function(){' + js + '\n})');
        r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
        if r.returncode: sys.exit('Script ' + str(i) + ' has a syntax error:\n' + r.stderr)
    print('scripts parse OK')
