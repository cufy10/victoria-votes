# Victoria Votes 2026

The data pipeline behind the Victoria Votes 2026 election website.

## Run it by hand

    python3 update.py

It takes about 40 seconds and writes `out/index.html` (the website file) and `out/last_run.json` (a summary).
It needs internet access to read Wikipedia. Nothing is published by this script.

## What it does

1. Fetches the latest polls, election page and candidate page from Wikipedia (`data/polls.txt`, `main.txt`, `cands.txt`).
2. Parses every dated 2026 statewide poll.
3. Collects the newest news headlines cited on those pages.
4. Runs the seat model once per poll, builds a daily history of projected seats, and blends the pollsters by trust
   (recent polls count more, bigger samples count more, party-paid polls count half).
5. Fills `template.html` with the data and writes `out/index.html`.

If a safety check fails (fewer than 20 polls parsed, newest poll over 30 days old, seat totals wrong) it stops and writes nothing.

## Daily schedule

A scheduled task called "Victoria Votes daily update" runs at about 7:10 am every day. It runs `update.py`, then republishes
`out/index.html` to the existing website link. The computer must be awake and the Claude app open at that time;
if not, the task runs when the app next opens. After 29 November 2026 the task reports that the election has passed.

## Files

- `update.py` runs everything.
- `template.html` is the website design.
- `data/` holds the model, boundaries, 2022 results, the official VEC candidate lists and the saved Wikipedia pages.
- `out/` holds the finished website file.

## Known limits

- Polls and 2022 results come from Wikipedia, not directly from the VEC. Candidate lists come from the VEC (checked 21 Nov 2026).
- Win likelihoods are model estimates. Preference flows and One Nation's spread across seat types are assumptions.
- Two candidates dropped by their parties (Williamstown, Bendigo West) are noted by hand in `data/post.py`.
