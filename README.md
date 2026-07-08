# Campsite Reservation Finder

Automated campsite availability checks using [Camply](https://github.com/juftin/camply) and GitHub Actions.

The workflow runs short `search_once` Camply searches on a schedule. This is a better fit for GitHub Actions than `search_forever`, which is intended for an always-on machine.

## How It Works

1. GitHub Actions runs hourly, or whenever you start it manually.
2. Python installs `camply` from `requirements.txt`.
3. `python scripts/run_searches.py` runs the grouped search runner.
4. The runner searches each enabled YAML file in `searches/`.
5. Matching campsites are grouped into one Apprise notification per search config.

`searches/example.yaml` is a template and is skipped by the runner. Provider-specific templates ending in `.disabled.yaml` are also skipped until you rename them. Enabled search configs are split by area so each region can have its own season and date window.

## Configure A Search

Copy the example config:

```bash
cp searches/example.yaml searches/my-trip.yaml
```

The current enabled searches are organized by area:

```text
searches/
  recreation-yosemite.yaml
  recreation-sequoia-kings.yaml
  recreation-joshua-tree.yaml
  recreation-mojave.yaml
  recreation-big-sur-inyo.yaml
  reserve-california-coast.yaml
  reserve-california-desert.yaml
```

Tune `start_date`, `end_date`, and `nights` independently in each file. The current configs use explicit Thursday-to-Sunday windows: each `start_date` entry is a Thursday arrival, and the matching `end_date` entry is the Sunday checkout date. For example, desert searches can target cooler months while Yosemite and Sequoia searches can focus on summer and early fall.

Edit the new file with real Recreation.gov IDs and dates:

```yaml
provider: RecreationDotGov
recreation_area:
  - 2991
start_date:
  - 2026-08-06
end_date:
  - 2026-08-09
nights: 3
notifications: apprise
search_once: true
continuous: false
search_forever: false
```

You can use one of these target fields:

- `recreation_area` for broad searches across a Recreation.gov area.
- `campgrounds` for one or more campground IDs.
- `campsites` for exact campsite IDs. Camply treats this as the most specific target.

Disable a search by renaming it to end with `.disabled.yaml`, for example `searches/my-trip.disabled.yaml`.

When using multiple date windows, keep `start_date` and `end_date` lists the same length. Camply pairs them by position:

```yaml
start_date:
  - 2026-08-06
  - 2026-08-13
end_date:
  - 2026-08-09
  - 2026-08-16
nights: 3
```

Do not combine `days: Thursday` with `nights: 3`; Camply filters the search dates down to Thursdays before checking consecutive nights, which prevents true Thu-Sun matching.

Find provider IDs with Camply:

```bash
camply recreation-areas --provider RecreationDotGov --search "Yosemite"
camply campgrounds --provider RecreationDotGov --search "Upper Pines"
camply recreation-areas --provider ReserveCalifornia --search "Los Angeles"
camply campgrounds --provider ReserveCalifornia --search "Sonoma Coast"
```

## GitHub Secrets

Add this repository secret before enabling notifications:

- `APPRISE_URL`

For iCloud Mail, use an app-specific password and Apple’s SMTP server with Apprise’s STARTTLS email URL:

```text
mailtos://icloud.com?user=you%40icloud.com&pass=APP_SPECIFIC_PASSWORD&smtp=smtp.mail.me.com&from=you%40icloud.com&to=you%40icloud.com
```

Apple documents iCloud SMTP as `smtp.mail.me.com` on port `587` with SSL required. Apprise’s `mailtos://` uses STARTTLS on port `587`, which matches iCloud. Camply’s built-in `email` notifier uses implicit SSL and is not a good fit for iCloud SMTP. URL-encode `@` as `%40` in email address parameters, and use an iCloud app-specific password with no spaces.

You can set secrets with the GitHub CLI from this repository after creating the GitHub repo:

```bash
gh secret set APPRISE_URL
```

## Run Locally

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` installs `camply[apprise]` so Camply can load the Apprise notification backend.

Export `APPRISE_URL` if you want to test real notifications:

```bash
export APPRISE_URL="mailtos://icloud.com?user=you%40icloud.com&pass=APP_SPECIFIC_PASSWORD&smtp=smtp.mail.me.com&from=you%40icloud.com&to=you%40icloud.com"
```

Run all enabled searches:

```bash
python scripts/run_searches.py
```

The runner forces Camply searches to use `silent` notifications, then sends one formatted Apprise message per search config when matches are found. This avoids one email per campsite and keeps related availability grouped together.

The runner also deduplicates notifications using `.cache/camply-notifications.json`. A campsite is only notified once every 3 days for the same search config, campsite ID, facility ID, arrival date, and checkout date. GitHub Actions restores and saves `.cache` with `actions/cache`, so repeated hourly runs should not resend the same availability until the 3-day reminder window expires. Override the local state path with `STATE_FILE=/path/to/state.json` if needed.

Test Camply's Apprise notification setup directly:

```bash
camply test-notifications --notifications apprise
```

## Pre-Commit Checks

Install the git hooks after installing dependencies:

```bash
pre-commit install
```

Run all checks manually:

```bash
pre-commit run --all-files
```

The configured hooks validate YAML, catch merge conflict markers, enforce executable shebang consistency, trim trailing whitespace, normalize line endings, ensure files end with a newline, and compile-check `scripts/run_searches.py`.

## GitHub Actions Schedule

The workflow in `.github/workflows/camply-search.yml` runs every 3 hours with:

```yaml
schedule:
  - cron: "0 */3 * * *"
```

GitHub cron schedules are evaluated in UTC. Adjust the cron expression if you only want checks during certain hours.

The workflow also caches `.cache/` so the 3-day notification dedupe state survives between scheduled runs.

If one search config fails because a provider endpoint rejects or rate-limits the request, the runner logs a GitHub Actions warning and continues with the remaining configs. This keeps successful search notification state from being lost because of one provider-specific failure.
