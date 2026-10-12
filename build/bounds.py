"""Electorate borders clipped to land -> multi-level JSON for Booth Inspector.
Usage: python3 bounds.py LINZ_COAST_SHP OUT_JSON GENERAL_SHP [MAORI_SHP]
Needs shapely, pyshp, pyproj. Each border is the line shared by two neighbouring electorates, kept only where
it crosses land (25 m inland of the LINZ coastline, so shoreline-hugging slivers drop out), tagged with both names."""
import sys, json, time, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
import shapefile
from shapely.geometry import shape, LineString, Polygon
from shapely.ops import unary_union, transform, linemerge
from shapely import STRtree
from pyproj import Transformer
t0 = time.time()
to_ll = Transformer.from_crs(2193, 4326, always_xy=True).transform
to_tm = Transformer.from_crs(4326, 2193, always_xy=True).transform

def read(path):
    r = shapefile.Reader(path); fields = [f[0] for f in r.fields[1:]]
    return fields, [(dict(zip(fields, sr.record)), shape(sr.shape.__geo_interface__)) for sr in r.iterShapeRecords()]

_, land_recs = read(sys.argv[1])
land = unary_union([transform(to_tm, g.buffer(0)) for _, g in land_recs
                    if -47.8 < g.representative_point().y < -34 and g.representative_point().x < 179])
inland = land.buffer(-25)
print(f'land ready {time.time()-t0:.0f}s')

def lines_of(g):
    if g.is_empty: return []
    if isinstance(g, LineString): return [g]
    if hasattr(g, 'geoms'): return [x for gg in g.geoms for x in lines_of(gg)]
    return []

Q = 1e4
TOLS = [600, 120, 20]  # metres per detail level
def enc(coords):
    q = []
    for x, y in coords:
        lon, lat = to_ll(x, y); p = (round(lon * Q), round(lat * Q))
        if not q or p != q[-1]: q.append(p)
    if len(q) < 2: return None
    flat = [q[0][0], q[0][1]]
    for (x0, y0), (x1, y1) in zip(q, q[1:]): flat += [x1 - x0, y1 - y0]
    xs = [p[0] for p in q]; ys = [p[1] for p in q]
    return [min(xs), min(ys), max(xs), max(ys), flat]

out = {'q': Q, 'tols': TOLS}
for path, kind in ((sys.argv[3], 'general'),) + (((sys.argv[4], 'maori'),) if len(sys.argv) > 4 else ()):
    fields, recs = read(path)
    name_f = [f for f in fields if f.endswith('__1') or f.upper().endswith('_NAME')][0]
    els = [(rec[name_f].strip(), g.buffer(0)) for rec, g in recs]
    tree = STRtree([g for _, g in els])
    pairs = []
    for i, (na, ga) in enumerate(els):
        for j in tree.query(ga):
            if j <= i: continue
            nb, gb = els[j]
            shared = ga.boundary.intersection(gb.boundary)
            ls = lines_of(linemerge(lines_of(shared))) if not shared.is_empty else []
            if not ls: continue
            on_land = unary_union(ls).intersection(inland)
            keep = [l for l in lines_of(linemerge(lines_of(on_land))) if l.length >= 150]
            if keep: pairs.append((na, nb, keep))
    names = [n for n, _ in els]
    idx = {n: k for k, n in enumerate(names)}
    levels = []
    for tol in TOLS:
        lines = []
        for na, nb, ls in pairs:
            for l in ls:
                r = enc(l.simplify(tol).coords)
                if r: lines.append(r + [idx[na], idx[nb]])
        levels.append(lines)
        print(f'{kind} tol={tol}m: {len(lines)} lines, {sum(len(l[4]) // 2 for l in lines)} points')
    out[kind] = {'names': names, 'levels': levels}
    print(f'{kind}: {len(els)} electorates, {len(pairs)} neighbouring pairs with a land border')
s = json.dumps(out, separators=(',', ':'), ensure_ascii=False)
open(sys.argv[2], 'w').write(s); print('bytes', len(s), f'{time.time()-t0:.0f}s')
