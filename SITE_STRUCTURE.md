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

## Bjerke – tvåstegsmodell för spikar och skrällar

Sidan för den aktuella omgången visar nu en **separat manuell vinnarmodell** utöver den automatiska marknadsbevakningen. Den påverkar inte ATG-importen eller historiken.

**Steg A: rangordna hela startfältet.** Använd fem verifierade delbedömningar per häst på skalan 0–5:

| Delbedömning | Vikt | Obs |
| --- | ---: | --- |
| Aktuell form och kapacitet | 30 % | Senaste prestationer och konkurrens |
| Loppbild och startspår | 25 % | Spets/tempo/trafik och positionschans |
| Distans, klass och bana | 20 % | Relevant dokumenterad förmåga |
| Kusk, utrustning, verkliga förändringar | 15 % | Förändring jämfört med tidigare starter |
| Dagsform, osäkerhet och risk | 10 % | 5 poäng betyder låg risk |

Vägd poäng = summan av delbetyg/5 × vikt; intervallet är 0–100. **Poängen är inte en sannolikhet**. Ingen fullständig inbördes ranking visas innan samtliga icke strukna hästar fått fem betyg.

**Steg B: bedöm och jämför vinstchanser.** Ange separat en *egen preliminär* vinstchans 0–100 % för varje aktiv häst. Summan för ett lopp ska bli 100 % (±0,5 procentenheter). Först då visar sidan differensen mellan den egna bedömningen och aktuell V85-streckprocent. Positiv differens och minst 20 % relativ övervikt (och +2 procentenheter) markeras som möjlig värdesignal; negativ differens och minst 15 % relativ undervikt (och −3 procentenheter) som möjlig överstreckning. Gränserna är oprövade arbetsregler, **inte validerade lönsamhetsgarantier**.

- Spikförslag kräver separat motbuds-, form- och startmomentskontroll; högst streckprocent räcker inte.
- Skrällar kan finnas även över 10 % streck. En låg streckandel i sig är inget vinnarargument.
- Tidiga vinnarodds med låg omsättning och censurerat odds 99,99 får inte behandlas som exakt vinstsannolikhet.
- `bjerke-model.js` sköter den manuella tvåstegsarbetsytan på `/`; `bjerke-model.css` dess stilar.
- Betyg och egna vinstchanser sparas i **webbläsarens localStorage**, inte i GitHub. De följer därför inte med till andra enheter, och de är inte en fryst publicerad förhandsanalys.
- Den automatiska `bjerke-20261031.json`-filens `recommendations` är fortfarande **endast streck-/trendbaserade marknadssignaler**. De får inte beskrivas som resultat från tvåstegsmodellen.
- Vikterna och etiketternas gränser är **hypoteser för framtida utvärdering**. Frys urval och bedömningar före start och jämför mot verkliga resultat utan efterhandsjustering.


## Bjerke – automatisk formhistorik inför 31 oktober

- `scripts/update_bjerke_form.py` hämtar de åtta loppens utökade ATG-data med `/races/{raceId}/extended` och avläser historik ur `starts[].horse.results.records`. Detta format verifierades på Bjerkes verkliga lopp den 27 oktober 2026; det är inte ett officiellt versionsgaranterat API.
- GitHub Actions `.github/workflows/bjerke-form.yml` kör separat från ordinarie marknadsbevakning och skriver endast `bjerke-form-20261031.json` om underlaget förändrats. Ingen uppdatering sker efter lördagens start.
- `bjerke-form.js` redovisar fem senaste starter, antal användbara formrader, poäng för form och separat distansprov, risk om verifierbart, datatäckning och källtid. Saknade uppgifter redovisas som saknade – aldrig som noll.
- `bjerke-model.js` kan förifylla de två verifierade delpoängen `form` och `risk`, men ändrar **inte** användarens befintliga egna poäng eller vinstprognoser i webbläsaren. Formpoäng sätts bara när minst två användbara historiska prestationer finns. En fullständig ranking kräver fortfarande övriga kategorier.
- Uträkningen bygger på **föregående lopp**, aldrig på framtida resultat eller bettingmarknad. `form` är en första oviktad klass-/motståndsjustering och ska inte beskrivas som en kalibrerad vinstchans. `distanceOnlyScore` är ett separat mått och fyller **inte** automatiskt den bredare kategorin `class`.
- API-fel som drabbar alla åtta lopp gör att föregående giltiga formrapport behålls. Fel i enskilda lopp syns i `failures` och saknade hästar får inga fabricerade data. Publicerade procenttal är alltid ATG-streck, inte modellprognoser.
- **Nästa utvecklingssteg:** uppskatta hästens klass mot motstånd (historisk prissumma/resultat), undersök loppbildens historiska positioner och skapa ett tidskorrekt, testat förhandsprognosmått över fler avslutade omgångar. Inga sådana kompletteringar har ännu påståtts vara automatiserade.

### Utökning 27 oktober – klass- och tempo/spårproxy

- ATG:s fem tidigare starter för varje häst utökas med historiska lopps **förstapris**, land, startmetod, startspår och kilometertid där informationen finns. Endast lopp strikt **före 31 oktober** inkluderas.
- **Klass (20 %):** tidigare lopps förstapris jämförs endast med lopp från *samma land* i aktuell V85-avdelnings historiska jämförelsefält. En kombination av prisnivå och faktiskt resultat ger en **klassproxy**. Minst två egna relevanta lopp och tillräcklig datavariation krävs. Detta är inte en verifierad klass-/motståndsrating och valuta jämförs inte direkt mellan länder.
- **Tempo/spår (25 %):** vid **autostart** krävs minst två historiska kilometerresultat på ungefär aktuell distans, och minst fem jämförbara hästar i aktuell avdelning. Historiska tider och det aktuella startspåret ger en *tempo-/positionsproxy*. Den beräknar **inte** faktisk spetschans eller delsträckornas hastighet. Vid voltstart eller brist på jämförbara historiska tider lämnas indikatorn tom.
- **Form (30 %)** och **risk (10 %)** behålls från tidigare insamling. **Utrustning/kusk (15 %)** beräknas ännu inte; ändringar ska verifieras. Kategorier utan tillräckligt underlag förblir `null`, aldrig 0.
- Rapporten redovisar `coverage.classRated`, `coverage.paceRated` och `coverage.partialRanked`. `evidence.partialRankScore` är en *normaliserad delpoäng* över kända faktorer och visas med datatäckning (`modelCoverageWeight`). Minst två kända faktorer, motsvarande minst 45 % av modellens totala vikt, krävs för delpoäng. Det går **inte** att likställa 70 delpoäng med 70 % vinstchans eller full A–D-ranking.
- `bjerke-form.js` visar preliminär sortering, förklaringar och historiska startuppgifter för samtliga åtta avdelningar. `bjerke-model.js` förifyller form/klass/tempo/risk *där de finns*, men användarens lokalt sparade manuella poäng har företräde och förändras inte av GitHub Actions.
- **Utvärdering krävs:** kontroll av datakvalitet, eventuell lands-/banbias, backtest på frysta tidigare omgångar, riktigt spetsunderlag och senare en kalibrerad vinstchansmodell. Marknadsandelar, odds och resultatinformation efter loppet får aldrig läcka in i förhandsbedömningen.
