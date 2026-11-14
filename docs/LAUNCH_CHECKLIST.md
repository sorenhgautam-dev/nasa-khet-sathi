# Launch checklist

The live site must work, unchanged, until the winners are announced in January. That means no outside requests,
nothing to fix later, and nothing pushed after submission. Hosting is Vercel: static files from `site/`, no build
step, no functions and no environment variables (CLAUDE.md "Hosting").

## 1. Before the push (the owner, on the main laptop)

1. [ ] Run `.venv/bin/python scripts/final_check.py`. It runs everything and prints one RESULT line:
   - it writes the version stamp `site/data/version.json`;
   - the full test suite;
   - `validate --final`;
   - `check_site --final`;
   - no outside requests at runtime;
   - the secrets scan.

   Push only if it says **RESULT: PASS**.
2. [ ] Read any FAIL lines. Fix them, then run it again.
3. [ ] Commit everything, including `site/data/version.json`. The stamp names the commit it was made at, so the
       pushed commit is the next one.
4. [ ] Push (the owner only, golden rule 2).

## 2. Vercel settings (check once, in the Vercel project)

- [ ] Root Directory: `site/`
- [ ] Framework Preset: **Other**
- [ ] Build Command: **empty**. Install Command: **empty**.
- [ ] Environment Variables: **none**
- [ ] No `api/` folder, no middleware, no `package.json` in `site/` (`check_site.py` checks this)
- [ ] The newest deployment is the **Production** one, and it is "Ready"

## 3. After the deploy (laptop)

- [ ] Run `.venv/bin/python scripts/final_check.py --live https://<live address> --live-only`. Every file the site
      publishes is downloaded and compared byte for byte with the checked local files. It must say **RESULT: PASS**.
- [ ] In desktop Chrome, open the live address and open DevTools, then Network. Reload. Type `-domain:<live address
      host>` in the filter: **the list must be empty** (no fonts, maps or scripts from other sites).
- [ ] In DevTools, Network: the first screen loads under 300 KB.

## 4. Phone checks (at least one iPhone with Safari and one Android with Chrome)

Use a phone that **has never opened the site** (or a private tab), on **mobile data** (Wi-Fi off), **not signed in**
to Vercel.

- [ ] The live address opens. The first screen is in Nepali.
- [ ] Tap **English**: the words change. Tap back to Nepali. The Nepali letters show properly (no empty boxes).
- [ ] "Try our demo field" opens the demo field. The map shows the **NASA picture** (brown and green valley), not a
      street map and not a grey box.
- [ ] Each prepared field in the list opens: demo, sample-1, sample-2, sample-3, sample-4 (and every field added
      later).
- [ ] Every screen of the demo field opens:
  - Home;
  - Where is your field;
  - From space;
  - Your field in small parts;
  - Let's check the soil;
  - the last years;
  - What should I grow (three plans, five tabs);
  - 2040;
  - Your plan;
  - How we know.
- [ ] "Let's check the soil":
  - before the replay exists, it says "not ready yet" kindly;
  - after `probe_log.json` exists, the replay plays and says "recorded on <date>".
- [ ] How we know shows the version (the `commit_short` in `site/data/version.json`) and its date.
- [ ] Mark a field far away (another country): you get a friendly message, not an error.
- [ ] **Airplane mode after load.**
  - Open the demo field and visit every screen once, then turn on airplane mode.
  - Go through the screens again.
  - Nothing crashes. A screen that cannot load a file says so in plain words.
- [ ] Turn the phone sideways and back: nothing breaks. Buttons are easy to tap.
- [ ] A draft language (for example Hindi) shows its "draft translation" label.

## 5. Submit and freeze

- [ ] Paste the live link and the repository link into the Space Apps project page, and submit.
- [ ] **After submission, push nothing to the connected branch.** Every push redeploys the live site. Or switch off
      automatic deployments in Vercel.
- [ ] Once a week until January, open the live address on a phone. Optionally run
      `final_check.py --live <address> --live-only` again.
