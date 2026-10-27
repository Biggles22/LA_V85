# LA_V85 – historisk pilot med tidsseparerat test

Den här katalogen innehåller ett **forskningsförsök**, inte färdiga spelråd eller validerade vinstsannolikheter.

## Syfte

1. Hämta avslutade V85-omgångar från ATG:s webbplats-API med kända datum från mars till oktober 2026.
2. Spara endast sådana hästvariabler som kunde beräknas från starter **före** respektive historiskt lopp. Tidpunkterna kontrolleras i `scripts/historical_pilot.py`.
3. Hämta resultat separat och använda vinnaren **enbart som målvariabel/facit**.
4. Träna en liten XGBoost-modell på äldre lopp och testa på **senare, helt åtskilda tävlingsdatum**.
5. Jämföra topprankade hästar mot slutlig ATG-streckfördelning där hela marknadsunderlaget finns.

## Data och kvalitet

- `historical_pilot_2026.json`: använda tävlingsdatum, godkända lopp, facit, hästarnas tidigare prestationer i kompakt numerisk form och eventuella **retrospektiva slutstreck**.
- `model_report_2026.json`: först när en testkörning lyckats; historiskt träningstest, mått för topp 1/topp 3, log loss och Brier samt motsvarande jämförelse mot tillgängliga marknadsdata.
- Endast en vinnare och minst sex verifierade startande per lopp får ingå. Dött lopp och otillräckligt resultat underkänns; inga gissade placeringar.
- Marknadsstrecken är från historiskt hämtad slutpool. Det är **inte samma sak som vår tidsstämplade snapshot före start**, och detta ska framgå tydligt i jämförelsen.
- Datan från ATG:s webbplats-API saknar officiell stabil utvecklargaranti. Vi bör begränsa antalet anrop och kontrollera användningsvillkor, fel och överensstämmelse vid fortsatta utökningar.
- Ingen viktning efter slutresultat, inga framtida starter och ingen `horse.statistics` från efter loppet. Historiska odds och streck används inte som träningsvariabler i grundmodellen.
- Denna pilot har **en enda tidsuppdelad holdout**. Det räcker inte för att bevisa spelvärde, statistiskt säker förbättring eller kalibrerad vinstchans.

## Filer

- `scripts/historical_pilot.py`: ATG-insamling med strikt datumsnitt, schemafilter och skydd mot dataläckage.
- `scripts/train_historical_pilot.py`: första XGBoost-testet, med 12 förhandskända numeriska faktorer.
- `tests/test_historical_pilot.py`: regressions- och läckagetester.
- `.github/workflows/historical-pilot.yml`: fristående GitHub Actions-pilot. Gör inga ändringar i Bjerkes nuvarande V85-tips eller automatiska oddsflöde.

## Viktiga begränsningar

För att omvandla modellen till en faktisk spelvärdesmodell måste vi senare:

1. Öka antal omgångar och tidsfönster, kontrollera alla speltyper och banor.
2. Ha jämförbara, **verifierade prestart-streck** vid samma tidpunkt som vår prognos.
3. Kalibrera sannolikheter på separat valideringsperiod samt utvärdera en längre osedd testperiod.
4. Jämföra mot de tre mest spelade och räkna på verkligt systemutfall, kostnad och eventuell utdelning.
5. Kontrollera om rangordning faktiskt hjälper mer än favoritrankingen, utan att justera modellen med facit.

**V85 lanserades 25 oktober 2025.** Äldre V75-lopp kan användas som kompletterande träningsmaterial i en senare fas, men får inte blandas in utan uttrycklig spelforms-/fältkontroll.


## Första verifierade körningen 27 oktober 2026

Historikpiloten lyckades samla **47 avslutade lopp och 505 häststarter från sju tävlingsdatum**. Av dessa användes **19 lopp i den kronologiskt senare testperioden**. Inget tävlingsresultat efter respektive lopp användes som hästvariabel.

