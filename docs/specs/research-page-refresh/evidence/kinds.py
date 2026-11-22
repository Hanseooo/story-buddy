import json,glob,os,collections as C
sl=json.load(open('data/judge/freezes/obj4-v1/character_slices.json'))
sp={}
for f in glob.glob('data/judge/corpus/runs/syn-*/memory.json'):
  m=json.load(open(f,encoding='utf8')); sid=os.path.basename(os.path.dirname(f))
  for c in m['characters']: sp[f"{sid}:{c['char_id']}"]=c['description']['species']
rows=[json.loads(l) for l in open('data/judge/freezes/obj4-v1/manifest.jsonl',encoding='utf8') if l.strip()]
for s in ['train','val']:
  rs=[r for r in rows if r['split']==s]
  chars={r['char_id'] for r in rs}
  kind=lambda c: 'human' if sp[c]=='human' else 'non_human'
  print(s,'by species chars',C.Counter(kind(c) for c in chars),'pairs',C.Counter(kind(r['char_id']) for r in rs))
  print(s,'by slices chars',C.Counter(sl[c] for c in chars),'pairs',C.Counter(sl[r['char_id']] for r in rs))
  print(' mismatched',sorted((c,sp[c]) for c in chars if kind(c)!=sl[c]))
