# LA_V85 – sidor och arbetsflöde

## Aktuell omgång

`rounds.json` väljer aktuell omgång och samlar datum, bana och länkar till förhandsarkiv och efteranalys. Startsidan använder denna metadata, inte en föregående omgångs filer. Aktuell arbetsyta är Eskilstuna 14 november 2026. Åtta lopp och 102 hästar är hämtade och identitetskontrollerade mot ATG:s kalender och omgångsdata. CatBoost-rankning och historisk form är omräknade för samtliga 102 hästar; modellfilen och formfilen är bundna till samma ATG-snapshot. Träningen använder det befintliga kontrollerade underlaget med 12 247 starter i 1 047 lopp till och med 31 oktober. Ny omgång har separat analys; tidigare spikar och modellprognoser återanvänds inte. Bergsåkers startsida bevaras på `archive/2026-11-07-bergsaker/forhand.html` med en egen omgångskonfiguration och bevarade renderingsskript. Efteranalysen ligger kvar på `efteranalys/2026-11-07/`.

Huvudmenyn har tre delar: **Lördagens V85**, **Historik**, **Metod & resultat**. Startsidan har ankarlänkar till **Skrällförslag**, **Spikförslag**, **Lopp för lopp** och **Mitt urval**. En avdelning visas åt gången med sökning, sortering och hästkort i mobilvy.

- `index.html`, `v85.css`, `v85.js`: den gemensamma arbetsytan.
- `v85-domain.js`: omgångsvalidering, granskade förslag, urval, radberäkning och förhandsfrysning.
- `rounds/<omgång>/data.json`: verifierad marknadssnapshot eller uttrycklig status `awaiting_data`.
- `rounds/<omgång>/analysis.json`: granskade förslag; samma gameId och snapshotId som datakällan krävs.
- `metod/`: definitioner, kriterier för förslag och jämförelse av publicerade historiska tester.
- `research/`: fördjupade experiment, modeller och frysta forskningsprognoser.
- `history/`: gemensam ingång till avslutade omgångar.

## Verifierat underlag och förslag

Kör `python3 scripts/update_current_round.py` från projektroten. Skriptet upptäcker V85-ID från ATG:s kalender och verifierar datum, bana, åtta lopp, hästidentiteter, starttid och källtid. Saknade uppgifter gissas inte. Nätverksfel, felaktig data, äldre snapshots eller passerad start lämnar tidigare data oförändrad. TLS-verifiering och den konfigurerade proxyn ska användas.

Inga förslag genereras enbart från låg streckandel eller hög marknadsrank. När underlaget har granskats anges `gameId`, `snapshotId`, `reviewedAt` och `version` i analysis.json. Varje post i `picks` ska innehålla:

- `type`: `outsider` eller `spike`.
- `leg`, `number`, `name`: exakt häst i rätt avdelning.
- `reason`, `risk`, `sources`: konkret motivering, risk och minst en HTTPS-källa.
- `challengers`: minst två granskade, aktiva motbuds namn för spikförslag (samtliga om färre än två finns).

En ny marknadssnapshot kräver förnyad kontroll av förslagen. Strukna hästar visas aldrig som aktiva förslag. Saknad analys blockerar inte läsning av verifierade startlistor.

## Egna urval och arkiv

Egna urval sparas per omgång i localStorage. En spik ersätter andra val i samma avdelning. Radantal är produkten av antalet valda hästar i alla åtta lopp. Radpris anges av användaren när verifierat pris saknas.

Frysning kräver minst en vald aktiv häst, verifierat underlag och en verifierad starttid som ännu inte passerats. Kopian bevarar urval, noteringar, marknad, analysversion och källtider. Den laddas ner och sparas lokalt. Lokal tid är inte serververifierad och exporten är inget inlämningskvitto. Senare ändringar eller strykningar påverkar arbetsurvalet, inte redan frysta kopior.

