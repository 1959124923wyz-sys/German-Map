#!/usr/bin/env python3
"""Prevent accidental restoration of automatic web-source fetching/update jobs.

CI and static Pages publication remain automatic. Research/data collectors
must require an explicit GitHub Actions 'Run workflow' invocation.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

MANUAL_SOURCE_WORKFLOWS = {
    "bremen-district-join-audit.yml",
    "city-expansion-research.yml",
    "drugs-euda-update.yml",
    "drugs-live-probe.yml",
    "drugs-news-update.yml",
    "drugs-preview-probe.yml",
    "drugs-source-shape.yml",
    "drugs-topic-build.yml",
    "duesseldorf-2025-count-qa.yml",
    "duesseldorf-2025-source-audit.yml",
    "duesseldorf-bv6-stadtteile.yml",
    "duesseldorf-bv7-bv9-source.yml",
    "germany-homicide-map.yml",
    "stuttgart-duesseldorf-audit.yml",
    "stuttgart-duesseldorf-geometry.yml",
    "stuttgart-landtag-2025.yml",
}


def triggers(path: Path) -> set[str]:
    """Extract only keys within the top-level 'on:' mapping (stdlib only)."""
    names: set[str] = set()
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "on:" or line == '"on":':
            active = True
            continue
        if not active:
            continue
        if line and not line.startswith((" ", "#")):
            break
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            names.add(line.strip()[:-1].strip("'\\\""))
    return names


def main() -> None:
    workflows = sorted(WORKFLOWS.glob("*.yml"))
    names = {x.name for x in workflows}
    assert MANUAL_SOURCE_WORKFLOWS <= names, (
        "Source workflow missing or renamed; review its replacement trigger policy",
        sorted(MANUAL_SOURCE_WORKFLOWS - names),
    )
    for file in workflows:
        events = triggers(file)
        assert "schedule" not in events, f"{file.name}: scheduled network update re-enabled"
        assert events, f"{file.name}: no event triggers"
        if file.name in MANUAL_SOURCE_WORKFLOWS:
            assert events == {"workflow_dispatch"}, (
                f"{file.name}: source research/update must stay manual-only, got {events}"
            )
    # Preserve the ability to update website from merged visual/data changes.
    assert "push" in triggers(WORKFLOWS / "drugs-pages-deploy.yml"), (
        "Static Pages publishing should stay automatic"
    )
    # Keep non-network dependent smoke/CI; disabling data bots must not
    # suppress browser testing before merge.
    assert "pull_request" in triggers(WORKFLOWS / "immigration-map-smoke.yml")
    assert "pull_request" in triggers(WORKFLOWS / "germany-homicide-map-smoke.yml")
    print(
        "[auto-update-policy] PASS:",
        len(workflows), "workflows; 0 schedules;",
        len(MANUAL_SOURCE_WORKFLOWS), "manual source/probe/update workflows",
    )


if __name__ == "__main__":
    main()
