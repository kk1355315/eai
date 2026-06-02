from pathlib import Path

import pytest

from app import seed


def test_foodkeeper_path_does_not_fallback_to_legacy_test1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configured = tmp_path / "missing-foodkeeper.json"
    real_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        normalized = str(path).replace("\\", "/")
        if path == configured:
            return False
        if normalized.endswith("/data/foodkeeper.json"):
            return False
        if normalized.endswith("/test1/foodkeeper.json"):
            return True
        return real_exists(path)

    monkeypatch.setattr(seed.settings, "foodkeeper_json_path", configured)
    monkeypatch.setattr(seed.Path, "exists", fake_exists)

    with pytest.raises(FileNotFoundError, match="FoodKeeper JSON not found"):
        seed._foodkeeper_path()
