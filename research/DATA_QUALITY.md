# Utökad ATG-historik 2 november 2026

**Aktuellt underlag: 1 047 lopp och 12 247 starter.** ATG:s kalender har kontrollerats för samtliga 148 lördagar från januari 2024 till oktober 2026. 145 omgångar hittades; de tre midsommarlördagarna saknade V75/V85. Av 1 068 hämtade lopp klarar 1 047 modellens kontroller: 634 V75-lopp och 413 V85-lopp. Alla 196 tidigare godkända lopp finns kvar, med 851 nya. Underlaget omfattar 81 lopp på Bergsåker.

21 lopp används inte: 14 med okända resultat, tre med dött lopp, tre montélopp och ett lopp med fem aktiva hästar. Modellen är avgränsad till vanliga travlopp med 6–20 aktiva hästar. Resultat saknas aldrig tyst som en antagen förlust.

[Insamlingsrapport](history_expansion_2026.json) · [Utökad träningsdata](historical_expanded_2024_2026.json) · [Aktuell utvärdering](expanded_model_evaluation_2026.json) · [Aktuell datakontroll](training_data_quality_2026.json).

Samtliga 1 361 källsvar är sparade med källa, hämtningstid och kontrollsumma. Nya råsvar är komprimerade utan informationsförlust. En ombyggnad utan nätverk gav identisk SHA-256 för träningsfilen. Den utökade tidskontrollen visar 3 089 förenliga övergångar av karriärstarter/segrar i 3 093 jämförbara par; fyra avvikelser finns dokumenterade. Karriärstatistik används fortsatt inte som modellvariabler. V75 och V85 får ingå i träningen, medan de aktuella testmåtten enbart avser senare V85-lopp.

    python -m scripts.expand_historical --offline
    python -m scripts.audit_historical_asof --expanded
    python -m scripts.data_quality
    python -m scripts.rank_current_catboost

## Föregående återhämtning samma dag

**Återhämtningen är genomförd:** 200 lopp från 25 V85-omgångar har hämtats som 225 råsvar. **196 lopp och 2 307 aktiva starter** klarar träningskontrollen. Av de tidigare 147 spärrade loppen har 145 återställts; alla 31 tidigare godkända lopp finns kvar och 20 kompletta lopp har tillkommit. Två lopp har okända resultat och två har dött lopp, vilket vinnarmodellen inte stöder. Dessa fyra lopp används inte i träningen.

[Återhämtningsrapport](history_recovery_2026.json) · [Aktuell datakontroll](training_data_quality_2026.json) · [Kontroll av historiska statistikövergångar](historical_asof_audit_2026.json) · [Aktuell CatBoost-modell](CURRENT_MODEL.md).

Råsvaren sparas med källa, hämtningstid och innehållshash. En full ombyggnad utan nätverk har gett samma SHA-256 för träningsfilen. I 385 kontrollerbara par av på varandra följande starter stämmer ökningen av karriärstarter och segrar med det mellanliggande loppet. Det stödjer att just dessa fält är tidsriktiga i urvalet, men bevisar inte att alla fält är frysta. Karriärstatistik används därför ännu inte som modellvariabler.

Följande beskriver utgångsläget den 1 november och de kontroller som fortsatt gäller.

Historiska råsvar saknas i den äldre databasen. Aggregerade galoppvärden kan därför inte repareras säkert i efterhand. ATG-åtkomst behövs för att hämta om de ursprungliga loppen. Tidigare databas, modellrapporter och frysta prognoser bevaras oförändrade som historisk dokumentation.

**Alternativ datakälla hittad:** ett redan publicerat GitHub-arkiv ger en separat resultatbas med 1 050 svenska travlopp och 11 220 aktiva starter. Det innehåller inte de 147 spärrade V85-loppen och ersätter inte denna databas. Se [källor, kontroller och begränsningar](ALTERNATIVE_DATA.md).

## Vad som är rättat

- `galloped: true` och `galloped: false` är de enda godkända galoppobservationerna. Saknade värden och okända koder förblir okända. Diskvalifikation är en separat uppgift; `disqualified: false` betyder inte galoppfri start. En bekräftad diskvalifikation räknas inte som en tidigare seger.
- Startfältet byggs av samtliga identifierade aktiva hästar innan resultat läses. Saknad placering tar inte bort hästen eller ändrar fältstorlek och relativa förhandsvariabler.
- Varje lopp har separata antal anmälda, aktiva, strukna, resultatverifierade och resultatokända hästar. Resultattäckningen har aktiva hästar som nämnare.
- Ett uttryckligt oplacerat resultat eller en bekräftad diskvalifikation kan ge en förlustetikett. Okänt eller motsägelsefullt resultat ger `winner: null`. Dött lopp stöds inte av denna vinnarmodell.
- Samtliga träningsvägar använder samma kvalitetskontroll. Hela lopp med osäker identitet, okända resultat eller tvetydig täckning hålls utanför träningen. Dessa hästar behandlas inte som förlorare.
- Rådata sparas från och med den nya importen med källa, hämtningstid och SHA-256. De kan kontrolleras och bearbetas igen utan nätverk. Inga råsvar har återskapats från aggregat.

## Äldre underlag före återhämtningen

Den äldre databasen omfattar 178 lopp och 1 931 häststarter. **31 lopp med 354 starter** har full registrerad täckning, konsekventa startfält och en entydig vinnare. Dessa kan användas för begränsade forskningsförsök, med äldre galoppvärden avstängda. **43 tidigare numeriska galoppvärden** i detta delurval har ersatts av okänt i modellernas indata; källfilen är bevarad.

**147 lopp spärrades** i den äldre filen tills rådata kunde verifieras. Den gamla täckningssiffran blandade strykningar med saknade resultat. Återhämtningen ovan använder nya råsvar, inte baklängesberäkning av de äldre aggregaten.

Även det utökade underlaget är selekterat. Galoppvariabeln är fortsatt avstängd i den aktuella CatBoost-modellen. Marknadsandelarna är historiska slutstreck, inte ursprungliga förhandssnapshots.

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
python -m scripts.recover_historical --offline
python -m scripts.audit_historical_asof
```

Push-kontrollerna gör ingen automatisk ATG-insamling. En uttrycklig manuell insamling kan väljas i historical-pilot-flödet. Publicering av rapporter avbryts om GitHubs main har förändrats under körningen, så att parallellt arbete inte skrivs över. Tidigare antalsregler som vägrade ersätta en stor rapport med ett mindre men korrekt test används inte för v2.

## Regressioner som kontrolleras

Tester täcker bland annat återhämtad galopp med seger, diskvalifikation utan galoppuppgift, okända booleska flaggor, oförändrade förhandsvariabler när ett resultat försvinner, strykningar, oplacerade och okända resultat, dött lopp, dubbla identiteter, spärrning av hela lopp, idempotent sanering, källhashar och verifierad läsning utan nätverk. Testernas konstgjorda lopp används aldrig som publicerad historik.
