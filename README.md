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

Or start from a provider-specific template:

```bash
cp searches/recreation-dot-gov.disabled.yaml searches/recreation-dot-gov.yaml
cp searches/reserve-california.disabled.yaml searches/reserve-california.yaml
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
notifications: email
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

Add these repository secrets before enabling email notifications:

- `EMAIL_TO_ADDRESS`
- `EMAIL_USERNAME`
- `EMAIL_PASSWORD`

Optional email secrets supported by Camply:

- `EMAIL_FROM_ADDRESS`
- `EMAIL_SUBJECT_LINE`
- `EMAIL_SMTP_SERVER`
- `EMAIL_SMTP_PORT`

For Gmail, `EMAIL_USERNAME` is usually your email address and `EMAIL_PASSWORD` should be an app password, not your normal account password.

You can set secrets with the GitHub CLI from this repository after creating the GitHub repo:

```bash
gh secret set EMAIL_TO_ADDRESS
gh secret set EMAIL_USERNAME
gh secret set EMAIL_PASSWORD
```

## Run Locally

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Export email settings if you want to test real notifications:

```bash
export EMAIL_TO_ADDRESS="you@example.com"
export EMAIL_USERNAME="you@example.com"
export EMAIL_PASSWORD="your-app-password"
```

Run all enabled searches:

```bash
./scripts/run-searches.sh
```

Test Camply's email notification setup directly:

```bash
camply test-notifications --notifications email
```

## GitHub Actions Schedule

The workflow in `.github/workflows/camply-search.yml` runs hourly with:

```yaml
schedule:
  - cron: "0 * * * *"
```

GitHub cron schedules are evaluated in UTC. Adjust the cron expression if you only want checks during certain hours.
