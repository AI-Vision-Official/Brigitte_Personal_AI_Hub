#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project Scanner v1.0 - Brigitte Personal AI Hub.

Leest een expliciete projectconfiguratie en inventariseert per ingeschakeld
project wat er feitelijk op schijf staat. Resultaat: gestructureerde JSON.

Eigenschappen
- Alleen lezen. De scanner verwijdert, verplaatst, hernoemt of wijzigt niets.
- Alleen standaardbibliotheek. Geen netwerk, geen installaties.
- Alleen ingeschakelde projecten binnen expliciet toegestane locaties
  ("allowed_roots"). Een pad buiten die locaties wordt niet eens bekeken.
- Symbolische links, Windows-junctions en andere reparse points worden NIET
  gevolgd (strenger dan nodig: ook links naar binnen worden overgeslagen).
- Een fout bij een project stopt de rest van de scan niet.
- Resultaat gaat naar standaarduitvoer, of naar een expliciet aangewezen
  bestaande map, in een NIEUW bestand (nooit overschrijven).

Gebruik
    python project_scanner.py --config pad\\naar\\config.json
    python project_scanner.py --config pad\\naar\\config.json --output-dir pad\\naar\\map
    python project_scanner.py --config pad\\naar\\config.json --no-save

Opslaan: staat "output_dir" in de configuratie (of geef je --output-dir mee), dan
wordt een geslaagde scan automatisch als nieuw JSON-bestand bewaard. Een
mislukte scan wordt nooit als inventarisatie opgeslagen.

Vanuit de Hub (Python):
    from project_scanner import run_scan, write_result, load_scan_result
    resultaat = run_scan(r"pad\\naar\\config.json")
    bestand = write_result(resultaat, r"pad\\naar\\map")
    teruggelezen = load_scan_result(bestand)

Exitcodes: 0 = scan uitgevoerd en (indien gevraagd) opgeslagen,
1 = configuratie onbruikbaar, 2 = uitvoerlocatie geweigerd of ongeldige opdracht,
3 = scan mislukt (geen enkel project gescand): niets opgeslagen.

De scanner bepaalt GEEN projectstatus, voortgang of vervolgstappen. Alles
wat daarover in het resultaat staat, staat onder "missing".
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

SCANNER_NAME = "project_scanner"
SCANNER_VERSION = "1.1.0"
RESULT_SCHEMA_VERSION = "1.1"

# Alleen scans met deze uitkomst worden als inventarisatie opgeslagen of ingelezen.
SAVEABLE_OUTCOMES = ("complete", "partial")
MAX_RESULT_BYTES = 50_000_000

DEFAULT_MAX_DEPTH = 4
DEFAULT_MAX_ENTRIES = 5000
MAX_DOCS_LISTED = 200
MAX_SAMPLE_ITEMS = 20
MAX_JSON_BYTES = 1_000_000
MAX_CONFIG_BYTES = 1_000_000

# Mappen die op naam worden overgeslagen (niet in de inhoud gekeken).
IGNORED_DIR_NAMES = frozenset({
    ".git", ".mypy_cache", "__pycache__", "node_modules",
    ".venv", "venv", ".pytest_cache",
})

# Herkende projectbestanden. Alleen in de hoofdmap van het project.
KEY_FILE_NAMES = frozenset({
    "readme.md", "readme.txt", "license", "license.md", "license.txt",
    "00_project_start.md", "project_state.md", "architecture.md",
    "rules_and_permissions.md", "changelog.md",
    "hub_manifest.json", "ai_context.json", "architecture_context.json",
    "dashboard.html", "requirements.txt", "pyproject.toml", "package.json",
    ".gitignore",
})

DOCUMENTATION_EXTENSIONS = frozenset({".md", ".txt", ".rst", ".pdf", ".docx", ".odt"})

