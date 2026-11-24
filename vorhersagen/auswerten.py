#!/usr/bin/env python3
"""Wertet vorhersagen.csv aus: offene, fällige und aufgelöste Vorhersagen, Brier-Score.

ergebnis: 1 = eingetreten, 0 = nicht eingetreten, leer = offen.
Brier-Score: Mittel von (p - ergebnis)^2. 0 ist perfekt, 0.25 erreicht man
mit p = 0.5 bei allem. Aufruf: python3 auswerten.py [datum JJJJ-MM-TT]
"""
import csv, sys, datetime, pathlib

heute = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
zeilen = list(csv.DictReader(open(pathlib.Path(__file__).with_name("vorhersagen.csv"), encoding="utf-8")))
aufgeloest = [z for z in zeilen if z["ergebnis"].strip() in ("0", "1")]
offen = [z for z in zeilen if z not in aufgeloest]
faellig = [z for z in offen if z["faellig"] <= heute]

print(f"{len(zeilen)} Vorhersagen: {len(aufgeloest)} aufgelöst, {len(offen)} offen, davon {len(faellig)} fällig ({heute}).")
for z in faellig:
    print(f"  fällig #{z['id']}: {z['frage']}  -> {z['quelle']}")
if aufgeloest:
    brier = sum((float(z["p"]) - int(z["ergebnis"])) ** 2 for z in aufgeloest) / len(aufgeloest)
    print(f"Brier-Score: {brier:.3f} (n={len(aufgeloest)})")
    for lo, hi in ((0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
        b = [z for z in aufgeloest if lo <= float(z["p"]) < hi]
        if b:
            print(f"  p {lo:.1f}–{min(hi,1):.1f}: {sum(int(z['ergebnis']) for z in b)}/{len(b)} eingetreten")
