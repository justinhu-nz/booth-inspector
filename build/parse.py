"""Parse 2023 NZ voting-place CSVs into one compact JSON for the Booth Inspector page.
Usage: python3 build/parse.py   (run from booth-inspector/)"""
import csv, io, json, re, sys
from collections import Counter

def read(path):
    return list(csv.reader(io.StringIO(open(path, encoding='utf-8-sig').read())))

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def num(x):
    x = x.strip().replace(',', '')
    return int(x) if x else 0

# ---- coordinates: global place lookup ----
coords = read('raw/voting-place-coordinates.csv')[1:]
places, pkey = [], {}
for e, ename, pid, typ, sub, addr, lon, lat, *_ in coords:
    k = norm(sub) + '|' + norm(addr)
    if k in pkey:
        continue
    pkey[k] = len(places)
    places.append({'id': int(pid), 'sub': sub.strip(), 'addr': addr.strip(),
                   'lat': round(float(lat), 5), 'lon': round(float(lon), 5),
                   'e': int(e), 'adv': typ == 'Advance'})
addr_only = Counter(norm(p['addr']) for p in places)
akey = {norm(p['addr']): i for i, p in enumerate(places) if addr_only[norm(p['addr'])] == 1}

def find_place(sub, addr):
    k = norm(sub) + '|' + norm(addr)
    if k in pkey: return pkey[k]
    return akey.get(norm(addr), -1)

def parse_file(path, kind):
    rows = read(path)
    title = rows[1][0].replace('\n', ' ')
    m = re.match(r'(.+?)\s+(\d+)', title)
    name, eid = m.group(1).strip(), int(m.group(2))
    header = [h.strip() for h in rows[2][2:]]
    ncols = len(header) - 2          # last two = total valid, informal
    out, section, last_sub, total, mapping = [], None, '', None, {}
    i = 3
    while i < len(rows):
        r = rows[i]
        if not r or all(not c.strip() for c in r):
            i += 1; continue
        c0 = r[0].strip()
        if c0 in ('Advance Voting Places', 'Voting Places'):
            section = 'A' if c0.startswith('Adv') else 'E'; last_sub = ''
        elif c0.startswith('Electorate ') and 'Valid Votes' in c0:
            # summary block: for candidate files, gives candidate -> party
            for rr in rows[i+1:]:
                if len(rr) >= 2 and rr[0].strip():
                    mapping[rr[0].strip()] = rr[1].strip()
            break
        elif len(r) > 2 and (c0 or r[1].startswith(' ') is False) and section and r[1].strip() and not r[1].startswith(('Overseas', 'Special Votes', 'Votes Allowed', 'Voting places where', name + ' Total', 'Valid ')) and c0 != '':
            last_sub = c0
            out.append(['booth', section, last_sub, r[1].strip(), [num(x) for x in r[2:2+ncols]], num(r[2+ncols]), num(r[3+ncols]) if len(r) > 3+ncols else 0])
        elif c0 == '' and len(r) > 2 and r[1].strip():
            lab = r[1].strip()
            vals = [num(x) for x in r[2:2+ncols]]
            if lab == name + ' Total' or lab.endswith(' Total'):
                total = (vals, num(r[2+ncols]), num(r[3+ncols]) if len(r) > 3+ncols else 0)
            elif lab.startswith('Valid '):
                pass
            elif lab.startswith(('Overseas', 'Special Votes', 'Votes Allowed', 'Voting places where')):
                out.append(['other', None, '', re.sub(r'\s+-\s+' + re.escape(name) + r'$', '', lab), vals, num(r[2+ncols]), num(r[3+ncols]) if len(r) > 3+ncols else 0])
            elif section:
                out.append(['booth', section, last_sub, lab, vals, num(r[2+ncols]), num(r[3+ncols]) if len(r) > 3+ncols else 0])
        i += 1
    return dict(eid=eid, name=name, title=title, header=header[:ncols], rows=out, total=total, mapping=mapping)

