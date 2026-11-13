# Notice for `dhm_onset_dates.csv`

The dates in `dhm_onset_dates.csv` are (c) Department of Hydrology and Meteorology (DHM), Government of Nepal. They
are copied, with attribution, from Table 1 (p. 3) of DHM Climate Division (Climate Analysis Section), "Monsoon Onset
and Withdrawal date information" (1968-2024; PDF created 2024-10-20):
https://www.dhm.gov.np/uploads/dhm/climateService/monsoon_onset_and_withdrawal_dates_english3.pdf (read 2026-11-14).
Each date is the day the monsoon entered (onset) or left (withdrawal) **eastern Nepal**. It reaches Kathmandu a few
days later. Every row names its document and page; the 1980 withdrawal is printed as "--" (record is not available).

Use in this repository: the record of whether the monsoon's start has shifted (`diary.shift_days`), the usual start
window and the late years (owner, 2026-11-14; `config/rules.yaml` `monsoon_onset_dhm`), and the sanity window of the
second onset measure (`onset_accumulation`).

DHM states no open licence for this table. It is **not covered by this repository's MIT licence** (see `LICENSE`,
"What this licence does not cover"). To reuse it, ask DHM: https://www.dhm.gov.np

Kept in the repository with this notice on the pattern the owner approved for `dhm_normals_1991_2020.csv`
(2026-11-13, REVIEW_2, answer 13).
