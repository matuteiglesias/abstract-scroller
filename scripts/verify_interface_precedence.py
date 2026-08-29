from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle}")


def main() -> int:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    system = (ROOT / "SYSTEM.yaml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contracts = (ROOT / "contracts" / "README.md").read_text(encoding="utf-8")

    require(makefile, "snapshot-review-records:", "canonical make target")
    require(makefile, "snapshot-csv-legacy:", "CSV compatibility target")
    require(makefile, "snapshot-review-node-legacy:", "review-node compatibility target")
    require(system, "consumes:\n  - contract:paper.review-record@1", "canonical SYSTEM input")
    require(system, "compatibility:", "SYSTEM compatibility section")
    require(readme, "preferred machine", "README preferred-interface language")
    require(contracts, "local compatibility schema", "local schema classification")

    print("P4 interface precedence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
