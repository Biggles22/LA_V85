# Weekly comparison reports — V75travet.se

The Codex automations in the owning chat run prestart Thursday/Friday 20:00 and Saturday 12:00, then post-race Saturday 21:00 Europe/Stockholm. Execution is scheduled, not a promise that upstream results exist at 21:00. Work on the current remote main, preserving unrelated changes. This is the existing GitHub Pages site, not a new Sites-hosted project.

## Evidence and freezing

Save timestamped, immutable prediction records under `research/comparison/YYYY-MM-DD/`. Use the same Saturday comparison window for both CatBoost variants, the market baseline and external sources. Retain actual capture times, ATG game/race/horse identities, source URLs and model version. Record both the source publication timestamp and capture timestamp when available. Never backdate or overwrite a frozen forecast. A page visible only after betting closes is not proof of a prestart prediction. Record missing/access-restricted/not-published sources explicitly; never register, subscribe or pay without authorization.

Track: V75travet.se historical CatBoost; experimental expanded CatBoost (clearly labelled); market top three at capture time; Travmaskinen; Travtips AI; V46; Tipper Trav; Travia AI; Travtipsaren; ATG Elli; Simsalabim Heat Rank. Respect the source's actual method. Do not turn unordered selections into an invented top three or a numerical index into a calibrated probability. Store attributable normalized picks and evidence; do not republish full third-party articles or private credentials. Multiple versions of the same source are not independent competitors.

## Post-race report

At Saturday 21:00 verify the official ATG results and matching round (V85 eight legs or V75 seven). Leave missing/pending results visible rather than inventing numbers. Write a separate static `efteranalys/YYYY-MM-DD/index.html` document, replacing only that date's pending notice. Add its link and status to the archive in `efteranalys/index.html`. Reuse reports.css, branding and shared navigation; the homepage already links to the archive. Mark provisional reports, corrections and their publication dates. Preserve the original frozen predictions.

Include: cutoff/capture times; source/data coverage; winner per leg; source-by-source first-choice/top-three hits with denominators; explicit spik/outsider hits with number proposed; disagreements between our models; missing/late/unavailable sources; lessons; separate cumulative statistics. Count a dead-heat race once if any accepted winner is selected, disclose it, and never double-count the race. Use exactly three unique ordered selections per scored top-three race; otherwise mark that metric incomparable or missing. Match races and timestamps before comparing percentages, and report the paired denominator. Preserve honest zeroes.

For financial comparisons require an actual frozen full system, stake fraction, unit price, budget and official payouts. If systems differ in budget, show them separately rather than rank their raw payouts. Do not reconstruct a winning system after the outcome, infer ROI from top-three hits, or claim general profitability from a few rounds. Missing systems => unavailable financial comparison. Spik threshold (>50% assessed chance) is user policy, not a threshold on raw CatBoost scores or inverse odds. Uncalibrated probabilities => no calibration claim.

Run relevant tests, validate links/mobile layout, commit only report-related work, push to the existing main branch and verify the deployed document. The user explicitly authorized weekly publication to V75travet.se in this chat. No bets or financial transactions.
