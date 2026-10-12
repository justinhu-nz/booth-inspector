# Booth Inspector

Interactive map of every voting place in New Zealand's 2023 general election.

Open `index.html` in a browser. All data is inlined, so it works offline (fonts fall back if offline).

## Rebuild

    python3 build/parse.py                      # csvpv/ + raw/ + evenmore/csv-splitvote → build/booths.compact.json
    python3 build/coast.py raw/linz2/lds-nz-coastlines-and-islands-polygons-topo-150k-SHP/nz-coastlines-and-islands-polygons-topo-150k.shp build/nz-coast-linz.json
    pip install shapely pyshp pyproj   # once, for the boundary step
    python3 build/bounds.py raw/linz2/lds-nz-coastlines-and-islands-polygons-topo-150k-SHP/nz-coastlines-and-islands-polygons-topo-150k.shp build/bounds.json raw/statsnz/general-electorates-2020.shp [raw/statsnz/maori-electorates-2020.shp]
    python3 build/make.py build/index.template.html build/booths.compact.json build/nz-coast-linz.json index.html

## Sources
- Electoral Commission, 2023 General Election official results: votes recorded at each voting place (csvpv/),
  split-vote reports (evenmore/csv-splitvote/), voting place coordinates (raw/voting-place-coordinates.csv, approximate).
- Electorate boundaries: Stats NZ General Electorates 2020 (the boundaries used at the 2023 election), CC BY 4.0. Clipped to land 25 m inside the LINZ coastline by build/bounds.py so borders don't run out to sea; only borders shared by two electorates are drawn.
- Coastline: LINZ NZ Coastlines and Islands Polygons (Topo 1:50k), CC BY 4.0, simplified to three zoom levels by build/coast.py (build/nz-coast-linz.json).

## Notes
- Advance voting places take votes from many electorates. On the national map each place's party vote is summed across every electorate file.
- Special, overseas and mobile-team votes have no fixed location and stay off the map (about 21% of party votes nationally).
- The coordinates file lists places only under general electorates. Māori electorate views show every place where Māori roll voters voted.
- Port Waikato: electorate poll cancelled (by-election 25 Nov 2023). Tāmaki Makaurau: official count majority 42, later 4 after a judicial recount.
- "Bloc lean" = (National + ACT + NZ First − Labour − Green − Te Pāti Māori) ÷ those six parties' combined vote.
- Party colours follow NZ convention. Labour red and Green green are hard to tell apart for some colour-blind readers, so bars carry labels and tooltips, and Bloc lean (red–blue) is the default map mode.

## Street map (local copy only)
`index.html` loads CARTO raster basemaps via Leaflet. CARTO now requires an API key: it lives in `carto-key.js` (git-ignored) as `window.BI_CARTO_KEY = '...'`. Without it the tiles show CARTO's watermark. The published artifact can't load outside tiles, so it keeps the drawn LINZ coastline.
