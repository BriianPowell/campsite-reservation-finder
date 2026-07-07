# Campsite Reservation Finder

Automated campsite availability checks using [Camply](https://github.com/juftin/camply) and GitHub Actions.

The workflow runs short `search_once` Camply searches on a schedule. This is a better fit for GitHub Actions than `search_forever`, which is intended for an always-on machine.

## How It Works

1. GitHub Actions runs hourly, or whenever you start it manually.
2. Python installs `camply` from `requirements.txt`.
3. `scripts/run-searches.sh` runs each enabled YAML file in `searches/`.
4. Camply sends email notifications when it finds matching availability.

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

Tune `start_date`, `end_date`, `days`, and `nights` independently in each file. For example, desert searches can target cooler months while Yosemite and Sequoia searches can focus on summer and early fall.

Edit the new file with real Recreation.gov IDs and dates:

```yaml
provider: RecreationDotGov
recreation_area:
  - 2991
start_date: 2026-08-01
end_date: 2026-08-05
nights: 2
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
mailtos://_?smtp=smtp.mail.me.com&from=you@icloud.com&to=you@icloud.com&user=you@icloud.com&pass=APP_SPECIFIC_PASSWORD
```

Apple documents iCloud SMTP as `smtp.mail.me.com` on port `587` with SSL required. Apprise’s `mailtos://` uses STARTTLS on port `587`, which matches iCloud. Camply’s built-in `email` notifier uses implicit SSL and is not a good fit for iCloud SMTP.

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

Export `APPRISE_URL` if you want to test real notifications:

```bash
export APPRISE_URL="mailtos://_?smtp=smtp.mail.me.com&from=you@icloud.com&to=you@icloud.com&user=you@icloud.com&pass=APP_SPECIFIC_PASSWORD"
```

Run all enabled searches:

```bash
./scripts/run-searches.sh
```

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

The configured hooks validate YAML, catch merge conflict markers, enforce executable shebang consistency, trim trailing whitespace, normalize line endings, ensure files end with a newline, and syntax-check `scripts/run-searches.sh`.

## GitHub Actions Schedule

The workflow in `.github/workflows/camply-search.yml` runs hourly with:

```yaml
schedule:
  - cron: "0 * * * *"
```

GitHub cron schedules are evaluated in UTC. Adjust the cron expression if you only want checks during certain hours.
