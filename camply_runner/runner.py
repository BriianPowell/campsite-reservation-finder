from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from camply_runner.campsites import notification_key, word
from camply_runner.config import ConfigError, RunnerConfig
from camply_runner.notifications import AppriseNotifier, NotificationError
from camply_runner.search import CamplySearchClient
from camply_runner.state import NotificationStateStore


class SearchRunner:
    def __init__(
        self,
        config: RunnerConfig,
        search_client: CamplySearchClient | None = None,
        state_store: NotificationStateStore | None = None,
        notifier: AppriseNotifier | None = None,
    ) -> None:
        self.config = config
        self.search_client = search_client or CamplySearchClient()
        self.state_store = state_store or NotificationStateStore(
            state_file=config.state_file,
            notification_ttl=config.notification_ttl,
        )
        self.notifier = notifier or AppriseNotifier(config.apprise_url)

    def run(self) -> int:
        ran_search = False
        failed_configs: list[str] = []
        now = datetime.now(timezone.utc)
        notified_at_by_key = self.state_store.load(now=now)

        for config_file in self.search_client.iter_configs(self.config.search_dir):
            ran_search = True
            search_name = config_file.stem
            print(f"Running Camply search config: {config_file.name}")
            try:
                matches = self.search_client.run_search(config_file)
            except Exception as error:
                failed_configs.append(config_file.name)
                print_search_warning(config=config_file, error=error)
                continue

            new_matches = [
                campsite
                for campsite in matches
                if notification_key(search_name=search_name, campsite=campsite)
                not in notified_at_by_key
            ]

            if not matches:
                print(f"No matching campsites found for {config_file.name}")
                continue

            if not new_matches:
                print(
                    f"No new matching campsites found for {config_file.name} "
                    f"({len(matches)} already notified in the last 3 days)."
                )
                continue

            print(
                f"Sending grouped notification for {config_file.name}: "
                f"{len(new_matches)} new {word(len(new_matches), 'match', 'matches')}"
            )
            if not self.notifier.notify_matches(
                search_name=search_name,
                matches=new_matches,
                total_matches=len(matches),
            ):
                print(
                    f"Failed to send Apprise notification for {config_file.name}",
                    file=sys.stderr,
                )
                return 1

            for campsite in new_matches:
                notified_at_by_key[
                    notification_key(search_name=search_name, campsite=campsite)
                ] = now
            self.state_store.save(notified_at_by_key=notified_at_by_key)

        if not ran_search:
            print(f"No enabled search configs found in {self.config.search_dir}.")
            print(
                "Copy searches/example.yaml to a new filename and fill in real search "
                "criteria."
            )

        if failed_configs:
            print(
                "Completed with search warnings for "
                f"{', '.join(failed_configs)}. Successful search state was saved."
            )

        return 0


def main() -> int:
    try:
        return SearchRunner(RunnerConfig.from_env()).run()
    except (ConfigError, NotificationError) as error:
        print(error, file=sys.stderr)
        return 1


def print_search_warning(config: Path, error: Exception) -> None:
    message = f"{error.__class__.__name__}: {error}"
    print(f"Search failed for {config.name}: {message}", file=sys.stderr)
    print(f"::warning file={config}::{escape_github_annotation(message)}")


def escape_github_annotation(message: str) -> str:
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
