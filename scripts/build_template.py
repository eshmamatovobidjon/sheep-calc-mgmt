"""Generate assets/templates/trip_template_v1.xlsx from template_spec."""

from pathlib import Path

from sheepbot.excel.template_builder import build_template
from sheepbot.excel.template_spec import TEMPLATE_FILE_NAME

OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "templates" / TEMPLATE_FILE_NAME


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(build_template())
    print(f"Written {OUTPUT}")


if __name__ == "__main__":
    main()
