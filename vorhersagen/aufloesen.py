#!/usr/bin/env python3
"""Schlägt für jede Vorhersage ein Ergebnis vor, indem es die Quelle selbst abfragt.

Warum: Die Auflösung soll nicht von meinem Urteil am Tag X abhängen, sondern von
einer Regel, die vor dem Ergebnis feststand und die jeder nachrechnen kann.
Die Prüfungen hier sind am 26.11.2026 geschrieben, bevor eine davon fällig war.

Das Skript schreibt nichts. Es gibt pro Vorhersage aus: 1, 0, oder "offen"
(noch nicht entscheidbar), dazu den gemessenen Wert. Ins `ergebnis` der CSV
trage ich den Vorschlag von Hand ein; weiche ich ab, steht der Grund im Logbuch.

Aufruf: python3 aufloesen.py [id ...]     (ohne id: alle fälligen)
        python3 aufloesen.py --alle       (auch nicht fällige, zum Testen)
"""
import csv, datetime, io, json, pathlib, re, sys, urllib.request

HEUTE = datetime.date.today().isoformat()


def holen(url):
    req = urllib.request.Request(url, headers={"User-Agent": "vorhersagen-aufloesen"})
    return urllib.request.urlopen(req, timeout=60).read()


def snb_leitzins(ab):
    """Erster Leitzins-Wert (LZ) an oder nach dem Datum `ab`."""
    text = holen("https://data.snb.ch/api/cube/snbgwdzid/data/csv/de").decode("utf-8-sig")
    werte = [(d, v) for d, k, v in re.findall(r'"([\d-]+)";"([A-Z]+)";"([^"]*)"', text) if k == "LZ" and d >= ab]
    return (werte[0][1], werte[0][0]) if werte else (None, None)


def ezb_letzter_kurs(bis):
    """Letzter EZB-Referenzkurs EUR/CHF bis und mit `bis`."""
    url = f"https://data-api.ecb.europa.eu/service/data/EXR/D.CHF.EUR.SP00.A?endPeriod={bis}&lastNObservations=1&format=csvdata"
    z = next(csv.DictReader(io.StringIO(holen(url).decode())))
    return float(z["OBS_VALUE"]), z["TIME_PERIOD"]


def meteo_monat(spalte, monat):
    """Monatswert Zürich-Fluntern (SMA); `monat` als 01.MM.JJJJ."""
    text = holen("https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/sma/ogd-smn_sma_m.csv").decode("latin-1")
    for z in csv.DictReader(io.StringIO(text), delimiter=";"):
        if z["reference_timestamp"].startswith(monat) and z[spalte].strip():
            return float(z[spalte])
    return None


def p1():
    if HEUTE < "2026-12-11":
        return "offen", "Lagebeurteilung noch nicht vorbei"
    v, d = snb_leitzins("2026-12-11")
    if v is None:
        return "offen", "noch kein Wert ab 11.12."
    return (1 if float(v) == 0 else 0), f"LZ {v} am {d}"


def eurchf(grenze):
    def pruefen():
        if HEUTE <= "2026-12-31":
            return "offen", "Jahr noch nicht vorbei"
        kurs, d = ezb_letzter_kurs("2026-12-31")
        return (1 if kurs < grenze else 0), f"{kurs} am {d}"
    return pruefen


def p4():
    url = "https://api.github.com/search/issues?q=repo:omkai/dreimal-taeglich+is:issue+created:%3C2027-01-01"
    n = json.loads(holen(url))["total_count"]
    if n > 0:
        return 1, f"{n} Issues"
    return ("offen" if HEUTE <= "2026-12-31" else 0), "0 Issues"


def p5():
    # Final, nicht rc: das Tarball linux-7.4.tar.xz mit Datum bis 31.12.2026.
    html = holen("https://cdn.kernel.org/pub/linux/kernel/v7.x/").decode()
    m = re.search(r'linux-7\.4\.tar\.xz</a>\s+(\d\d-\w{3}-\d{4})', html)
    if m:
        d = datetime.datetime.strptime(m.group(1), "%d-%b-%Y").date().isoformat()
        return (1 if d <= "2026-12-31" else 0), f"7.4 am {d}"
    return ("offen" if HEUTE <= "2026-12-31" else 0), "7.4 nicht veröffentlicht"


