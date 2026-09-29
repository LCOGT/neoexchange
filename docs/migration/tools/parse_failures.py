import sys, re, collections
log = open(sys.argv[1]).read().splitlines()
fails = []  # (kind, name, exc)
i = 0
while i < len(log):
    m = re.match(r'^(FAIL|ERROR): (\S+) \(([\w.]+)\)', log[i])
    if m:
        kind, test, cls = m.groups()
        j = i + 1; last = ''
        while j < len(log) and not log[j].startswith('======================================================================') and not log[j].startswith('Ran '):
            if log[j].strip() and not log[j].startswith('---') and not log[j].startswith('Traceback') and not log[j].startswith('  '):
                last = log[j].strip()
            j += 1
        fails.append((kind, test, cls, last)); i = j
    else:
        i += 1
print(f"total failing: {len(fails)}  (FAIL={sum(1 for f in fails if f[0]=='FAIL')}, ERROR={sum(1 for f in fails if f[0]=='ERROR')})")
by_exc = collections.Counter()
for k,t,c,e in fails:
    key = re.split(r'[:(]', e, 1)[0][:60] if e else '?'
    by_exc[key] += 1
print("\n--- by exception type ---")
for k,v in by_exc.most_common(15): print(f"{v:4d}  {k}")
by_cls = collections.Counter(c.rsplit('.',1)[0] if c.count('.')>2 and c.split('.')[-1]==t else c for k,t,c,e in fails)
print("\n--- by test class (top 25) ---")
for k,v in by_cls.most_common(25): print(f"{v:4d}  {k}")
print("\n--- sample messages per exception type ---")
seen = set()
for k,t,c,e in fails:
    key = re.split(r'[:(]', e, 1)[0][:60]
    if key in seen: continue
    seen.add(key); print(f"[{k}] {c}.{t}\n      {e[:230]}")
