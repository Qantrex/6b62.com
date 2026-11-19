#!/usr/bin/env python3
"""websites.py: build the trade pages /websites/<trade>/ from /websites/.

site/websites/index.html is the hand-edited source. Each trade page takes from it, unchanged:
the CSS, the favicon, the free-draft box and buttons of the hero, that trade's example (list, price
table, notes), and the shared sections (base package, process, who, comparison, extras, terms,
reference, contact, footer). Only the top of each page is the trade's own: its problem, the
example's price, and a few trade questions (TRADES below). Prices on the trade pages are read from
the example tables in index.html, so they can't drift from /websites/.

  ./websites.py          write site/websites/<trade>/index.html
  ./websites.py --check  exit 1 if a written page differs from what the source builds
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "site/websites/index.html"
SHARED = ["angebot", "ablauf", "wer", "vergleich", "extras", "fair", "ref", "kontakt"]
WA_ANY = "f%C3%BCr%20meinen%20Betrieb%3A%20"

TRADES = [
    {
        "slug": "friseur",
        "label": "Websites für Salons",
        "title": "Websites für Friseur, Barber, Kosmetik und Nagelstudio · Konstantin Bauer",
        "og_title": "Websites für Friseur, Kosmetik und Nagelstudio",
        "desc": "Eine Website, über die Ihre Kunden selbst einen Termin buchen. Ab {base_once} einmalig und {base_month} im Monat, mit Online-Buchung wie im Beispiel {once} einmalig. Von Konstantin Bauer, Wien.",
        "eyebrow": "Für Friseur, Barber, Kosmetik und Nagelstudio",
        "h1": "Ihre Kunden buchen selbst, während Sie schneiden",
        "lead": "Das Telefon läutet mitten im Haarschnitt, und abends beantworten Sie Terminfragen auf Instagram und WhatsApp. Auf Ihrer eigenen Seite sehen Kunden Preise und Öffnungszeiten und buchen einen freien Termin selbst, auch abends und am Sonntag.",
        "ex_with": "mit Online-Terminbuchung und Google-Eintrag",
        "wa": "f%C3%BCr%20meinen%20Salon%3A%20",
        "ex_h2": "Was es für einen Salon kostet",
        "faq_h2": "Gut zu wissen für Salons",
        "faq": [
            ("Ich habe doch Instagram.", "Instagram bleibt, und die Seite zeigt es. Dazu kommt, was auf Instagram schwer zu finden ist: Preise, Öffnungszeiten, Adresse und ein Knopf zum Buchen. Wer Sie auf Google sucht, landet direkt dort."),
            ("Was kostet das Buchungsprogramm?", "Sie zahlen es direkt an den Anbieter: für eine Person oft gratis bis 50 Termine im Monat, sonst etwa 10 €. Welche Leistungen wie lange dauern und wann Sie frei haben, legen Sie selbst fest."),
            ("Ich habe schon eine Seite bei Wix oder Jimdo.", "Den Umzug mache ich für 150–300 €, Ihre Adresse bleibt. Danach zahlen Sie den Baukasten nicht mehr."),
            ("Ich verpasse trotzdem viele Anrufe.", "Dafür gibt es optional einen Telefonassistenten, der abhebt, während Sie schneiden: 290 € einmalig und ab 99 € im Monat beim Anbieter. Ich empfehle ihn nur, wenn Sie wirklich viele Anrufe verpassen."),
        ],
    },
    {
        "slug": "werkstatt",
        "label": "Websites für Werkstätten",
        "title": "Websites für Kfz-Werkstätten und Reifenhändler · Konstantin Bauer",
        "og_title": "Websites für Kfz-Werkstätten und Reifenhändler",
        "desc": "Kunden buchen Pickerl, Service oder Reifenwechsel selbst online. Ab {base_once} einmalig und {base_month} im Monat, mit Online-Buchung wie im Beispiel {once} einmalig. Von Konstantin Bauer, Wien.",
        "eyebrow": "Für Kfz-Werkstätten und Reifenhändler",
        "h1": "Pickerl und Reifenwechsel online buchen, statt anzurufen",
        "lead": "Das Telefon läutet, während Sie unter dem Auto liegen, und zum Reifenwechsel im Frühjahr und Herbst rufen alle gleichzeitig an. Auf Ihrer Seite wählen Kunden Pickerl, Service oder Reifenwechsel und buchen einen freien Termin selbst. Wer lieber anruft, erreicht Sie am Handy mit einem Tipp.",
        "ex_with": "mit eigenen Seiten für Pickerl und Reifen und Online-Terminbuchung",
        "wa": "f%C3%BCr%20meine%20Werkstatt%3A%20",
        "ex_h2": "Was es für eine Werkstatt kostet",
        "faq_h2": "Gut zu wissen für Werkstätten",
        "faq": [
            ("Warum eigene Seiten für Pickerl und Reifen?", "Wer in Ihrer Gegend nach Pickerl oder Reifenwechsel sucht, soll eine Seite finden, die genau davon handelt. Eine bestimmte Platzierung bei Google garantiere ich nicht, das kann niemand seriös."),
            ("Bestimme ich, wann gebucht werden kann?", "Ja. Sie legen Zeiten und Dauer pro Leistung fest. Buchungen kommen per E-Mail und im Kalender an, und das Buchungsprogramm zahlen Sie direkt an den Anbieter, etwa 10 € im Monat."),
            ("Unsere alte Seite ist am Handy kaum lesbar.", "Ich ersetze sie, und Links, die Google schon kennt, führen weiter auf die richtige Seite. Das kostet einmalig 150–300 €, dazu kommt der Preis der neuen Seite."),
            ("Und wer hebt ab, wenn ich arbeite?", "Optional ein Telefonassistent: 390 € einmalig und ab 99 € im Monat beim Anbieter. Er ist nicht im Preis oben."),
        ],
    },
    {
        "slug": "handwerk",
        "label": "Websites fürs Handwerk",
        "title": "Websites für Installateure, Elektriker und Handwerk · Konstantin Bauer",
        "og_title": "Websites für Installateure, Elektriker und Handwerk",
        "desc": "Notdienst-Nummer ganz oben, Einsatzgebiet, Fotos fertiger Arbeiten. Ab {base_once} einmalig und {base_month} im Monat, mit Galerie und Foto-Formular wie im Beispiel {once} einmalig. Von Konstantin Bauer, Wien.",
        "eyebrow": "Für Installateure, Elektriker und andere Handwerksbetriebe",
        "h1": "Wer einen Notfall hat, findet Ihre Nummer sofort",
        "lead": "Bei einem Rohrbruch oder Stromausfall sucht man am Handy und will sofort jemanden erreichen. Auf Ihrer Seite steht die Notdienst-Nummer ganz oben, dazu Einsatzgebiet, Leistungen und Fotos fertiger Arbeiten. Kunden schicken Ihnen ein Foto vom Schaden, bevor Sie hinfahren.",
        "ex_with": "mit Galerie, Foto-Formular und Google-Eintrag",
        "wa": WA_ANY,
        "ex_h2": "Was es für einen Handwerksbetrieb kostet",
        "faq_h2": "Gut zu wissen für Handwerksbetriebe",
        "faq": [
            ("Unsere Domain ist abgelaufen.", "Ich prüfe gratis, ob sie noch zu haben ist. Die Domain läuft auf Ihren Namen, und die jährliche Verlängerung erledige und zahle ich, damit sie nicht wieder unbemerkt abläuft."),
            ("Die Notdienst-Nummer ändert sich.", "Dringendes wie eine neue Notdienst-Nummer ändere ich meist am selben oder nächsten Tag. Das ist im Monatsbetrag inklusive."),
            ("Wir haben keine Zeit für Texte.", "Sie schicken mir Ihre Leistungen, Ihr Einsatzgebiet und ein paar Fotos fertiger Arbeiten, den Rest mache ich. Texte schreibe ich auf Wunsch für 50 € pro Seite, Sie geben sie frei."),
            ("Steht der Notdienst auch bei Google?", "Ja. Ich stelle Ihren Google-Eintrag richtig, er zeigt die Notdienst-Nummer, und Anrufer kommen mit einem Tipp durch. Das ist im Beispiel oben schon drin."),
        ],
    },
]

EXTRA_CSS = """
/* trade pages (websites.py) */
.excase{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:14px;}
.excase .bd{margin-top:0;}
@media (max-width:760px){.excase{grid-template-columns:1fr;}}
.trades-line .here{color:var(--ink-2);}
"""


def one(pattern, s, what):
    m = re.findall(pattern, s, re.S)
    if len(m) != 1:
        sys.exit(f"websites.py: expected exactly one {what} in {SRC.relative_to(ROOT)}, found {len(m)}")
    return m[0]


def source():
    s = SRC.read_text(encoding="utf-8")
    src = {
        "head_meta": one(r'(<meta name="color-scheme".*?<meta name="theme-color" content="#0b0c0e"[^>]*>)\n', s, "colour metas"),
        "icon": one(r'(<link rel="icon" href="data:[^"]+">)', s, "favicon"),
        "css": one(r"<style>\n(.*?)</style>", s, "style block"),
        "hero": one(r'(<section class="hero".*?</section>)', s, "hero"),
        "beispiele": one(r'(<section id="beispiele".*?</section>)', s, "examples section"),
        "footer": one(r"(<footer>.*?</footer>)", s, "footer"),
        "sections": {},
    }
    src["free"] = one(r'(<p class="free">.*?</p>)', src["hero"], "free-draft box")
    src["btns"] = one(r'(<div class="btns">.*?</div>)', src["hero"], "hero buttons")
    src["terms_tail"] = one(r'<p class="small">Im ersten Jahr [^.]+\. (Mindestlaufzeit[^<]+)</p>', src["hero"], "terms in the hero")
    src["base"] = one(r'<p class="price">Grundseite: <b>([^<]+)</b> einmalig, dann <b>([^<]+)</b> im Monat</p>', src["hero"], "base price")
    src["base_year"] = one(r'<p class="small">Im ersten Jahr ([^ ]+ €)', src["hero"], "base first-year total")
    src["note"] = one(r'(<p class="note">Sie zahlen nur.*?</p>)', src["beispiele"], "examples note")
    src["mid"] = one(r'(<div class="btns mid">.*?</div>)', src["beispiele"], "examples button")
    for key in SHARED:
        src["sections"][key] = one(rf'(<section[^>]*aria-labelledby="h-{key}">.*?</section>)', s, f"section h-{key}")
    for t in TRADES:
        art = one(rf'<article class="part" id="{t["slug"]}">(.*?)</article>', src["beispiele"], f'example #{t["slug"]}')
        row = lambda name: html.unescape(one(rf'<th scope="row">{name}</th><td class="r">([^<]+)</td>', art, f'"{name}" row in #{t["slug"]}'))
        t["src"] = {
            "ul": one(r"(<ul>.*?</ul>)", art, f'list in #{t["slug"]}'),
            "table": one(r'(<table class="bd">.*?</table>)', art, f'table in #{t["slug"]}'),
            "ex": re.findall(r'(<p class="ex(?: opt)?">.*?</p>)', art, re.S),
            "once": row("Einmalig"), "month": row("Dann im Monat"), "year": row("Im ersten Jahr"),
        }
    return src


def nb(s):
    """Keep amounts on one line: '360 €' never breaks before the euro sign."""
    return s.replace(" €", "&nbsp;€")


def wa(s, t):
    return s.replace(WA_ANY, t["wa"])


def page(t, src):
    e = lambda x: html.escape(x, quote=True)
    x = t["src"]
    base_once, base_month = src["base"]
    others = " · ".join(
        f'<a href="/websites/{o["slug"]}/">{o["eyebrow"].removeprefix("Für ")}</a>' for o in TRADES if o is not t)
    faq = "\n".join(f"    <li><b>{e(q)}</b> {nb(e(a))}</li>" for q, a in t["faq"])
    shared = "\n\n".join(wa(src["sections"][k], t) for k in SHARED)
    footer = src["footer"].replace(
        "</div></footer>",
        f'  <p>Andere Branchen: {others} · <a href="/websites/">alle Branchen</a></p>\n</div></footer>')
    desc = t["desc"].format(once=x["once"], month=x["month"], base_once=base_once, base_month=base_month)
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(t["title"])}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="https://6b62.com/websites/{t["slug"]}/">
{src["head_meta"]}
<meta property="og:type" content="website">
<meta property="og:title" content="{e(t["og_title"])}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="https://6b62.com/websites/{t["slug"]}/">
{src["icon"]}
<style>
{src["css"]}{EXTRA_CSS}</style>
</head>
<body>
<!-- Built by websites.py from /websites/index.html. Edit there or in websites.py, not here. -->
<a class="skip" href="#main">Zum Inhalt</a>

<div class="top"><div class="wrap">
  <a class="who" href="/websites/">Konstantin Bauer<span>{e(t["label"])}</span></a>
  {wa(one(r'(<a class="btn" href="https://wa.me/[^"]+">.*?</a>)', src["btns"], "WhatsApp button").replace("Gratis-Entwurf per WhatsApp", "Gratis-Entwurf"), t)}
</div></div>

<main class="wrap" id="main">

<section class="hero" aria-labelledby="h-hero">
  <p class="trades-line"><span class="here">{e(t["eyebrow"])}</span> ·&nbsp;<a href="/websites/">andere Branche</a></p>
  <h1 id="h-hero">{e(t["h1"])}</h1>
  <p class="lead">{e(t["lead"])}</p>
  <p class="price">Grundseite: <b>{base_once}</b> einmalig, dann <b>{base_month}</b> im Monat</p>
  <p class="small">{nb(f'Im ersten Jahr {src["base_year"]}. Wie im <a href="#beispiel">Beispiel unten</a>, {e(t["ex_with"])}: {e(x["once"])} einmalig. {src["terms_tail"]}')}</p>
  {src["free"]}
  {wa(src["btns"], t)}
</section>

<section id="beispiel" aria-labelledby="h-beispiel">
  <h2 id="h-beispiel">{e(t["ex_h2"])}</h2>
  <p class="txt intro">Jede Seite baue ich für Ihren Betrieb, aus keiner Vorlage. So sieht ein typisches Beispiel aus:</p>
  <div class="excase">
    <div class="part">
      <h3>Was die Seite für Sie tut</h3>
      {x["ul"]}
      {(chr(10) + "      ").join(x["ex"])}
    </div>
    <div class="part">
      <h3>Was es kostet</h3>
      {x["table"]}
    </div>
  </div>
  {src["note"]}
  {wa(src["mid"], t)}
</section>

<section aria-labelledby="h-faq">
  <h2 id="h-faq">{e(t["faq_h2"])}</h2>
  <ul class="terms">
{faq}
  </ul>
</section>

{shared}

</main>

{footer}
</body>
</html>
"""


def main():
    check = "--check" in sys.argv[1:]
    src = source()
    stale = []
    for t in TRADES:
        out = ROOT / f"site/websites/{t['slug']}/index.html"
        new = page(t, src)
        if check:
            if not out.exists() or out.read_text(encoding="utf-8") != new:
                stale.append(str(out.relative_to(ROOT)))
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(new, encoding="utf-8")
            print(f"{out.relative_to(ROOT)}  {len(new.encode())} B")
    if stale:
        sys.exit("websites.py --check: out of date, run ./websites.py: " + ", ".join(stale))


if __name__ == "__main__":
    main()
