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
