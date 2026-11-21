import sys,re,html,base64,zlib,urllib.parse,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8")
for p in sys.argv[1:]:
    s=open(p,encoding='utf8').read()
    m=re.search(r'content="([^"]*)"',s)
    mx=html.unescape(m.group(1))
    root=ET.fromstring(mx)
    for d in root.iter('diagram'):
        print('=== ',p,d.get('name'))
        txt=(d.text or '').strip()
        if txt:
            raw=zlib.decompress(base64.b64decode(txt),-15).decode()
            xml=urllib.parse.unquote(raw)
            g=ET.fromstring(xml)
        else:
            g=d.find('mxGraphModel')
        cells={c.get('id'):c for c in g.iter('mxCell')}
        def lab(i):
            c=cells.get(i); 
            return re.sub('<[^>]+>',' ',html.unescape(c.get('value') or '')).strip() if c is not None else i
        for c in g.iter('mxCell'):
            if c.get('vertex')=='1':
                print('V',c.get('id'),'|',lab(c.get('id')))
        for c in g.iter('mxCell'):
            if c.get('edge')=='1':
                print('E',lab(c.get('source')),'->',lab(c.get('target')),'|',lab(c.get('id')))
