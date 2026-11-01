# Datarättning 1 november 2026

Historiska råsvar saknas i den äldre databasen. Aggregerade galoppvärden kan därför inte repareras säkert i efterhand. ATG-åtkomst behövs för att hämta om de ursprungliga loppen. Tidigare databas, modellrapporter och frysta prognoser bevaras oförändrade som historisk dokumentation.

**Alternativ datakälla hittad:** ett redan publicerat GitHub-arkiv ger en separat resultatbas med 1 050 svenska travlopp och 11 220 aktiva starter. Det innehåller inte de 147 spärrade V85-loppen och ersätter inte denna databas. Se [källor, kontroller och begränsningar](ALTERNATIVE_DATA.md).

## Vad som är rättat

- `galloped: true` och `galloped: false` är de enda godkända galoppobservationerna. Saknade värden och okända koder förblir okända. Diskvalifikation är en separat uppgift; `disqualified: false` betyder inte galoppfri start. En bekräftad diskvalifikation räknas inte som en tidigare seger.
- Startfältet byggs av samtliga identifierade aktiva hästar innan resultat läses. Saknad placering tar inte bort hästen eller ändrar fältstorlek och relativa förhandsvariabler.
- Varje lopp har separata antal anmälda, aktiva, strukna, resultatverifierade och resultatokända hästar. Resultattäckningen har aktiva hästar som nämnare.
- Ett uttryckligt oplacerat resultat eller en bekräftad diskvalifikation kan ge en förlustetikett. Okänt eller motsägelsefullt resultat ger `winner: null`. Dött lopp stöds inte av denna vinnarmodell.
- Samtliga träningsvägar använder samma kvalitetskontroll. Hela lopp med osäker identitet, okända resultat eller tvetydig täckning hålls utanför träningen. Dessa hästar behandlas inte som förlorare.
- Rådata sparas från och med den nya importen med källa, hämtningstid och SHA-256. De kan kontrolleras och bearbetas igen utan nätverk. Inga råsvar har återskapats från aggregat.

## Befintligt underlag

Den äldre databasen omfattar 178 lopp och 1 931 häststarter. **31 lopp med 354 starter** har full registrerad täckning, konsekventa startfält och en entydig vinnare. Dessa kan användas för begränsade forskningsförsök, med äldre galoppvärden avstängda. **43 tidigare numeriska galoppvärden** i detta delurval har ersatts av okänt i modellernas indata; källfilen är bevarad.

**147 lopp spärras** tills rådata kan verifieras. Den gamla täckningssiffran blandar strykningar med saknade resultat, så vi kan inte säkert skilja dessa fall genom att räkna baklänges. Kvalitetsrapporten listar varje spärrat lopp och orsak.

Detta är ett begränsat, selekterat underlag. Varken gallopprisken eller de fullständiga äldre startfälten har påståtts vara återhämtade. Även marknadsandelarna är historiska slutstreck, inte ursprungliga förhandssnapshots.

## Körning och återhämtning

Kvalitetskontroll och tester använder sparade filer och kräver ingen nätåtkomst:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_*.py'
python scripts/data_quality.py
python scripts/train_historical_pilot.py
python scripts/walkforward_evaluation.py
python scripts/catboost_trial.py
```

Nya resultat skrivs till `*_v2.json`. För små testmängder skrivs som `status: insufficient_data`, utan prestationsmått. Felaktiga data eller programfel ger fortsatt felstatus. Den äldre forskningssidan är märkt som historisk; Metod & resultat visar datakontroll och jämförelsen efter rättningen.

När `www.atg.se` är tillåtet av miljöns aktiva nätverksregler:

```sh
python scripts/historical_pilot.py
python scripts/data_quality.py
python scripts/train_historical_pilot.py
python scripts/walkforward_evaluation.py
python scripts/catboost_trial.py
```

Importen skriver den separata filen `research/historical_pilot_v2.json`. Inga äldre aggregat blandas in i det nya rådatabaserade materialet. Kompletta råsvar sparas i `research/raw-history/`; även dessa ska bevaras vid publicering. Nätverks- och schemafel ger diagnostik och ersätter inte befintliga källdata med tomma filer.

För ombearbetning av redan hämtade svar:

```sh
python scripts/historical_pilot.py --offline
```

Push-kontrollerna gör ingen automatisk ATG-insamling. En uttrycklig manuell insamling kan väljas i historical-pilot-flödet. Publicering av rapporter avbryts om GitHubs main har förändrats under körningen, så att parallellt arbete inte skrivs över. Tidigare antalsregler som vägrade ersätta en stor rapport med ett mindre men korrekt test används inte för v2.

## Regressioner som kontrolleras

Tester täcker bland annat återhämtad galopp med seger, diskvalifikation utan galoppuppgift, okända booleska flaggor, oförändrade förhandsvariabler när ett resultat försvinner, strykningar, oplacerade och okända resultat, dött lopp, dubbla identiteter, spärrning av hela lopp, idempotent sanering, källhashar och verifierad läsning utan nätverk. Testernas konstgjorda lopp används aldrig som publicerad historik.
