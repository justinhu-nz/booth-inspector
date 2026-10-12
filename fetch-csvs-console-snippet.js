// Paste into Chrome DevTools console while on any page of
// https://www.electionresults.govt.nz/electionresults_2023/statistics/
// Fetches the 2023 voting-place CSVs one at a time (4s apart, ~10 min)
// and saves them as a single file: nz2023-voting-places-raw.json
(async () => {
  const base = '/electionresults_2023/statistics/csv/';
  const list = ['voting-place-coordinates.csv', 'candidate-votes-and-turnout-by-electorate.csv',
    'party-votes-and-turnout-by-electorate.csv', 'winning-electorate-candidates.csv', 'overall-results-summary.csv'];
  for (let i = 1; i <= 72; i++) list.push(`party-votes-by-voting-place-${i}.csv`, `candidate-votes-by-voting-place-${i}.csv`);
  const files = {}, failed = [];
  for (const [n, f] of list.entries()) {
    const r = await fetch(base + f); const t = await r.text();
    if (r.ok && !t.startsWith('<!DOCTYPE')) files[f] = t;
    else { failed.push(f); console.warn('Blocked on', f, '- stopping. Reload the page and re-run.'); break; }
    console.log(`${n + 1}/${list.length} ${f}`);
    await new Promise(s => setTimeout(s, 4000));
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify({ files, failed })], { type: 'application/json' }));
  a.download = 'nz2023-voting-places-raw.json'; a.click();
  console.log('Saved', Object.keys(files).length, 'files');
})();
