from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from camply_runner.campsites import campsite_sort_key

SKIPPED_NAMES = {"example.yaml", "example.yml"}


class CamplySearchClient:
    def iter_configs(self, search_dir: Path) -> Iterable[Path]:
        for config in sorted([*search_dir.glob("*.yaml"), *search_dir.glob("*.yml")]):
            if config.name in SKIPPED_NAMES or ".disabled." in config.name:
                print(f"Skipping template or disabled search config: {config.name}")
                continue
            yield config

    def run_search(self, config: Path) -> list[Any]:
        from camply.search import CAMPSITE_SEARCH_PROVIDER
        from camply.utils import yaml_utils

        provider, provider_kwargs, search_kwargs = yaml_utils.yaml_file_to_arguments(
            file_path=str(config)
        )
        provider_class = CAMPSITE_SEARCH_PROVIDER[provider]
        camping_finder = provider_class(**provider_kwargs)

        # We own notification formatting here, so Camply should only search.
        search_kwargs.update(
            {
                "continuous": False,
                "notification_provider": "silent",
                "search_forever": False,
                "search_once": False,
            }
        )
        return sorted(
            camping_finder.get_matching_campsites(**search_kwargs),
            key=campsite_sort_key,
        )
