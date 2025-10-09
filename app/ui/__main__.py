"""Allow running the UI with ``python -m app.ui``."""
from app.ui.app import main


if __name__ == "__main__":  # pragma: no cover - module execution entry-point
    raise SystemExit(main())