Varje avslutad omgång har en beständig arkivadress. Bjerkes tidigare arbetsyta finns på `archive/2026-10-31-bjerke/forhand.html`; den är en bevarad arbetsyta med senast sparade data, inte ett retroaktivt fryst personligt urval. Gävles historiska data ligger i dess egen arkivkatalog. Den äldre `rounds/2026-10-10-solvalla/` leder till Solvallas kanoniska arkivsida. Saknade forskningsfrysningar markeras som saknade och återskapas inte efter start.

## Lokal validering

```sh
python3 -m http.server 8001 --bind 127.0.0.1
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_v85_domain.cjs
node tests/test_homepage.cjs
```

Webbläsartestet kräver Playwright och Chromium. Det kontrollerar först den verkliga startsidan och testar sedan urvalsflödet med uttryckligt syntetiska svar i en isolerad webbläsarkontext. Testdata skrivs aldrig till webbplatsens datafiler.

## Träningsdata efter datarättningen 1 november

Alla modelltränare använder `scripts/data_quality.py`. Den äldre databasen är bevarad; ofullständiga lopp spärras och dess galoppvärden används inte. Rådatabaserad återinsamling sköts av `scripts/historical_pilot.py` och skriver `historical_pilot_v2.json` samt kontrollerbara källsvar under `research/raw-history/`. `--offline` förbjuder nätanrop och använder endast sparade, hashkontrollerade råsvar.

`research/training_data_quality_2026.json` redovisar användbara lopp och spärrade lopp. Modellrapporter efter rättningen skrivs till `*_v2.json`; ett otillräckligt underlag får en uttrycklig status utan prestationsmått. Metodsidan visar de nya rapporterna och `data-quality.js` visar datakontrollen. Äldre forskningsresultat och frysta prognoser är historiska och bevaras. Se `research/DATA_QUALITY.md` för återhämtning och tester.

## Historisk implementation: Bjerke 31 oktober

Följande beskriver den bevarade äldre arbetsytan, inte Bergsåkers nya startsida.

## Bjerke – marknadsdata

- `bjerke-20261031.json` innehåller den senaste verifierade ATG-snapshoten för V85 den 31 oktober: startlistor, odds, streck, kuskar, tränare och hemmabanor.
- `scripts/update_bjerke.py` används av GitHub Actions-flödet `.github/workflows/bjerke-hourly.yml` för att uppdatera snapshoten fram till spelstopp.
- `bjerke-dashboard.js` visar snapshoten i Bjerkes förhandsarkiv. Källtid och eventuell brist på data måste alltid framgå; inga uppgifter ska presenteras som liveodds.
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
- `bjerke-model.js` sköter den manuella tvåstegsarbetsytan i Bjerkes förhandsarkiv; `bjerke-model.css` dess stilar.
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

## Aktuell formuppdatering

Efter `python3 scripts/update_current_round.py`, kör `python3 scripts/update_current_form.py`. Formrapporten återanvänder de testade historiska beräkningsfunktionerna, kontrollerar lopp- och hästidentitet och använder endast starter före aktuell tävlingsdag. Den skriver först när alla åtta lopp hämtats. Rapporten binds till aktuell snapshotId. Startsidan visar delranking, datatäckning och fem senaste starter. Ingen tränad XGBoost/CatBoost-prognos eller kalibrerad vinstchans påstås.

## Våra inlämnade resultat

`resultat/` samlar användarens sex V85-kuponger från oktober–november 2026. `data.json` bevarar alla streck, reserver, inlämningstider, ATG-källor, SHA-256 för källsvaren, vinnare och utdelningsberäkningar. HTML är förgenererad och läsbar utan JavaScript. Filtret påverkar bara omgångslistan; totalsiffrorna avser alla sex. Beräknad utdelning är inte verifierad kontoutbetalning. Alla sex kuponger har 50 % insats och inga valda strykningar. Jägersros döda lopp har flera godkända vinnare per avdelning; en rad räknas endast en gång. Nya kuponger kräver ny avläsning, kontroll av strykningar/reserver och ny beräkning. Startsidan och huvudmenyn länkar till resultatöversikten.
