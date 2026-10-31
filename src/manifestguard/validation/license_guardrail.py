from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    import tomllib  # py>=3.11
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


NormalizedLicenseKind = Literal[
    "MIT",
    "Apache-2.0",
    "GPL-3.0",
    "Proprietary",
    "Unknown",
    "Missing",
]

MISSING_KIND: NormalizedLicenseKind = "Missing"
UNKNOWN_KIND: NormalizedLicenseKind = "Unknown"
KNOWN_FILTER: set[NormalizedLicenseKind] = {MISSING_KIND, UNKNOWN_KIND}


LICENSE_FILE_CANDIDATES = (
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "COPYING",
    "COPYING.txt",
)


@dataclass(frozen=True)
class LicenseConsistencyIssue:
    type: Literal[
        "licenseMismatch",
        "missingLicenseFile",
        "missingProjectLicense",
        "unknownLicenseDeclaration",
        "multipleHeaderLicenses",
    ]
    message: str
    expected: str | None = None
    found: str | None = None


# Intentionally complex for comprehensive license token normalization across SPDX and PEP 639 formats
# manifestguard-ignore-next-line: COMPLEXITY
def normalize_license_token(token: str) -> NormalizedLicenseKind:
    raw = (token or "").strip()
    if not raw:
        return "Missing"

    upper = raw.upper()

    if upper in {"UNLICENSED", "UNLICENSE"}:
        return "Proprietary"

    if upper in {"PROPRIETARY", "PRIVATE"}:
        return "Proprietary"

    # PEP 639 / LicenseRef-... style (commercial / proprietary marker)
    if upper.startswith("LICENSEREF-"):
        return "Proprietary"

    if upper == "MIT":
        return "MIT"

    if upper in {"APACHE-2.0", "APACHE 2.0", "APACHE2"}:
        return "Apache-2.0"

    if upper in {"GPL-3.0", "GPLV3", "GPL 3.0"}:
        return "GPL-3.0"

    # SPDX-like patterns that we map loosely
    if re.fullmatch(r"MIT", raw, flags=re.IGNORECASE):
        return "MIT"
    if re.fullmatch(r"Apache-?2\.0", raw, flags=re.IGNORECASE):
        return "Apache-2.0"
    if re.fullmatch(r"GPL-?3\.0(-only|-or-later)?", raw, flags=re.IGNORECASE):
        return "GPL-3.0"

    if re.search(r"(proprietary|private|all rights reserved)", raw, flags=re.IGNORECASE):
        return "Proprietary"

    return "Unknown"


def _tokenize_spdx_expression(expr: str) -> list[str]:
    """Extract SPDX-like license identifiers from an SPDX expression.

    Minimal tokenizer (no full AST): collects identifier-like tokens and skips operators.
    This is intentionally dependency-free.
    """
    raw = (expr or "").strip()
    if not raw:
        return []

    # Split on everything except SPDX-ish identifier characters.
    parts = re.split(r"[^A-Za-z0-9.+-]", raw)
    tokens = [p for p in parts if p]

    # Filter common SPDX operators/keywords.
    skip = {"AND", "OR", "WITH"}
    return [t for t in tokens if t.upper() not in skip]


def license_kinds_from_declaration(token: str) -> set[NormalizedLicenseKind]:
    """Normalize a manifest/header license declaration into a set of known kinds."""
    raw = (token or "").strip()
    if not raw:
        return {MISSING_KIND}

    # First try direct normalization (common case).
    direct = normalize_license_token(raw)
    if direct not in KNOWN_FILTER:
        return {direct}

    # Otherwise parse SPDX expression-like strings and normalize each identifier.
    kinds: set[NormalizedLicenseKind] = set()
    for t in _tokenize_spdx_expression(raw):
        kinds.add(normalize_license_token(t))

    # If nothing useful was found, keep the direct result.
    if not kinds:
        return {direct}

    # If we got at least one known kind, drop Unknown to avoid noise.
    known: set[NormalizedLicenseKind] = {k for k in kinds if k not in KNOWN_FILTER}
    return known if known else kinds


# Intentionally complex for comprehensive license text pattern matching across multiple license types
# manifestguard-ignore-next-line: COMPLEXITY
def infer_license_from_license_file_text(text: str) -> NormalizedLicenseKind:
    t = (text or "").lower()

    # Proprietary/private signals
    if (
        "all rights reserved" in t
        or "proprietary" in t
        or "private" in t
        or "not for redistribution" in t
        or "no redistribution" in t
        or "no part of this" in t
        or "unauthorized" in t
    ):
        return "Proprietary"

    # MIT
    if "mit license" in t or "permission is hereby granted" in t:
        return "MIT"

    # Apache 2.0
    if "apache license" in t and "version 2.0" in t:
        return "Apache-2.0"

    # GPL v3
    if "gnu general public license" in t and ("version 3" in t or "either version 3" in t):
        return "GPL-3.0"

    return "Unknown"