CATEGORY_BY_EXTENSION = {
    **{ext: "documentation" for ext in DOCUMENTATION_EXTENSIONS},
    **{ext: "code" for ext in (
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css",
        ".ps1", ".bat", ".cmd", ".sh")},
    **{ext: "config" for ext in (
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf")},
    **{ext: "data" for ext in (
        ".json", ".csv", ".tsv", ".xlsx", ".xls", ".xml",
        ".db", ".sqlite", ".sqlite3")},
    **{ext: "media" for ext in (
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico",
        ".mp3", ".wav", ".flac", ".mp4", ".mov", ".mkv")},
    **{ext: "archive" for ext in (
        ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz")},
}

KNOWN_ENTRY_FIELDS = frozenset({"id", "name", "path", "enabled", "tags", "profile"})

REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

# Dit bepaalt de scanner nooit. Zo blijft zichtbaar wat NIET is vastgesteld.
NOT_DETERMINED = (
    {"field": "status",
     "reason": "Geen bron voor een projectstatus in v1.0; niet afgeleid."},
    {"field": "progress",
     "reason": "Geen bron voor voortgang in v1.0; niet afgeleid."},
    {"field": "next_steps",
     "reason": "Geen bron voor vervolgstappen in v1.0; niet afgeleid."},
)


class ConfigError(Exception):
    """De configuratie is niet bruikbaar; er wordt niets gescand."""


class OutputError(Exception):
    """De uitvoerlocatie wordt geweigerd; er is niets geschreven."""


class NotSavedError(OutputError):
    """De scan is mislukt en wordt daarom niet als inventarisatie opgeslagen."""


class ResultFileError(Exception):
    """Een opgeslagen scanbestand is onleesbaar of geen geldige, geslaagde scan."""


# --------------------------------------------------------------------------
# Hulpfuncties
# --------------------------------------------------------------------------

def _issue(code: str, severity: str, message: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _iso_time(timestamp: float) -> Optional[str]:
    try:
        return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return None


def _os_error_text(exc: BaseException) -> str:
    detail = getattr(exc, "strerror", None) or str(exc)
    return f"{type(exc).__name__}: {detail}"


def is_within(child: str, root: str, path_mod: Any = os.path) -> bool:
    """True als `child` gelijk is aan of onder `root` ligt. Zuivere tekstvergelijking.

    Gebruikt normcase (hoofdletterongevoelig op Windows) en commonpath, zodat
    'C:\\\\toegestaan_extra' NIET binnen 'C:\\\\toegestaan' valt en een andere
    schijfletter nooit binnen valt. `path_mod` is verwisselbaar (ntpath) om
    Windows-regels te kunnen testen zonder Windows.
    """
    try:
        child_norm = path_mod.normcase(path_mod.normpath(child))
        root_norm = path_mod.normcase(path_mod.normpath(root))
        return path_mod.commonpath([child_norm, root_norm]) == root_norm
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Configuratie (inlezen en valideren)
# --------------------------------------------------------------------------

def load_config(config_path: str) -> Any:
    """Leest het JSON-configuratiebestand. Wijzigt niets."""
    if not isinstance(config_path, str) or not config_path.strip():
        raise ConfigError("Geen configuratiebestand opgegeven.")
    try:
        if os.path.getsize(config_path) > MAX_CONFIG_BYTES:
            raise ConfigError("Het configuratiebestand is onverwacht groot (> 1 MB).")
        # utf-8-sig: werkt ook met bestanden die PowerShell met BOM schrijft.
        with open(config_path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except ConfigError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(
            f"Configuratiebestand niet leesbaar of geen geldige JSON ({_os_error_text(exc)})."
        ) from exc


def _check_entry(index: int, item: Any, seen_ids: set) -> Dict[str, Any]:
    """Valideert één projectitem. Streng: elk probleem = niet scannen."""
    fallback_id = f"entry-{index + 1}"
    entry: Dict[str, Any] = {
        "index": index, "id": fallback_id, "name": None, "path": None,
        "enabled": None, "tags": None, "profile": None,
        "problems": [], "ignored_fields": [],
    }
    problems: List[str] = entry["problems"]

    if not isinstance(item, dict):
        problems.append("Het item is geen JSON-object.")
        return entry

    raw_id = item.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        problems.append("'id' ontbreekt of is geen tekst.")
    else:
        entry["id"] = raw_id.strip()
        if entry["id"] in seen_ids:
            problems.append(f"'id' '{entry['id']}' komt dubbel voor.")
        seen_ids.add(entry["id"])

    if "name" in item:
        if isinstance(item["name"], str) and item["name"].strip():
            entry["name"] = item["name"].strip()
        else:
            problems.append("'name' moet een niet-lege tekst zijn.")

    raw_path = item.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        problems.append("'path' ontbreekt of is geen tekst.")
    elif "\x00" in raw_path:
        problems.append("'path' bevat een ongeldig teken.")
    elif not os.path.isabs(raw_path):
        problems.append("'path' moet een absoluut pad zijn.")
    else:
        entry["path"] = raw_path

    if not isinstance(item.get("enabled"), bool):
        problems.append("'enabled' moet expliciet true of false zijn.")
    else:
        entry["enabled"] = item["enabled"]

    if "tags" in item:
        tags = item["tags"]
        if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
            entry["tags"] = list(tags)
        else:
            problems.append("'tags' moet een lijst met tekst zijn.")

    if "profile" in item:
        profile = item["profile"]
        if isinstance(profile, (str, dict)):
            entry["profile"] = profile
        else:
            problems.append("'profile' moet tekst of een object zijn.")

    entry["ignored_fields"] = sorted(k for k in item if k not in KNOWN_ENTRY_FIELDS)
    return entry


def parse_config(raw: Any) -> Dict[str, Any]:
    """Valideert de configuratie. Faalt gesloten: zonder geldige roots geen scan."""
    if not isinstance(raw, dict):
        raise ConfigError("De configuratie moet een JSON-object zijn.")

    issues: List[Dict[str, str]] = []
    roots_raw = raw.get("allowed_roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise ConfigError(
            "'allowed_roots' ontbreekt of is leeg: zonder toegestane locaties wordt niets gescand."
        )

    roots: List[Dict[str, str]] = []
    for position, item in enumerate(roots_raw):
        if (isinstance(item, str) and item.strip() and "\x00" not in item
                and os.path.isabs(item)):
            roots.append({"configured": item, "real": os.path.realpath(item)})
        else:
            issues.append(_issue(
                "invalid_allowed_root", "warning",
                f"allowed_roots[{position}] is geen geldig absoluut pad en wordt genegeerd."))
    if not roots:
        raise ConfigError("Geen enkel geldig absoluut pad in 'allowed_roots'.")

    projects_raw = raw.get("projects")
    if not isinstance(projects_raw, list):
        raise ConfigError("'projects' ontbreekt of is geen lijst.")

    output_dir = raw.get("output_dir")
    if output_dir is not None and (
            not isinstance(output_dir, str) or not output_dir.strip()
            or "\x00" in output_dir or not os.path.isabs(output_dir)):
        # Bepaalt waar geschreven wordt: bij twijfel stoppen, niet raden.
        raise ConfigError("'output_dir' moet een absoluut pad (tekst) zijn.")

    seen_ids: set = set()
    entries = [_check_entry(i, item, seen_ids) for i, item in enumerate(projects_raw)]

    unknown = sorted(k for k in raw
                     if k not in ("allowed_roots", "projects", "config_version", "output_dir"))
    if unknown:
        issues.append(_issue(
            "unknown_config_fields", "info",
            "Onbekende velden op hoofdniveau genegeerd: " + ", ".join(unknown)))

    return {"allowed_roots": roots, "entries": entries, "issues": issues,
            "output_dir": output_dir}


# --------------------------------------------------------------------------
# Scanlogica
# --------------------------------------------------------------------------

def _classify_entry(entry: "os.DirEntry[str]") -> Tuple[Optional[str], Any]:
    """Geeft (linksoort, stat). Volgt nooit een link; kijkt alleen naar de link zelf."""
    if entry.is_symlink():
        return "symlink", None
    info = entry.stat(follow_symlinks=False)
    if getattr(info, "st_file_attributes", 0) & REPARSE_FLAG:
        return "reparse_point", info  # o.a. Windows-junction
    return None, info


def _category_for(extension: str) -> str:
    return CATEGORY_BY_EXTENSION.get(extension, "other")


def _check_json_file(path: str, size: int) -> Dict[str, Any]:
    """Controleert alleen of een bekend JSON-projectbestand geldige JSON is."""
    if size > MAX_JSON_BYTES:
        return {"json_valid": None, "json_note": "Te groot om te controleren."}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            json.load(handle)
        return {"json_valid": True}
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"json_valid": False, "json_error": f"{type(exc).__name__}: {exc}"}
    except OSError as exc:
        return {"json_valid": None, "json_note": _os_error_text(exc)}


def _scan_tree(real_root: str, max_depth: int, max_entries: int) -> Dict[str, Any]:
    """Loopt door de projectmap. Alleen lezen; volgt geen links."""
    acc: Dict[str, Any] = {
        "files": 0, "dirs": 0, "bytes": 0, "seen": 0, "truncated": False,
        "categories": {}, "extensions": {},
        "documentation": [], "documentation_total": 0, "key_files": [],
        "skipped_links": [], "skipped_dirs": [], "unreadable": [],
        "not_descended": [], "special_skipped": 0, "newest": None,
    }
    stack: List[Tuple[str, str, int]] = [(real_root, "", 0)]

    while stack and not acc["truncated"]:
        dir_path, rel_dir, depth = stack.pop()
        try:
            with os.scandir(dir_path) as iterator:
                entries = sorted(iterator, key=lambda e: e.name.lower())
        except OSError as exc:
            acc["unreadable"].append({"path": rel_dir or ".", "error": _os_error_text(exc)})
            continue

        for entry in entries:
            acc["seen"] += 1
            if acc["seen"] > max_entries:
                acc["truncated"] = True
                break
            rel = f"{rel_dir}/{entry.name}" if rel_dir else entry.name

            try:
                link_kind, info = _classify_entry(entry)
            except OSError as exc:
                acc["unreadable"].append({"path": rel, "error": _os_error_text(exc)})
                continue
            if link_kind:
                acc["skipped_links"].append({"path": rel, "kind": link_kind})
                continue

            if stat.S_ISDIR(info.st_mode):
                acc["dirs"] += 1
                if entry.name.lower() in IGNORED_DIR_NAMES:
                    acc["skipped_dirs"].append(rel)
                elif depth >= max_depth:
                    acc["not_descended"].append(rel)
                elif not is_within(os.path.realpath(entry.path), real_root):
                    # Vangnet: de map blijkt via een omweg buiten het project te liggen.
                    acc["skipped_links"].append({"path": rel, "kind": "escapes_project_root"})
                else:
                    stack.append((entry.path, rel, depth + 1))
            elif stat.S_ISREG(info.st_mode):
                _record_file(acc, entry, rel, depth, info)
            else:
                acc["special_skipped"] += 1

    return acc


def _record_file(acc: Dict[str, Any], entry: "os.DirEntry[str]", rel: str,
                 depth: int, info: Any) -> None:
    name_lower = entry.name.lower()
    extension = os.path.splitext(name_lower)[1]
    category = _category_for(extension)

    acc["files"] += 1
    acc["bytes"] += info.st_size
    acc["categories"][category] = acc["categories"].get(category, 0) + 1
    ext_key = extension or "(geen)"
    acc["extensions"][ext_key] = acc["extensions"].get(ext_key, 0) + 1

    if acc["newest"] is None or info.st_mtime > acc["newest"][0]:
        acc["newest"] = (info.st_mtime, rel)

    modified = _iso_time(info.st_mtime)
    if category == "documentation":
        acc["documentation_total"] += 1
        if len(acc["documentation"]) < MAX_DOCS_LISTED:
            acc["documentation"].append(
                {"path": rel, "size_bytes": info.st_size, "modified": modified})

    if depth == 0 and name_lower in KEY_FILE_NAMES:
        item: Dict[str, Any] = {
            "path": rel, "category": category,
            "size_bytes": info.st_size, "modified": modified,
        }
        if extension == ".json":
            item.update(_check_json_file(entry.path, info.st_size))
        acc["key_files"].append(item)


def _sample(items: List[Any]) -> Dict[str, Any]:
    return {"count": len(items), "sample": items[:MAX_SAMPLE_ITEMS]}


def _empty_project_result(entry: Dict[str, Any]) -> Dict[str, Any]:
    missing = [dict(m) for m in NOT_DETERMINED]
    if entry["name"] is None:
        missing.append({"field": "name", "reason": "Niet opgegeven in de configuratie."})
    if not entry["tags"]:
        missing.append({"field": "tags", "reason": "Niet opgegeven in de configuratie."})
    if entry["profile"] is None:
        missing.append({"field": "profile", "reason": "Niet opgegeven in de configuratie."})
    return {
        "id": entry["id"],
        "state": "pending",
        "established": {
            "name": entry["name"], "configured_path": entry["path"],
            "enabled": entry["enabled"], "tags": entry["tags"],
            "profile": entry["profile"], "resolved_path": None,
            "within_allowed_roots": None, "path_exists": None,
            "is_directory": None, "has_git_folder": None,
        },
        "derived": None,
        "missing": missing,
        "uncertain": [],
        "issues": [],
    }


def scan_project(entry: Dict[str, Any], roots: List[Dict[str, str]],
                 max_depth: int, max_entries: int) -> Dict[str, Any]:
    """Scant één project. Geeft altijd een resultaat; gooit niets naar buiten."""
    result = _empty_project_result(entry)
    established = result["established"]
    issues = result["issues"]

    try:
        if entry["problems"]:
            result["state"] = "invalid_config"
            for problem in entry["problems"]:
                issues.append(_issue("invalid_config", "error", problem))
            return result

        if entry["ignored_fields"]:
            issues.append(_issue(
                "unknown_entry_fields", "info",
                "Onbekende velden genegeerd: " + ", ".join(entry["ignored_fields"])))

        if not entry["enabled"]:
            # Uitgeschakeld: het bestandssysteem wordt voor dit pad niet aangeraakt.
            result["state"] = "disabled"
            issues.append(_issue("disabled", "info", "Project is uitgeschakeld; niet gescand."))
            return result

        real = os.path.realpath(entry["path"])
        established["resolved_path"] = real
        within = any(is_within(real, root["real"]) for root in roots)
        established["within_allowed_roots"] = within
        if not within:
            # Buiten de toegestane locaties: ook niet kijken of het bestaat.
            result["state"] = "outside_allowed_roots"
            issues.append(_issue(
                "outside_allowed_roots", "error",
                "Het opgeloste pad ligt buiten de toegestane locaties; niet gescand."))
            return result

        exists = os.path.exists(real)
        established["path_exists"] = exists
        if not exists:
            result["state"] = "path_missing"
            issues.append(_issue("path_missing", "error", "Het projectpad bestaat niet."))
            return result

        is_directory = os.path.isdir(real)
        established["is_directory"] = is_directory
        if not is_directory:
            result["state"] = "not_a_directory"
            issues.append(_issue("not_a_directory", "error", "Het projectpad is geen map."))
            return result

        established["has_git_folder"] = os.path.lexists(os.path.join(real, ".git"))

        # Bewust breed: één project mag de rest van de scan nooit stoppen.
        tree = _scan_tree(real, max_depth, max_entries)
    except Exception as exc:  # noqa: BLE001
        result["state"] = "error"
        result["derived"] = None
        issues.append(_issue("scan_error", "error", _os_error_text(exc)))
        return result

    root_unreadable = any(item["path"] == "." for item in tree["unreadable"])
    if root_unreadable:
        result["state"] = "access_denied"
        issues.append(_issue("access_denied", "error", "De projectmap kon niet worden gelezen."))
        return result

    newest = tree["newest"]
    result["derived"] = {
        "name_from_folder": os.path.basename(real.rstrip("\\/")) or real,
        "counts": {"files": tree["files"], "directories": tree["dirs"],
                   "total_bytes": tree["bytes"]},
        "file_categories": dict(sorted(tree["categories"].items())),
        "file_extensions": dict(sorted(tree["extensions"].items())),
        "last_modified_file": (
            {"path": newest[1], "modified": _iso_time(newest[0])} if newest else None),
        "key_files": sorted(tree["key_files"], key=lambda k: k["path"]),
        "documentation": {
            "total": tree["documentation_total"],
            "listed": sorted(tree["documentation"], key=lambda d: d["path"]),
            "list_truncated": tree["documentation_total"] > len(tree["documentation"]),
        },
        "ignored_directories": sorted(tree["skipped_dirs"]),
        "scan_limits": {"max_depth": max_depth, "max_entries": max_entries},
    }

    uncertain = result["uncertain"]
    if tree["truncated"]:
        uncertain.append({"code": "scan_truncated",
                          "detail": f"Gestopt na {max_entries} items; het resultaat is onvolledig."})
    if tree["unreadable"]:
        uncertain.append({"code": "unreadable_entries", **_sample(tree["unreadable"])})
    if tree["not_descended"]:
        uncertain.append({"code": "depth_limit_reached", **_sample(tree["not_descended"])})
    if tree["skipped_links"]:
        uncertain.append({"code": "links_not_followed", **_sample(tree["skipped_links"])})
    if tree["special_skipped"]:
        uncertain.append({"code": "special_files_skipped", "count": tree["special_skipped"]})

    if tree["truncated"] or tree["unreadable"]:
        result["state"] = "partial"
        issues.append(_issue("partial_scan", "warning",
                             "De scan is onvolledig (afgekapt of niet alles leesbaar)."))
    else:
        result["state"] = "scanned"
    if tree["skipped_links"]:
        issues.append(_issue("links_not_followed", "warning",
                             "Links of junctions zijn niet gevolgd."))
    return result


def compute_outcome(projects: List[Any]) -> Tuple[str, str]:
    """Bepaalt of een scan als inventarisatie bruikbaar is.

    complete        alle ingeschakelde projecten volledig gescand
    partial         minstens één project gescand, maar niet alles gelukt of volledig
    failed          geen enkel project kon worden gescand
    nothing_to_scan geen enkel ingeschakeld project

    Alleen 'complete' en 'partial' worden opgeslagen.
    """
    relevant = [p for p in projects if isinstance(p, dict) and p.get("state") != "disabled"]
    if not relevant:
        return "nothing_to_scan", "Geen enkel ingeschakeld project om te scannen."
    usable = [p for p in relevant if p.get("state") in ("scanned", "partial")]
    if not usable:
        return "failed", "Geen enkel project kon worden gescand."
    if all(p.get("state") == "scanned" for p in relevant):
        return "complete", f"Alle {len(relevant)} ingeschakelde project(en) volledig gescand."
    return "partial", (f"{len(usable)} van {len(relevant)} ingeschakelde project(en) "
                       "gescand; niet alles is gelukt of volledig.")


def scan_projects(config_raw: Any, *, config_source: Optional[str] = None,
                  max_depth: int = DEFAULT_MAX_DEPTH,
                  max_entries: int = DEFAULT_MAX_ENTRIES) -> Dict[str, Any]:
    """Scant alle projecten uit een al ingelezen configuratie (dict)."""
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 0:
        raise ValueError("max_depth moet een geheel getal >= 0 zijn.")
    if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries < 1:
        raise ValueError("max_entries moet een geheel getal >= 1 zijn.")

    parsed = parse_config(config_raw)
    projects = [scan_project(entry, parsed["allowed_roots"], max_depth, max_entries)
                for entry in parsed["entries"]]

    outcome, outcome_note = compute_outcome(projects)
    states: Dict[str, int] = {}
    severities: Dict[str, int] = {}
    for project in projects:
        states[project["state"]] = states.get(project["state"], 0) + 1
        for issue in project["issues"]:
            severities[issue["severity"]] = severities.get(issue["severity"], 0) + 1

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "scanner": {"name": SCANNER_NAME, "version": SCANNER_VERSION},
        "scanned_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "config": {
            "source": config_source,
            "allowed_roots": [r["configured"] for r in parsed["allowed_roots"]],
            "output_dir": parsed["output_dir"],
            "issues": parsed["issues"],
        },
        "projects": projects,
        "summary": {
            "projects_total": len(projects),
            "outcome": outcome,
            "outcome_note": outcome_note,
            "by_state": dict(sorted(states.items())),
            "issues_by_severity": dict(sorted(severities.items())),
        },
    }


def run_scan(config_path: str, *, max_depth: int = DEFAULT_MAX_DEPTH,
             max_entries: int = DEFAULT_MAX_ENTRIES) -> Dict[str, Any]:
    """Leest het configuratiebestand en scant. Dit is de aanroep voor de Hub."""
    raw = load_config(config_path)
    return scan_projects(raw, config_source=config_path,
                         max_depth=max_depth, max_entries=max_entries)


# --------------------------------------------------------------------------
# Uitvoer
# --------------------------------------------------------------------------

def _project_paths(result: Dict[str, Any]) -> List[str]:
    paths: List[str] = []
    for project in result.get("projects", []):
        established = project.get("established", {})
        configured = established.get("configured_path")
        if isinstance(configured, str):
            paths.append(os.path.abspath(configured))
        resolved = established.get("resolved_path")
        if isinstance(resolved, str):
            paths.append(resolved)
    return paths


def _file_stem() -> str:
    """Bestandsnaam zonder uitgang: datum en tijd (lokale tijd, op de seconde)."""
    return datetime.now().strftime("project_scan_%Y%m%d_%H%M%S")


def write_result(result: Dict[str, Any], output_dir: str) -> str:
    """Slaat een GESLAAGDE scan op als NIEUW bestand in een bestaande, expliciete map.

    - Een mislukte scan (uitkomst 'failed' of 'nothing_to_scan') wordt niet opgeslagen.
    - Een deels geslaagde scan krijgt '_partial' in de bestandsnaam en 'outcome: partial'
      in de inhoud, zodat ze niet voor een complete inventarisatie wordt aangezien.
    - Maakt geen mappen aan.
    - Weigert een map binnen een gescand project (anders wijzig je dat project).
    - Opent met modus "x": een bestaand bestand wordt nooit overschreven; bij dezelfde
      seconde volgt een volgnummer.
    - UTF-8, zonder BOM. De volledige tekst wordt eerst klaargemaakt, zodat een
      codeerfout geen leeg bestand achterlaat.
    """
    projects = result.get("projects", []) if isinstance(result, dict) else []
    outcome, note = compute_outcome(projects)
    if outcome not in SAVEABLE_OUTCOMES:
        raise NotSavedError(f"Niet opgeslagen: de scan is mislukt (uitkomst '{outcome}'). {note}")

    if not isinstance(output_dir, str) or not output_dir.strip():
        raise OutputError("Geen uitvoermap opgegeven.")
    real_out = os.path.realpath(output_dir)
    if not os.path.isdir(real_out):
        raise OutputError("De uitvoermap bestaat niet. De scanner maakt zelf geen mappen aan.")
    for project_path in _project_paths(result):
        if is_within(real_out, project_path):
            raise OutputError(
                "De uitvoermap ligt binnen een projectmap uit de configuratie. "
                "Kies een map buiten de gescande projecten.")

    payload = dict(result)
    payload["summary"] = {**result.get("summary", {}), "outcome": outcome, "outcome_note": note}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        # Bijvoorbeeld een bestandsnaam met een ongeldig teken: dan veilig escapen.
        text = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"

    stem = _file_stem()
    tag = "" if outcome == "complete" else "_partial"
    for attempt in range(1, 100):
        number = "" if attempt == 1 else f"_{attempt}"
        target = os.path.join(real_out, f"{stem}{number}{tag}.json")
        try:
            with open(target, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            return target
        except FileExistsError:
            continue
        except OSError as exc:
            raise OutputError(f"Schrijven mislukt ({_os_error_text(exc)}).") from exc
    raise OutputError("Geen vrije bestandsnaam gevonden; er is niets overschreven.")


def load_scan_result(path: str) -> Dict[str, Any]:
    """Leest een opgeslagen scan terug en controleert of het een geldige, geslaagde scan is.

    Alleen lezen. Een afgebroken of beschadigd bestand, een bestand van een ander
    programma, een onbekende hoofdversie van het formaat of een mislukte scan wordt
    geweigerd met een ResultFileError.
    """
    if not isinstance(path, str) or not path.strip():
        raise ResultFileError("Geen bestand opgegeven.")
    try:
        if os.path.getsize(path) > MAX_RESULT_BYTES:
            raise ResultFileError("Het scanbestand is onverwacht groot.")
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except ResultFileError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResultFileError(
            f"Scanbestand niet leesbaar of geen geldige JSON ({_os_error_text(exc)}).") from exc

    if not isinstance(data, dict):
        raise ResultFileError("Geen scanresultaat: hoofdniveau is geen object.")
    scanner = data.get("scanner")
    if not isinstance(scanner, dict) or scanner.get("name") != SCANNER_NAME:
        raise ResultFileError("Dit bestand is niet door de project scanner gemaakt.")
    version = data.get("schema_version")
    if not isinstance(version, str) or version.split(".")[0] != RESULT_SCHEMA_VERSION.split(".")[0]:
        raise ResultFileError(f"Onbekende formaatversie: {version!r}.")
    projects = data.get("projects")
    if not isinstance(projects, list) or not all(
            isinstance(p, dict) and "id" in p and "state" in p for p in projects):
        raise ResultFileError("'projects' ontbreekt of heeft een ongeldige opbouw.")
    summary = data.get("summary")
    if not isinstance(summary, dict) or summary.get("outcome") not in SAVEABLE_OUTCOMES:
        raise ResultFileError("Dit bestand is geen geslaagde scan (uitkomst ontbreekt of is mislukt).")
    return data


# --------------------------------------------------------------------------
# Opdrachtregel
# --------------------------------------------------------------------------

def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "backslashreplace").decode("ascii"))


def _non_negative(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("moet 0 of hoger zijn")
    return number


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("moet 1 of hoger zijn")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project_scanner",
        description="Project Scanner (alleen lezen). Een geslaagde scan wordt als nieuw "
                    "JSON-bestand bewaard als er een uitvoermap is; anders gaat de JSON naar het scherm.")
    parser.add_argument("--config", required=True,
                        help="Pad naar het JSON-configuratiebestand.")
    where = parser.add_mutually_exclusive_group()
    where.add_argument("--output-dir",
                       help="Bestaande map voor het resultaat. Gaat voor op 'output_dir' uit de "
                            "configuratie. Altijd een nieuw bestand, nooit overschrijven.")
    where.add_argument("--no-save", action="store_true",
                       help="Niet opslaan, ook niet als de configuratie een 'output_dir' heeft: "
                            "toon de JSON op het scherm.")
    parser.add_argument("--max-depth", type=_non_negative, default=DEFAULT_MAX_DEPTH,
                        help=f"Maximale mapdiepte (standaard {DEFAULT_MAX_DEPTH}).")
    parser.add_argument("--max-entries", type=_positive, default=DEFAULT_MAX_ENTRIES,
                        help=f"Maximaal aantal items per project (standaard {DEFAULT_MAX_ENTRIES}).")
    parser.add_argument("--version", action="version", version=f"{SCANNER_NAME} {SCANNER_VERSION}")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run_scan(args.config, max_depth=args.max_depth, max_entries=args.max_entries)
    except ConfigError as exc:
        print(f"Configuratiefout: {exc}", file=sys.stderr)
        return 1

    summary = result["summary"]
    target_dir = None if args.no_save else (args.output_dir or result["config"].get("output_dir"))

    if target_dir:
        try:
            target = write_result(result, target_dir)
        except NotSavedError as exc:
            print(str(exc), file=sys.stderr)
            for project in result["projects"]:
                print(f"  - {project['id']}: {project['state']}", file=sys.stderr)
            return 3
        except OutputError as exc:
            print(f"Uitvoer geweigerd: {exc}", file=sys.stderr)
            return 2
        _safe_print(f"Scan klaar ({summary['outcome']}): {summary['projects_total']} project(en), "
                    f"status per project: {summary['by_state']}")
        _safe_print(f"Resultaat opgeslagen als nieuw bestand: {target}")
        return 0

    # ensure_ascii=True: veilig voor elke Windows-console of omleiding.
    sys.stdout.write(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
    return 0 if summary["outcome"] in SAVEABLE_OUTCOMES else 3


if __name__ == "__main__":
    sys.exit(main())
