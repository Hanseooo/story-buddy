import json,glob,os
sl=json.load(open('data/judge/freezes/obj4-v1/character_slices.json'))
m0=None
for f in sorted(glob.glob('data/judge/corpus/runs/syn-*/memory.json')):
  m=json.load(open(f,encoding='utf8')); sid=os.path.basename(os.path.dirname(f))
  if m0 is None: m0=m; print(list(m['characters'][0].keys()))
  for c in m['characters']:
    key=f"{sid}:{c.get('char_id')}"
    d=c.get('description'); sp=d.get('species') if isinstance(d,dict) else None
    print(key, sl.get(key), repr(c.get('name')), sp)
