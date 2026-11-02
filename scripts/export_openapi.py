import json
from pathlib import Path

from lendup_reputation.config.settings import Settings
from lendup_reputation.main import create_app


def main() -> None:
    app = create_app(Settings(database_url="mysql+pymysql://openapi:openapi@localhost/openapi"))
    target = Path("docs/openapi.json")
    target.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