electorates, parties, problems = [], None, []
for eid in range(1, 73):
    P = parse_file(f'csvpv/party-votes-by-voting-place-{eid}.csv', 'party')
    C = parse_file(f'csvpv/candidate-votes-by-voting-place-{eid}.csv', 'cand')
    hdr = [h.strip() for h in P['header']]
    if parties is None: parties = hdr
    assert hdr == parties, (eid, hdr)
    # checks: rows sum to total
    for lbl, X in (('party', P), ('cand', C)):
        s = [sum(r[4][j] for r in X['rows']) for j in range(len(X['header']))]
        if X['total'] and s != X['total'][0]:
            problems.append((eid, lbl, 'sum mismatch', sum(s), sum(X['total'][0])))
    # align candidate rows to party rows by (section, sub, addr / label)
    ck = {}
    for r in C['rows']: ck[(r[0], r[1], norm(r[2]), norm(r[3]))] = r
    rows = []
    for r in P['rows']:
        kind, sec, sub, lab, pv, pvalid, pinf = r
        c = ck.get((kind, sec, norm(sub), norm(lab)))
        if c is None and kind == 'other' and 'Party Only' not in lab:
            problems.append((eid, 'no cand row', lab))
        place = find_place(sub, lab) if kind == 'booth' else -1
        if kind == 'booth' and place < 0:
            problems.append((eid, 'no coords', sub, lab))
        rows.append({'k': sec if kind == 'booth' else 'S', 'p': place,
                     'l': lab if kind != 'booth' else None,
                     'sub': sub if (kind == 'booth' and place < 0) else None,
                     'pv': pv, 'pi': pinf,
                     'cv': c[4] if c else None, 'ci': c[6] if c else None})
    cands = []
    for cn in C['header']:
        party = C['mapping'].get(cn, '')
        cands.append({'n': cn, 'party': party.strip()})
    electorates.append({'id': eid, 'name': P['name'], 'maori': eid >= 66,
                        'cancelled': 'Poll Cancelled' in C['title'],
                        'cands': cands, 'rows': rows})

# compact: drop None keys
for e in electorates:
    e['rows'] = [{k: v for k, v in r.items() if v is not None} for r in e['rows']]

data = {'source': 'Electoral Commission, 2023 General Election official results — votes recorded at each voting place; voting place coordinates (approximate).',
        'parties': parties, 'places': places, 'electorates': electorates}
json.dump(data, open('build/booths.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('parties', len(parties), parties)
print('places', len(places), 'electorates', len(electorates))
print('rows', sum(len(e['rows']) for e in electorates))
print('problems', len(problems))
for p in problems:
    if p[1] != 'no coords' or not p[2].startswith('Taken in'): print('  ', p)
print('no-coord rows', sum(1 for p in problems if p[1]=='no coords'))

# ---- split-vote matrices (electorate level) + compact export for the page ----
def split_for(eid, cands):
    rows = read(f'evenmore/csv-splitvote/split-votes-electorate-{eid}.csv')
    cols = [c.strip() for c in rows[0][2:]]
    names = [c['n'] for c in cands]
    col_idx = []
    for c in cols:
        hit = [i for i, n in enumerate(names) if c.startswith(n + ' (')]
        col_idx.append(hit[0] if hit else c)   # int = candidate index, str = special column
    out = []
    for r in rows[1:]:
        if len(r) < 3 or not r[0].strip(): continue
        out.append([r[0].strip(), num(r[1])] + [float(x) if x.strip() else 0.0 for x in r[2:2+len(cols)]])
    return {'cols': col_idx, 'rows': out}

compact = {
    'parties': parties,
    'places': [[p['lat'], p['lon'], p['sub'], p['addr'], p['e'], 1 if p['adv'] else 0] for p in places],
    'electorates': [],
}
for e in electorates:
    rows = []
    for r in e['rows']:
        rows.append([r['k'], r['p'], r.get('l') or r.get('sub') or '', r['pv'], r['pi'], r.get('cv'), r.get('ci')])
    compact['electorates'].append({
        'id': e['id'], 'name': e['name'], 'maori': e['maori'], 'cancelled': e['cancelled'],
        'cands': [[c['n'], c['party']] for c in e['cands']], 'rows': rows,
        'split': split_for(e['id'], e['cands'])})
s = json.dumps(compact, ensure_ascii=False, separators=(',', ':'))
open('build/booths.compact.json', 'w', encoding='utf-8').write(s)
print('compact bytes', len(s.encode()))
bad = [(e['name'], c) for e in compact['electorates'] for c in e['split']['cols'] if isinstance(c, str)]
print('split special cols', sorted(set(c for _, c in bad)))
