"""LINZ NZ Coastlines and Islands Polygons (Topo 1:50k) shapefile -> multi-level simplified coastline JSON.
Usage: python3 build/coast.py raw/linz2/<dir>/nz-coastlines-and-islands-polygons-topo-150k.shp build/nz-coast-linz.json"""
import struct, sys, json, math

def read_polys(path):
    b = open(path, 'rb').read()
    pos, rings = 100, []
    while pos < len(b):
        _, clen = struct.unpack('>ii', b[pos:pos+8]); pos += 8
        rec = b[pos:pos + clen*2]; pos += clen*2
        if struct.unpack('<i', rec[:4])[0] != 5: continue
        nparts, npts = struct.unpack('<ii', rec[36:44])
        parts = list(struct.unpack(f'<{nparts}i', rec[44:44+4*nparts])) + [npts]
        off = 44 + 4*nparts
        pts = struct.unpack(f'<{2*npts}d', rec[off:off+16*npts])
        for a, z in zip(parts[:-1], parts[1:]):
            rings.append([(pts[2*i], pts[2*i+1]) for i in range(a, z)])
    return rings

K = math.cos(math.radians(41))
def area(r):  # signed, in km^2 (approx)
    s = 0.0
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]): s += (x1*K) * y2 - (x2*K) * y1
    return s / 2 * 111.2**2

def dp(pts, eps):
    n = len(pts)
    if n < 3: return pts
    keep = [False]*n; keep[0] = keep[-1] = True
    stack = [(0, n-1)]
    while stack:
        a, z = stack.pop()
        ax, ay = pts[a][0]*K, pts[a][1]; zx, zy = pts[z][0]*K, pts[z][1]
        dx, dy = zx-ax, zy-ay; L = math.hypot(dx, dy) or 1e-12
        dmax, idx = -1, -1
        for i in range(a+1, z):
            px, py = pts[i][0]*K, pts[i][1]
            d = abs(dy*px - dx*py + zx*ay - zy*ax) / L
            if d > dmax: dmax, idx = d, i
        if dmax > eps:
            keep[idx] = True; stack += [(a, idx), (idx, z)]
    return [p for p, k in zip(pts, keep) if k]

def simplify_ring(r, eps):
    if r[0] == r[-1]: r = r[:-1]
    if len(r) < 4: return r
    # split closed ring at the point farthest from the first, so DP has two open chains
    far = max(range(len(r)), key=lambda i: (r[i][0]-r[0][0])**2 + (r[i][1]-r[0][1])**2)
    a = dp(r[:far+1], eps); b = dp(r[far:] + [r[0]], eps)
    return a[:-1] + b[:-1]

rings = read_polys(sys.argv[1])
print('rings', len(rings), 'points', sum(map(len, rings)))
# keep mainland region + Chathams; drop sub-antarctic & Kermadecs
def keep_region(r):
    x = sum(p[0] for p in r)/len(r); y = sum(p[1] for p in r)/len(r)
    return -47.8 < y < -34 and (x < 179 or 183 < x < 184.5)
rings = [r for r in rings if keep_region(r)]
A = [abs(area(r)) for r in rings]
Q = 1e4  # quantise to 1e-4 deg (~10 m)
levels = [  # (eps in "K-scaled degrees", min island area km^2)
    (0.004, 3.0),
    (0.0008, 0.15),
    (0.00015, 0.004),
]
out = []
for eps, amin in levels:
    lv = []; n = 0
    for r, a in zip(rings, A):
        if a < amin: continue
        s = simplify_ring(r, eps)
        if len(s) < 3: continue
        q = [(round(x*Q), round(y*Q)) for x, y in s]
        flat = [q[0][0], q[0][1]]
        for (x0, y0), (x1, y1) in zip(q, q[1:]): flat += [x1-x0, y1-y0]
        xs = [p[0] for p in q]; ys = [p[1] for p in q]
        lv.append([min(xs), min(ys), max(xs), max(ys), flat]); n += len(q)
    out.append({'eps': eps, 'rings': lv})
    print(f'level eps={eps}: rings {len(lv)} points {n}')
s = json.dumps({'q': Q, 'levels': out}, separators=(',', ':'))
open(sys.argv[2], 'w').write(s); print('bytes', len(s))
