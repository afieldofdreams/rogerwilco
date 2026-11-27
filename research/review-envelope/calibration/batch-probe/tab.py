import json,sys,collections
rows=[json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
cells=collections.defaultdict(lambda: collections.Counter())
meta=collections.defaultdict(list)
for r in rows:
    k=(r['layout'],r['n'],r['model'],'F' if r['faulted'] else 'C')
    cells[k][r['outcome']]+=1
    meta[k].append((r.get('chars') or 0, r.get('seconds') or 0, r.get('cost') or 0))
for k in sorted(cells):
    m=meta[k]; n=len(m)
    print(f"{k[0]:9} n={k[1]:<3} {k[2]:9} {k[3]}  {dict(cells[k])}  chars~{sum(x[0] for x in m)//n} sec~{sum(x[1] for x in m)/n:.1f} cost~${sum(x[2] for x in m)/n:.4f}")
print(len(rows),'rows')