# Intentionally complex for comprehensive SPDX and license marker detection in file headers
# manifestguard-ignore-next-line: COMPLEXITY
def infer_license_markers_from_python_file_header(text: str) -> list[NormalizedLicenseKind]:
    header = (text or "")[:2000]
    markers: set[NormalizedLicenseKind] = set()

    spdx = re.search(r"SPDX-License-Identifier:\s*([^\r\n]+)", header, flags=re.IGNORECASE)
    if spdx and spdx.group(1):
        for kind in license_kinds_from_declaration(spdx.group(1)):
            markers.add(kind)

    if re.search(r"\bMIT License\b", header, flags=re.IGNORECASE) or re.search(
        r"permission is hereby granted",
        header,
        flags=re.IGNORECASE,
    ):
        markers.add("MIT")

    if re.search(r"\bApache License\b", header, flags=re.IGNORECASE) and re.search(
        r"\bVersion\s*2\.0\b",
        header,
        flags=re.IGNORECASE,
    ):
        markers.add("Apache-2.0")

    if re.search(r"\bGNU General Public License\b", header, flags=re.IGNORECASE) and re.search(
        r"\bversion\s*3\b",
        header,
        flags=re.IGNORECASE,
    ):
        markers.add("GPL-3.0")

    if re.search(r"all rights reserved", header, flags=re.IGNORECASE) or re.search(
        r"\bproprietary\b",
        header,
        flags=re.IGNORECASE,
    ):
        markers.add("Proprietary")

    arr: list[NormalizedLicenseKind] = list(markers)
    without_unknown: list[NormalizedLicenseKind] = [m for m in arr if m != "Unknown"]
    return without_unknown if without_unknown else arr


def find_first_existing_license_file(project_root: Path) -> Path | None:
    for name in LICENSE_FILE_CANDIDATES:
        p = project_root / name
        if p.exists() and p.is_file():
            return p
    return None


def load_pyproject_project_license(pyproject_toml_text: str) -> str:
    data = tomllib.loads(pyproject_toml_text)
    project = data.get("project") or {}
    lic = project.get("license")

    if isinstance(lic, str):
        return lic.strip()

    if isinstance(lic, dict) and isinstance(lic.get("text"), str):
        return str(lic["text"]).strip()

    return ""


def scan_python_source_headers(paths: Iterable[Path]) -> set[NormalizedLicenseKind]:
    kinds: set[NormalizedLicenseKind] = set()
    for path in paths:
        if not path.is_file() or path.suffix.lower() != ".py":
            continue
        try:
            header = path.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError:
            continue
        for kind in infer_license_markers_from_python_file_header(header):
            kinds.add(kind)
    return kinds


def scan_python_source_header_marker_sets(
    paths: Iterable[Path],
) -> list[set[NormalizedLicenseKind]]:
    """Return per-file marker sets (used to distinguish drift vs SPDX expressions)."""
    marker_sets: list[set[NormalizedLicenseKind]] = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() != ".py":
            continue
        try:
            header = path.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError:
            continue

        per_file = set(infer_license_markers_from_python_file_header(header))
        marker_sets.append(per_file)

    return marker_sets


def _add_mismatch_kind(
    issues: list[LicenseConsistencyIssue],
    *,
    where: str,
    exp: NormalizedLicenseKind,
    found: NormalizedLicenseKind,
) -> None:
    if exp in KNOWN_FILTER or found in KNOWN_FILTER:
        return
    if exp == found:
        return
    issues.append(
        LicenseConsistencyIssue(
            type="licenseMismatch",
            message=(
                f"License mismatch ({where}): expected '{exp}' but found '{found}'. "
                "This is release-critical when AI rewrites metadata or headers."
            ),
            expected=exp,
            found=found,
        ),
    )


def _add_mismatch_set(
    issues: list[LicenseConsistencyIssue],
    *,
    where: str,
    exp_set: set[NormalizedLicenseKind],
    found: NormalizedLicenseKind,
) -> None:
    if found in KNOWN_FILTER:
        return
    exp_known = sorted(k for k in exp_set if k not in KNOWN_FILTER)
    if not exp_known:
        return
    if found in exp_set:
        return
    issues.append(
        LicenseConsistencyIssue(
            type="licenseMismatch",
            message=(
                f"License mismatch ({where}): expected one of {exp_known!r} but found '{found}'. "
                "This is release-critical when AI rewrites metadata or headers."
            ),
            expected=", ".join(exp_known),
            found=found,
        ),
    )