def meteo(spalte, ja):
    def pruefen():
        v = meteo_monat(spalte, "01.12.2026")
        if v is None:
            return "offen", "Dezember noch nicht in den Daten"
        return (1 if ja(v) else 0), f"{spalte} = {v}"
    return pruefen


def p8():
    B = "https://ws.parlament.ch/odata.svc/"
    get = lambda p: json.loads(holen(B + p))["d"]["results"]
    bills = get("Bill?$filter=Language%20eq%20'DE'%20and%20BusinessNumber%20eq%2020260041&$select=ID&$format=json")
    treffer = []
    for bl in bills:
        for r in get(f"Resolution?$filter=Language%20eq%20'DE'%20and%20IdBill%20eq%20guid'{bl['ID']}'"
                     "&$select=ResolutionText,ResolutionDate&$format=json"):
            if "Einigungskonferenz" in (r["ResolutionText"] or ""):
                ms = re.search(r"\d+", r["ResolutionDate"] or "")
                d = datetime.datetime.fromtimestamp(int(ms.group()) / 1000, datetime.timezone.utc).date().isoformat() if ms else "?"
                if d <= "2026-12-31":
                    treffer.append(d)
    if treffer:
        return 1, f"{len(treffer)} Beschlüsse, erster {min(treffer)}"
    return ("offen" if HEUTE <= "2026-12-31" else 0), "kein Beschluss zur Einigungskonferenz"


def p9():
    if HEUTE < "2027-01-01":
        return "offen", "Dezember noch nicht vorbei"
    url = ("https://ll.thespacedevs.com/2.2.0/launch/previous/?limit=1&mode=list&include_suborbital=false"
           "&net__gte=2026-12-01T00:00:00Z&net__lt=2027-01-01T00:00:00Z")
    n = json.loads(holen(url))["count"]
    return (1 if n >= 25 else 0), f"{n} Starts"


def p10():
    if HEUTE < "2027-01-05":
        return "offen", "Stichtag 5.1.2027"
    m = re.search(r"Total of ([\d,]+) entries", holen("https://arxiv.org/list/cs.AI/2026-12").decode())
    n = int(m.group(1).replace(",", ""))
    return (1 if n >= 6000 else 0), f"{n} Einträge"


def p11():
    if HEUTE < "2026-12-21":
        return "offen", "Winterpause noch nicht erreicht"
    if HEUTE > "2027-01-07":
        return "offen", "Fenster vorbei: Tabelle zeigt nicht mehr Spieltag 14, von Hand prüfen"
    t = json.loads(holen("https://api.openligadb.de/getbltable/bl1/2026"))
    if t[0]["matches"] != 14:
        return "offen", f"Tabelle nach {t[0]['matches']} Spielen, nicht 14"
    return (1 if t[0]["teamName"] == "FC Bayern München" else 0), f"Erster: {t[0]['teamName']}, {t[0]['points']} Punkte"


PRUEFUNGEN = {
    "1": p1, "2": eurchf(0.93), "3": eurchf(0.91), "4": p4, "5": p5,
    "6": meteo("tre200m0", lambda v: v > 2.0), "7": meteo("rre150m0", lambda v: v >= 50),
    "8": p8, "9": p9, "10": p10, "11": p11,
}

with open(pathlib.Path(__file__).with_name("vorhersagen.csv"), encoding="utf-8") as f:
    zeilen = list(csv.DictReader(f))
args = [a for a in sys.argv[1:] if a != "--alle"]
for z in zeilen:
    if z["ergebnis"].strip():
        continue
    if args and z["id"] not in args:
        continue
    if not args and "--alle" not in sys.argv and z["faellig"] > HEUTE:
        continue
    pruefen = PRUEFUNGEN.get(z["id"])
    if pruefen is None:
        print(f"#{z['id']}: keine Prüfung hinterlegt, von Hand auflösen")
        continue
    try:
        ergebnis, wert = pruefen()
    except Exception as e:  # Quelle weg oder anders: nicht raten
        ergebnis, wert = "fehler", repr(e)[:120]
    print(f"#{z['id']}: {ergebnis}  ({wert})")
