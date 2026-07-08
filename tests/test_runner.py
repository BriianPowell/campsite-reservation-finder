from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from camply_runner.config import RunnerConfig
from camply_runner.runner import SearchRunner, escape_github_annotation


def test_runner_continues_after_config_failure_and_saves_successful_state() -> None:
    state_store = FakeStateStore()
    notifier = FakeNotifier()
    runner = SearchRunner(
        config=RunnerConfig(apprise_url="test://example", search_dir=Path(".")),
        search_client=FakeSearchClient(
            {
                "ok.yaml": [
                    campsite(campsite_id="1", facility_id="2", site="001"),
                ],
                "bad.yaml": RuntimeError("blocked"),
            }
        ),
        state_store=state_store,
        notifier=notifier,
    )

    assert runner.run() == 0
    assert notifier.calls == [("ok", 1, 1)]
    assert len(state_store.saved) == 1
    assert "ok|1|2|2026-08-06|2026-08-09" in state_store.saved[0]


def test_runner_skips_matches_already_in_state() -> None:
    key = "ok|1|2|2026-08-06|2026-08-09"
    state_store = FakeStateStore(existing_keys={key})
    notifier = FakeNotifier()
    runner = SearchRunner(
        config=RunnerConfig(apprise_url="test://example", search_dir=Path(".")),
        search_client=FakeSearchClient(
            {
                "ok.yaml": [
                    campsite(campsite_id="1", facility_id="2", site="001"),
                ]
            }
        ),
        state_store=state_store,
        notifier=notifier,
    )

    assert runner.run() == 0
    assert notifier.calls == []
    assert state_store.saved == []


def test_runner_returns_failure_when_notification_send_fails() -> None:
    notifier = FakeNotifier(should_succeed=False)
    runner = SearchRunner(
        config=RunnerConfig(apprise_url="test://example", search_dir=Path(".")),
        search_client=FakeSearchClient(
            {
                "ok.yaml": [
                    campsite(campsite_id="1", facility_id="2", site="001"),
                ]
            }
        ),
        state_store=FakeStateStore(),
        notifier=notifier,
    )

    assert runner.run() == 1
    assert notifier.calls == [("ok", 1, 1)]


def test_escape_github_annotation_escapes_reserved_characters() -> None:
    assert escape_github_annotation("bad % value\nnext\rline") == (
        "bad %25 value%0Anext%0Dline"
    )


class FakeSearchClient:
    def __init__(self, results_by_config: dict[str, list[object] | Exception]) -> None:
        self.results_by_config = results_by_config

    def iter_configs(self, search_dir: Path):
        return (Path(config_name) for config_name in self.results_by_config)

    def run_search(self, config: Path) -> list[object]:
        result = self.results_by_config[config.name]
        if isinstance(result, Exception):
            raise result
        return result


class FakeStateStore:
    def __init__(self, existing_keys: set[str] | None = None) -> None:
        self.existing_keys = existing_keys or set()
        self.saved: list[dict[str, object]] = []

    def load(self, now):
        return {key: now for key in self.existing_keys}

    def save(self, notified_at_by_key: dict[str, object]) -> None:
        self.saved.append(dict(notified_at_by_key))


class FakeNotifier:
    def __init__(self, should_succeed: bool = True) -> None:
        self.should_succeed = should_succeed
        self.calls: list[tuple[str, int, int]] = []

    def notify_matches(
        self,
        search_name: str,
        matches: list[object],
        total_matches: int,
    ) -> bool:
        self.calls.append((search_name, len(matches), total_matches))
        return self.should_succeed


def campsite(campsite_id: str, facility_id: str, site: str) -> SimpleNamespace:
    return SimpleNamespace(
        facility_name="Test Campground",
        booking_date="2026-08-06",
        booking_end_date="2026-08-09",
        campsite_site_name=site,
        campsite_loop_name="A",
        campsite_type="Tent",
        booking_url="",
        campsite_id=campsite_id,
        facility_id=facility_id,
    )