def _aggregate_header_marker_sets(
    header_marker_sets: Iterable[set[NormalizedLicenseKind]],
) -> tuple[
    set[NormalizedLicenseKind],
    set[NormalizedLicenseKind],
    list[NormalizedLicenseKind],
    NormalizedLicenseKind | None,
]:
    header_union: set[NormalizedLicenseKind] = set()
    single_license_decls: set[NormalizedLicenseKind] = set()

    for per_file in header_marker_sets:
        per_file_known: set[NormalizedLicenseKind] = {k for k in per_file if k not in KNOWN_FILTER}
        header_union |= per_file_known
        if len(per_file_known) == 1:
            single_license_decls |= per_file_known

    header_distinct = sorted(header_union)
    header_primary: NormalizedLicenseKind | None = (
        header_distinct[0] if len(header_distinct) == 1 else None
    )
    return header_union, single_license_decls, header_distinct, header_primary


# Intentionally complex for comprehensive license consistency validation across multiple sources
# manifestguard-ignore-next-line: COMPLEXITY
def validate_license_consistency(
    *,
    pyproject_license_token: str,
    license_file_text: str | None,
    header_marker_sets: Iterable[set[NormalizedLicenseKind]] = (),
) -> list[LicenseConsistencyIssue]:
    issues: list[LicenseConsistencyIssue] = []

    expected_set = license_kinds_from_declaration(pyproject_license_token)
    expected_known = bool(expected_set - KNOWN_FILTER)
    if not expected_known:
        issues.append(
            LicenseConsistencyIssue(
                type=(
                    "missingProjectLicense"
                    if expected_set == {MISSING_KIND}
                    else "unknownLicenseDeclaration"
                ),
                message=(
                    "pyproject.toml [project].license must be explicit and "
                    "machine-readable (SPDX-like or LicenseRef-...). "
                    "This reduces AI-induced license drift."
                ),
                found=pyproject_license_token,
            ),
        )

    if not license_file_text:
        issues.append(
            LicenseConsistencyIssue(
                type="missingLicenseFile",
                message="LICENSE file content missing; guardrail cannot verify consistency.",
            ),
        )
        return issues

    license_kind = infer_license_from_license_file_text(license_file_text)
    license_known = license_kind not in KNOWN_FILTER

    if license_known:
        _add_mismatch_set(
            issues,
            where="LICENSE ↔ pyproject.toml",
            exp_set=expected_set,
            found=license_kind,
        )

    header_union, single_license_decls, header_distinct, header_primary = (
        _aggregate_header_marker_sets(
            header_marker_sets,
        )
    )

    # Drift = conflicting single-license declarations across files.
    if len(single_license_decls) > 1:
        issues.append(
            LicenseConsistencyIssue(
                type="multipleHeaderLicenses",
                message=(
                    "Multiple different license markers found in source headers: "
                    + ", ".join(sorted(single_license_decls))
                    + ". This often indicates AI-induced license drift."
                ),
            ),
        )

    # Header comparisons
    if header_primary is not None:
        _add_mismatch_kind(
            issues,
            where="LICENSE ↔ source headers",
            exp=license_kind,
            found=header_primary,
        )
        _add_mismatch_set(
            issues,
            where="pyproject.toml ↔ source headers",
            exp_set=expected_set,
            found=header_primary,
        )
    elif header_distinct:
        # Expression / multi-marker case: enforce intersection checks.
        if expected_known and not (expected_set & header_union):
            issues.append(
                LicenseConsistencyIssue(
                    type="licenseMismatch",
                    message=(
                        "License mismatch (pyproject.toml ↔ source headers): "
                        f"expected '{', '.join(sorted(k for k in expected_set if k not in KNOWN_FILTER))}' "
                        f"but found multiple markers: {', '.join(header_distinct)}. "
                        "This is release-critical when AI rewrites headers."
                    ),
                    expected=", ".join(sorted(k for k in expected_set if k not in KNOWN_FILTER)),
                    found=", ".join(header_distinct),
                ),
            )

        if license_known and license_kind not in header_union:
            issues.append(
                LicenseConsistencyIssue(
                    type="licenseMismatch",
                    message=(
                        "License mismatch (LICENSE ↔ source headers): expected "
                        f"'{license_kind}' but found multiple markers: {', '.join(header_distinct)}. "
                        "This is release-critical when AI rewrites headers."
                    ),
                    expected=license_kind,
                    found=", ".join(header_distinct),
                ),
            )

    return issues
