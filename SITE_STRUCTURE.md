# LA_V85 – webbstruktur

## Grundprincip

Webbplatsen har två huvudnivåer:

1. **Aktuell omgång** – veckans enda aktiva arbetsyta.
2. **Historik** – en master som leder till avslutade omgångar.

En avslutad omgång har i sin tur två tydliga faser:

- **Förhandsarkiv** – det material och de val som fanns före start.
- **Efteranalys** – resultat, utvärdering och lärdomar.

Förhandsmaterial ska aldrig skrivas om med facit i hand. Efter start arkiveras sidan och länkas från historikmastern.

## Nuvarande sidor

| Nivå | Sida | Syfte |
| --- | --- | --- |
| Aktuell | `/` | Bjerke 31 oktober, startlista och arbetsyta |
| Master | `/history/` | Samlad ingång till alla avslutade omgångar |
| Omgång | `/archive/2026-10-24-jagersro/` | Jägersros förhandsmaterial och efteranalys |
| Omgång | `/archive/2026-10-17-gavle/` | Gävles frysta förhandsmaterial |
| Analys | `/archive/2026-10-17-gavle/analys/` | Gävles efteranalys |
| Omgång | `/archive/2026-10-10-solvalla/` | Solvallas frysta förhandsmaterial |
| Analys | `/resultatanalys/` | Solvallas efteranalys |
| Omgång | `/archive/2026-10-03-boden/` | Bodens förhandsmaterial och analyssektioner |

## Navigationsregler

- Huvudmenyn visar bara **Aktuell omgång** och **Historik**.
- Arkivsidor visar dessutom en lokal omgångsrad med bana, datum och flikarna **Förhandsarkiv** och **Efteranalys**.
- Historikmastern är den enda sidan som listar alla omgångar.
- En äldre sida får aldrig märkas som aktuell.
- Varje omgång ska ha en unik, beständig URL.

## Arbetsgång för kommande omgångar

1. Skapa veckans sida som `/` och ange bana och datum i den gemensamma navigationen.
2. Publicera verifierad startlista och marknadsdata med tydlig källtid.
3. Spara förhandsurvalet före första start.
4. Efter omgången: kopiera den oförändrade sidan till `/archive/YYYY-MM-DD-bana/`.
5. Skapa efteranalysen under omgångens `analys/`-katalog.
6. Lägg till omgången överst i `/history/` med båda länkarna.
7. Byt `/` till nästa omgång och uppdatera aktuell bana/datum i `site-navigation.js`.

## Framgent

För att undvika fortsatt specialkod bör nästa tekniska steg vara att flytta omgångsmetadata till en gemensam JSON-fil. Navigation, historikkort och omgångsflikar kan då genereras från samma källa. När den förändringen görs bör även Solvallas äldre `/resultatanalys/` flyttas till `/archive/2026-10-10-solvalla/analys/`, med en omdirigering från den gamla adressen.

## Bjerke – marknadsdata

- `bjerke-20261031.json` innehåller den senaste verifierade ATG-snapshoten för V85 den 31 oktober: startlistor, odds, streck, kuskar, tränare och hemmabanor.
- `scripts/update_bjerke.py` används av GitHub Actions-flödet `.github/workflows/bjerke-hourly.yml` för att uppdatera snapshoten fram till spelstopp.
- `bjerke-dashboard.js` visar snapshoten på startsidan. Källtid och eventuell brist på data måste alltid framgå; inga uppgifter ska presenteras som liveodds.
- För ändringar från ChatGPT eller VS Code: läs alltid senaste GitHub-version och använd filens aktuella blob-SHA före uppdatering för att minska risken att skriva över parallella ändringar.
