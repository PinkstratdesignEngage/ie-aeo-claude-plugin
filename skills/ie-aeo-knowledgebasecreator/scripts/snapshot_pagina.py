#!/usr/bin/env python3
"""Salva una copia di testo di una pagina web nella cartella raw/ della knowledge base.

Uso: python3 -I snapshot_pagina.py <url> <file-di-destinazione.md> [--non-analizzato]

Il file contiene titolo, URL, data di salvataggio e stato (analizzato o no),
seguiti dal testo della pagina senza script, stili e markup. Restano fuori anche
intestazione, menu e piè di pagina (<header>, <nav>, <footer>) e i moduli (<form>,
<dialog>): si ripetono uguali in ogni pagina e nell'indice di ricerca sono solo rumore.
Il testo alternativo delle immagini resta, come [immagine: ...]: nelle pagine prodotto
ci sono dati come le classi energetiche. Si scartano gli alt vuoti e quelli che sono
solo nomi di file.
"""
import sys, re, html, subprocess, datetime
from html.parser import HTMLParser
NOME_FILE=re.compile(r"(\.(png|jpe?g|gif|webp|svg)$|^(img|image|dsc|location)[\s_\-]*[\(\d])",re.I)
SALTA=("script","style","noscript","svg","header","nav","footer","form","dialog")
class T(HTMLParser):
    def __init__(s): super().__init__(); s.out=[]; s.skip=0; s.title=""; s.intitle=False
    def handle_starttag(s,t,a):
        if t in SALTA: s.skip+=1
        if t=="title": s.intitle=True
        if t=="img" and not s.skip:
            alt=re.sub(r"\s+"," ",dict(a).get("alt") or "").strip()
            if alt and not NOME_FILE.search(alt): s.out.append(f" [immagine: {alt}] ")
        if t in("p","div","li","h1","h2","h3","h4","br","tr","section"): s.out.append("\n")
        if t in("h1","h2","h3"): s.out.append("#"*int(t[1])+" ")
        if t=="li": s.out.append("- ")
    def handle_endtag(s,t):
        if t in SALTA: s.skip=max(0,s.skip-1)
        if t=="title": s.intitle=False
    def handle_data(s,d):
        if s.intitle: s.title+=d
        if not s.skip: s.out.append(d)
args=[a for a in sys.argv[1:] if not a.startswith("--")]
if len(args)!=2:
    print(__doc__); sys.exit(2)
url,dest=args[0],args[1]
stato="non analizzato" if "--non-analizzato" in sys.argv else "analizzato"
oggi=datetime.date.today().isoformat()
raw=subprocess.run(["curl","-sL","--max-time","40",url],capture_output=True).stdout.decode("utf-8","replace")
p=T(); p.feed(raw)
txt=re.sub(r"[ \t]+"," ","".join(p.out)); txt=re.sub(r"^ ?- ?$","",txt,flags=re.M)  # voci di elenco vuote
txt=re.sub(r"\n\s*\n+","\n\n",txt).strip()
open(dest,"w").write(f"# {html.unescape(p.title.strip())}\n\n- URL: {url}\n- Copia di testo salvata il {oggi}\n- Stato: {stato}\n\n---\n\n{html.unescape(txt)}\n")
print(len(txt))