| Mått | XGBoost, alla 19 testlopp | XGBoost, 9 jämförbara lopp | ATG, samma 9 lopp |
| --- | ---: | ---: | ---: |
| Vinnaren rankad 1 | 4/19 | 1/9 | 5/9 |
| Vinnaren inom topp 3 | 10/19 | 5/9 | 8/9 |

**Slutsats:** för denna lilla pilot rankade ATG:s retrospektiva slutstreck vinnarna bättre än den tränade modellen, när samma nio lopp jämfördes. Resultaten räcker **inte** för att bevisa generell överlägsenhet, vinstvärde eller kalibrerade sannolikheter.

ATG:s kalenderfunktion gav upprepade HTTP 500. Vi återhämtade identifierbara äldre V85-omgångar via kontrollerade spel-ID-kandidater samt fyra exakt arkiverade ID:n. Några historiska datum och lopp förblev otillgängliga. Lopp med dött lopp eller för stor andel okända resultat filtrerades bort. Resultat för hästar med okänd placering användes **inte** som förluster.

För att påstå bättre spelvärde behövs en större serie, jämförbar förhandsmarknad och återkommande tidsseparerade testperioder. Vi gör ingen Benter-blend och publicerar inga automatiska AI-spikar baserat på detta resultat.

[Läs rapporten på webbplatsen](https://biggles22.github.io/LA_V85/research/) · [Källdata](https://github.com/Biggles22/LA_V85/blob/main/research/historical_pilot_2026.json) · [Modellresultat](https://github.com/Biggles22/LA_V85/blob/main/research/model_report_2026.json).

## Andra etappen 27 oktober – utökad historik och upprepade tester

GitHub Actions har hämtat och verifierat **178 V85-lopp med 1 931 häststarter från 25 tävlingsdatum**. Insamlingen omfattar delar av perioden november 2025–oktober 2026. Datakällan är det ej officiellt versionsgaranterade ATG Racinginfo-gränssnittet. Historiska spel-ID har kontrollerats mot åtta lopp per V85-omgång. Några lopp och datum är fortfarande otillgängliga.

Nu finns ett andra testsätt i `scripts/walkforward_evaluation.py`:

- **21 kronologiska testfönster:** varje modell tränas bara på tidigare tävlingsdatum, därefter bedöms nästa datum.
- **151 osedda lopp:** modellen rankade vinnaren först i 39 lopp (25,8 %) och inom topp tre i 82 lopp (54,3 %).
- **Strikt marknadsjämförelse:** bara lopp med en entydig vinnare, nära 100 % registrerade resultat och en någorlunda komplett ATG-slutpool (95–105 % totalt) får jämföras.
- **25 jämförbara lopp:** XGBoost träffade topp 1 i 7/25 (28 %) och topp 3 i 15/25 (60 %). ATG:s slutstreck träffade topp 1 i 12/25 (48 %) och topp 3 i 20/25 (80 %).
- **Skydd:** den nya rapporten är skild från äldre experimentrapport, och redan verifierad historik behålls vid nya API-fel. Eget VS Code-arbete och Bjerkes livefiler lämnas orörda.

Dessa 25 lopp är **ett selekterat kvalitetsurval** och ger ännu inget påstående om att någon modell fungerar bättre generellt eller kan generera positivt spelvärde. Eftersom ATG-kolumnen innehåller historiska **slutstreck** är jämförelsen inte en fullständig förhandssimulering. Några träningslopp har partiellt okända placeringar; okända hästar behandlas inte som förlorare, men urvalet kan fortfarande ge bias.

**Resultat:** vår första AI-modell är i nuläget tydligt sämre än streckrankingen i kvalitetsurvalet. Vi använder därför inte automatisk AI-spik eller AI-skräll i lördagens rekommendationer.

[Läs de nya testfönstren](https://biggles22.github.io/LA_V85/research/) · [Walk-forward-rapport](https://github.com/Biggles22/LA_V85/blob/main/research/walkforward_report_2026.json).

**Fortsatt utveckling:** utöka med verifierbara lopp från fler månader och speltyper; arbeta med mer rättvis form-/motståndsklassning och startmoment; analysera dataläckage och urvalsbias; samla tidsstämplade *förhandsstreck* och utvärdera på separata kommande omgångar innan någon kalibrering eller Benter-blend.

## Tredje etappen – historiska marknadssnapshots och faktorjämförelse

**Förhandsmarknad.** Vi sparar nu oföränderliga snapshots från ATG:s **faktiska observationsperiod före tävlingsstart** under `research/prestart/2026-10-31/`. Varje fil innehåller källtid, observationstid, tidsfördröjning, åtta lopp, startnummer, hästnamn, ATG-streck och strykningar. Programmet `scripts/capture_prestart_market.py` kontrollerar att procentsumman blir cirka 100 % per lopp och vägrar förhandsarkivering efter spelstart. Filnamnet baseras på källtid och innehållshash, vilket förebygger dubbla commits med identiska data. `.github/workflows/bjerke-prestart-history.yml` kör schemalagt och separat från ordinarie Bjerke-fil. **ATG:s källa är inofficiell och kan sluta fungera.** Omedelbar snapshot efter senaste ändring garanteras inte, eftersom GitHub Actions tidsschema kan försenas.

Den första verkliga snapshoten sparades med **ATG-källtid 27 oktober 2026 kl. 09.01.30 svensk tid** och **observation kl. 09.24.59**, 23 minuter och 30 sekunder senare. Åtta lopp, 97 hästar. Den äldre historikens ATG-slutstreck får **inte** beskrivas som om de varit observerade i förväg.

**Faktorförsök v2.** `scripts/feature_trial.py` lägger till tolv fasta förhandsvariabler på samma 1 931 historiska häststarter och samma 21 walk-forward-fönster som grundmodellen. Experimentet tränar två XGBoost-modeller med identiska hyperparametrar och daterad holdout. Inga slutresultat, odds eller streck får ingå i input-matriserna. Proxyn för loppklass baseras på tidigare lopps prissumma och hästens form, **inte** på verifierade tidigare motståndares förmåga. Äkta bananpassning och första-500-meters-tider saknas fortfarande.

| Samma testlopp | Grundmodell | Faktorvariant | ATG-slutstreck |
| --- | ---: | ---: | ---: |
| Topp 1, 151 lopp | 39/151 (25,8 %) | 36/151 (23,8 %) | – |
| Topp 3, 151 lopp | 82/151 (54,3 %) | 81/151 (53,6 %) | – |
| Log loss, 151 lopp | 2,1671 | 2,1455 | – |
| Topp 1, strikt 25 lopp | 7/25 | 8/25 | 12/25 |
| Topp 3, strikt 25 lopp | 15/25 | 15/25 | 20/25 |

Resultatet visar **ingen robust förbättring i antal rätt**; log loss och Brier blev något bättre. Variationen kan vara slumpmässig och databasen har fortfarande kvalitets- och urvalsbegränsningar. **Vi byter därför inte modell för den aktuella V85-omgången** och använder inte dessa poäng för automatiskt genererade spikar eller skrällar.

Nästa tekniska uppgift för att faktiskt modellera **motståndets styrka** är ett sparsamt, källverifierat register över deltagare och deras **historiska rating vid datumet för ett tidigare lopp**. Det kräver fullständiga äldre startfält och datumsäker as-of-join; historiskt förstapris är inte tillräckligt. En sådan faktisk motståndsmodell är **inte** implementerad ännu.

[Faktortestets rapport](https://github.com/Biggles22/LA_V85/blob/main/research/feature_trial_2026.json) · [Förhandsarkivet](https://github.com/Biggles22/LA_V85/tree/main/research/prestart/2026-10-31) · [GitHub-körningar](https://github.com/Biggles22/LA_V85/actions).

## Tidskorrekt prov av faktiska tidigare motståndare

För att undvika att likställa förstapris med verklig motståndsnivå provar vi nu `scripts/opponent_probe.py`: högst **16 distinkta tidigare lopp** (för hästar på Bjerkes nuvarande startlista). Programmet hämtar det tidigare startfältet och beräknar motståndarnas vinst-/topp-3-form från enbart starter med datum **strikt före det tidigare loppet**. Hästen som utvärderas tas bort ur den egna motståndarsammanställningen. Saknade placeringar räknas inte som förluster. Minst fyra, eller hälften av rivalerna, måste ha tillräcklig tidigare historik.

- 16 olika äldre lopp försöktes; 14 kunde hämtas; 13 av 14 bedömda referenser fick tillräckligt underlag.
- Två historiska API-anrop gav HTTP 404 och avgränsades bort.
- Måttet `opponentRecentFormMean` (0–1) är ett dokumenterat *historiskt prestationsmått* för tidigare motståndare, inte en kalibrerad vinstprocent för vår häst.
- Denna studie är **ännu inte inkluderad i XGBoost- eller Bjerke-rankingen**. Den är för liten och för ojämnt täckt. Nästa steg kräver större, källverifierat datastöd och test av om variabeln tillför signal på osedda lopp.
- `.github/workflows/opponent-probe.yml` har egna regressionstester och producerar endast `research/opponent_probe_2026.json`; inga livefiler eller tips skrivs om.

[Rapport från motståndsprovet](https://github.com/Biggles22/LA_V85/blob/main/research/opponent_probe_2026.json).


## Fjärde etappen – större prov av faktiska motståndare och historiskt formtest

**Utökad Bjerkeinsamling:** `scripts/opponent_coverage.py` utgår från **alla 97 aktiva hästar** i `bjerke-form-20261031.json`, i stället för de två första hästarna per avdelning. Tidigare lopp dedupliceras och högst 100 distinkta äldre lopp hämtas, med högst två samtidiga nätverksanrop. Godkända historiska lopps startfält och deras före-lopp-form cacheas i `research/opponent_coverage_2026.json`. Historiska resultat från **det studerade loppet och senare** får aldrig ingå i motståndarnas formmått. När för få motståndare har tidigare resultat lämnas ratingen tom, inte noll. Detta är inte ett tränat spelprognosmått.

Första verifierade körningen: **100 tidigare lopp planerade; 94 läsbara; 90 av 97 Bjerkehästar hade minst en tidigare prestation med tillräckligt dokumenterade motståndare**. Sex gamla lopp gav HTTP 404 och deras information fabricerades inte. `.github/workflows/opponent-coverage.yml` testar före-lopp-tid och urval och skriver bara forskning, aldrig Bjerkes publika tips.

**Separat historiskt formexperiment:** `scripts/opposition_field_trial.py` använder **de andra startande i samma historiska V85-lopp** och deras daterade förhandsform. Detta är ett närliggande men **annat mått** än motståndarna i en hästs äldre lopp. Det senare har inte backtestats ännu. De två XGBoost-modellerna i detta experiment tränas på samma tidigare tävlingsdatum med identiska hyperparametrar, och jämförs på samma **151 senare lopp** från 21 walk-forward-testfönster.

| Mått | Grundmodell | Motståndarnas förhandsform i fältet |
| --- | ---: | ---: |
| Topp 1, 151 lopp | 39/151 (25,8 %) | 38/151 (25,2 %) |
| Topp 3, 151 lopp | 82/151 (54,3 %) | 79/151 (52,3 %) |
| Log loss, 151 lopp | 2,1671 | 2,1276 |
| Brier score, 151 lopp | 0,08134 | 0,08035 |

Detta ger en marginell förbättring av sannolikhetsmåtten, **men sämre vinnarranking**. Resultatet kan påverkas av selektion och att samma historiska data använts i flera utvecklingsförsök. Inga automatiska spikar eller skrällar från denna experimentmodell ska användas. Historiska ATG-jämförelser är retrospektiva slutstreck, inte samtidiga förhandssnapshots.

**Nästa experiment** är en äkta historisk före-lopp-join som mäter kvaliteten på **de faktiska motståndarna i hästarnas egna tidigare lopp** i tillräckligt många redan avgjorda V85-lopp. Först då går det att testa den nya 90/97-datakällans motsvarighet i ett osett utfall. Det kräver fler kontrollerade äldre lopps startfält och tillhörande förhandsform samt tydlig hantering av saknad historik.

[Källspår för bred motståndsinsamling](https://github.com/Biggles22/LA_V85/blob/main/research/opponent_coverage_2026.json) · [Historiskt experiment](https://github.com/Biggles22/LA_V85/blob/main/research/opposition_field_trial_2026.json).

## Femte etappen – historiskt före-lopp-test av faktiska tidigare motståndare

**Nytt test, två strikta datumgränser.** `scripts/historical_opponent_asof.py` väljer historiska V85-lopp *utan att känna till deras vinnare* och hämtar tidigare lopps fulla startfält från ATG:s ej versionsgaranterade webbgränssnitt. En tidigare start måste ligga **före V85-loppet**. De verkliga motståndarnas senaste placeringar i den tidigare starten beräknas i sin tur enbart med data **före den tidigare starten**. En vunnen historisk V85-start påverkar alltså endast testfacit, inte förhandsvariablerna.

Den första insamlingen fick först en **tidsobalanserad täckning**, eftersom ett för litet tak för API-anrop gynnade äldre testdatum. Urvalet utökades därför till 380 möjliga tidigare loppskort; 366 verifierade kort fanns tillgängliga. Redan insamlat material behölls, och senare datum prioriterades. Resultatet är **42 analyserade äldre V85-lopp, 452 matchade häststarter och 441 häststarter med beräknad tidigare motståndarform**, över 25 tävlingsdatum.

Den oberoende experimentfilen `scripts/historical_opponent_test.py` jämför samma två XGBoost-modeller över 21 kronologiska testfönster. Den försöker inte kalibrera vinstprocent eller skapa spelrekommendationer. En strikt delmängd för motståndsjämförelsen kräver minst sex bedömda hästar och minst 60 % täckning i loppet.

| Resultat, samma 35 testlopp | Grundmodell | Med verkliga tidigare motståndare |
| --- | ---: | ---: |
| Vinnaren rankad först | 9/35 (25,7 %) | 7/35 (20,0 %) |
| Vinnaren bland topp 3 | 20/35 (57,1 %) | 22/35 (62,9 %) |
| Log loss (lägre = bättre) | 2,1247 | 2,0631 |
| Brier score (lägre = bättre) | 0,08099 | 0,07986 |

På **samtliga 151 walk-forward-testlopp**, inklusive lopp där motståndarvariabeln saknas, blev topp 1 **39/151 mot 35/151**, medan topp 3 blev **82/151 mot 84/151**. **Bara fyra** av de 35 historiska loppen har tillräckligt fullständig retrospektiv slutpool för en strikt ATG-jämförelse, så de resultaten har inte statistisk tyngd.

**Begränsningar:** Måttet beskriver motståndarnas historiska seger-/topp-3-andelar, inte deras verkliga klass i ett tränat ratingsystem. De gamla API-svaren hämtas i efterhand och daterade startresultat filtreras till dåtid; de utgör inte ursprungliga frysta förhandsdatabaser. Urval, saknad data och upprepade modellförsök på samma historiska lopp kan påverka siffrorna. Den förbättrade topp 3-träffen är en hypotes, **inte bevis på bättre spikar, skrällar eller spelvärde**.

**Beslut:** behåll nuvarande liveanalys och befintlig modell. Nästa validering måste använda nya, tidsstämplade V85-omgångar och förhandsstreck som sparas *före* spelstopp. Endast modellen med bevisad förbättring på osedd data bör få påverka råd eller kupong.

[Läs forskningssidan](https://biggles22.github.io/LA_V85/research/) · [Historiska as-of-källdata](https://github.com/Biggles22/LA_V85/blob/main/research/historical_opponent_asof_2026.json) · [Walk-forward-test](https://github.com/Biggles22/LA_V85/blob/main/research/historical_opponent_test_2026.json).
