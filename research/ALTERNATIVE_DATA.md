# Alternativa historiska datakällor, 1 november 2026

> Uppdatering 2 november: 145 av de 147 V85-lopp som beskrivs som spärrade nedan har nu återställts direkt från ATG:s råsvar. Det separata alternativarkivet beskrivs här som historisk dokumentation. [Aktuell datakontroll och återhämtning](DATA_QUALITY.md).

**Vi har hämtat ett redan publicerat rådataarkiv från GitHub och byggt en separat resultatfil med 1 050 svenska travlopp och 11 220 aktiva starter.** Det är ett underlag för att bygga historiska variabler och nya modellförsök. Det ersätter inte de 147 spärrade V85-loppen och är inte kopplat till sajtens tips eller befintliga modellrapporter.

## Källor och faktisk täckning

| Publicerad källa | Hämtat material | Bedömning |
| --- | --- | --- |
| [lbondarenko/travmodel, låst version](https://github.com/lbondarenko/travmodel/tree/de68577d26a3384e0e16d38bbe650297cc586c77/data/games_hist) | 263 komprimerade spelomgångar med råa startfält och resultat | 1 042 svenska travlopp klarar resultatkontrollen. Period januari–juli 2026. |
| [jojo-swe/trav-mvp, rå V85-omgång](https://github.com/jojo-swe/trav-mvp/blob/b937891915b985a48152cbe74ceb9f4c6ec3d47d/data/game_V85_2025-10-25.json) | En rå omgång från Jägersro 25 oktober 2025 | Ytterligare åtta kompletta lopp. |
| [jojo-swe/trav-mvp, starter-CSV](https://github.com/jojo-swe/trav-mvp/blob/b937891915b985a48152cbe74ceb9f4c6ec3d47d/data/atg_starters.csv) | 68 156 rader, 7 079 lopp, 10 oktober 2025–7 oktober 2026 | Hämtad och granskad, men underkänd som källa till kompletta träningsfält. |

Källorna är tidigare publicerade filer, inte nya ATG-anrop via en mellanhand. Inga externa insamlingsskript har körts. Direkta ATG- och Svensk Travsport-anrop nekas fortfarande av miljöns nätverkspolicy. Uppgifterna har kontrollerats mot de publicerade filerna, inte verifierats på nytt direkt hos ATG.

De 264 omgångarna innehåller totalt 1 630 lopp. Resultatkontrollen väljer svenska sulkylopp med 6–20 aktiva hästar, unika identiteter, kända resultat för samtliga aktiva och exakt en vinnare. **566 lopp med annan sport eller annat land, sex lopp utan entydig vinnare, sju med avvikande fältstorlek och ett med okänt resultat** hålls utanför resultatfilen. Strukna räknas separat; diskvalificerade aktiva hästar tas med.

De 1 050 godkända resultatfälten fördelas på **180 GS75, 622 V64, 176 V65, 64 V86 och åtta V85**. Datumintervallet är 25 oktober 2025–22 juli 2026; det är ett urval med luckor, inte heltäckande svensk travhistorik.

## Varför den stora CSV-filen inte löser problemet

CSV:n innehåller samma lopp-ID som **124 av våra 147 spärrade lopp**, men det bevisar inte att fälten är kompletta. Den publicerade [parsern](https://github.com/jojo-swe/trav-mvp/blob/b937891915b985a48152cbe74ceb9f4c6ec3d47d/scripts/fetch_atg_sample.py#L231) tar bort starter utan `result.place` och räknar därefter `field_size` på de kvarvarande raderna.

Jämförelsen med råarkivet visar **609 ofullständiga CSV-fält av 1 049 jämförbara lopp, sammanlagt 940 saknade aktiva starter**. Identiteter och vinnaretiketter för de gemensamma raderna stämmer i denna jämförelse. Problemet är hästarna som saknas. Varken filens storlek eller dess egen fältstorlek ger därför tillräckligt stöd för träning.

`market_share_pool` är dessutom en blandning: parsern använder normaliserade vinnarodds när poolstreck saknas. CSV:ns råa streckkolumn är tom i alla 68 156 rader. Dessa värden ska inte tolkas som V85-streck. Förberäknade livstids-/årsstatistikvärden har inte verifierad observationstid före respektive lopp och används inte.

## Vad resultatfilen kan och inte kan användas till

- Den ger fullständiga resultatfält enligt ovanstående kontroller, häst-/kusk-/tränar-ID, distans, startspår, strykningar, vinnaretiketter och källhänvisning per lopp.
- Form, historisk segerandel, distansvana och motståndarvariabler kan byggas från strikt tidigare tävlingsdatum i arkivet. Luckor i historiken måste redovisas. Dagens livstidsstatistik ska inte användas för historiska prognoser.
- Det finns **2 264 uttryckliga galoppmarkeringar och 8 956 okända galoppstatusar**. Saknad flagga betyder inte galoppfri start. En tillförlitlig galoppfrekvens kan därför inte räknas genom att fylla luckorna med noll.
- Marknadsuppgifterna kommer från historiska resultatsvar och har märkningen `historical_result_payload_not_prestart`. De är inte tidsstämplade förhandsstreck. Speltypen sparas; V64- och V86-streck får inte behandlas som V85-streck.
- Inget av råarkivets lopp överlappar de 147 spärrade V85-loppen. Dessa förblir spärrade. Fullständiga tidigare starter per häst från `/extended` saknas också.
- CatBoost/XGBoost måste utvärderas kronologiskt, med separat redovisning per speltyp. Åtta V85-lopp räcker inte för att avgöra vilken modell som hittar V85-skrällar bäst.

## Sparade filer och reproduktion

Rådata och den cirka 4 MB stora resultatfilen finns lokalt i molnmiljön:

```text
/workspace/.onboarding/alternate-data/travmodel-source.tar.gz
/workspace/.onboarding/alternate-data/game_V85_2025-10-25.json
/workspace/.onboarding/alternate-data/jojo-starters.csv
/workspace/.onboarding/alternate-data/verified/verified-results.jsonl
/workspace/.onboarding/alternate-data/verified/audit.json
```

[Den publicerade sammanställningen](public_archive_audit_2026.json) innehåller källornas låsta Git-commit, URL, SHA-256, urval, felantal och resultatfilens hash. Den fullständiga lokala rapporten listar även exkluderade lopp och varje jämförelse med CSV:n. Resultatfilens SHA-256 är `2d6a671ce1c378cf3808dd576e19e4443a1e8e6cd1449040b09b1d4efe4ecb64`.

Kör kontrollen utan nätverk från repots rot:

```sh
python scripts/audit_public_archive.py \
  --archive /workspace/.onboarding/alternate-data/travmodel-source.tar.gz \
  --sample-game /workspace/.onboarding/alternate-data/game_V85_2025-10-25.json \
  --csv /workspace/.onboarding/alternate-data/jojo-starters.csv \
  --output /workspace/.onboarding/alternate-data/verified
```

Programmet kontrollerar källhasharna före bearbetning och avbryter om filerna har ändrats. Det importerar ingen tredjepartskod och skriver ingen `historical_pilot_v2.json`. Resultatfilen är ett separat format för vidare bearbetning, inte färdiga modellindata.

Råfilerna återpubliceras inte i LA_V85; någon uttrycklig licens för vidare spridning har inte fastställts. Källförteckning, kontrollprogram, tester och sammanställning finns i repot. Alla 108 Python-tester passerar, inklusive kontroller för okända resultat, strykningar, dött lopp, dubbla identiteter, CSV-bortfall och ändrade källfiler.
