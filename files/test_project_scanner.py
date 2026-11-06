# -*- coding: utf-8 -*-
"""Tests voor Project Scanner v1.0.

Alle tests gebruiken SYNTHETISCHE projecten in een tijdelijke map die na afloop
vanzelf wordt opgeruimd. Er wordt niets aangeraakt buiten die tijdelijke map.

Starten (PowerShell, in de map van dit bestand):
    $env:PYTHONDONTWRITEBYTECODE = "1"   # voorkomt een __pycache__-map
    python -m unittest -v test_project_scanner

Tests die niet kunnen draaien op jouw systeem (bijvoorbeeld symlinks zonder
rechten, of Windows-only tests op Linux) worden als "skipped" gemeld, nooit
stilzwijgend als geslaagd.
"""

import ast
import contextlib
import hashlib
import io
import json
import ntpath
import os
import subprocess
import tempfile
import unittest
from unittest import mock

import project_scanner as ps

SOURCE_PATH = os.path.abspath(ps.__file__)


# --------------------------------------------------------------------------
# Hulpfuncties
# --------------------------------------------------------------------------

def write(path, content="x", binary=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if binary else "w"
    kwargs = {} if binary else {"encoding": "utf-8"}
    with open(path, mode, **kwargs) as handle:
        handle.write(content)


def snapshot(root):
    """Vingerafdruk van een mappenboom: inhoud, grootte, tijdstip, links, mapnamen."""
    state = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs):
            full = os.path.join(current, name)
            rel = os.path.relpath(full, root)
            state[rel] = ("link", os.readlink(full)) if os.path.islink(full) else ("dir",)
        for name in sorted(files):
            full = os.path.join(current, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                state[rel] = ("link", os.readlink(full))
            else:
                with open(full, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
                info = os.stat(full)
                state[rel] = ("file", digest, info.st_size, info.st_mtime_ns)
    return state


class Fixture:
    """Bouwt een synthetische omgeving:

    base/
      allowed/            <- toegestane locatie
        proj_valid/       geldig project met diverse bestandstypen
        proj_disabled/
        proj_deep/        diepe mappenstructuur
      allowed_evil/       <- begint met dezelfde letters als 'allowed'
      outside_project/    <- geldig project, maar buiten de toegestane locatie
      outside_secret/     <- 'geheim' bestand dat nooit in een resultaat mag komen
      out/                <- uitvoermap voor resultaten
    """

    def __init__(self, base):
        self.base = os.path.realpath(base)
        self.allowed = os.path.join(self.base, "allowed")
        self.valid = os.path.join(self.allowed, "proj_valid")
        self.disabled = os.path.join(self.allowed, "proj_disabled")
        self.deep = os.path.join(self.allowed, "proj_deep")
        self.evil = os.path.join(self.base, "allowed_evil", "proj_evil")
        self.outside = os.path.join(self.base, "outside_project")
        self.secret_dir = os.path.join(self.base, "outside_secret")
        self.out = os.path.join(self.base, "out")
        self.build()

    def build(self):
        os.makedirs(self.out)
        write(os.path.join(self.valid, "README.md"), "# test")
        write(os.path.join(self.valid, "PROJECT_STATE.md"), "# state")
        write(os.path.join(self.valid, "HUB_MANIFEST.json"), json.dumps({"ok": True}))
        write(os.path.join(self.valid, "AI_CONTEXT.json"), "{ dit is geen json")
        write(os.path.join(self.valid, "dashboard.html"), "<html></html>")
        write(os.path.join(self.valid, "script.py"), "print('x')")
        write(os.path.join(self.valid, "data.csv"), "a,b\n1,2\n")
        write(os.path.join(self.valid, "foto.PNG"), "png", binary=False)
        write(os.path.join(self.valid, "archief.zip"), "zip")
        write(os.path.join(self.valid, "zonder_extensie"), "x")
        write(os.path.join(self.valid, "sub", "diep", "notities.txt"), "n")
        write(os.path.join(self.valid, "docs", "gids.md"), "# gids")
        write(os.path.join(self.valid, ".git", "HEAD"), "ref: refs/heads/main")
        write(os.path.join(self.valid, "node_modules", "pakket", "index.js"), "x")
        write(os.path.join(self.disabled, "geheim_niet_lezen.md"), "x")
        write(os.path.join(self.deep, "a", "b", "c", "d", "e", "f", "te_diep.md"), "x")
        write(os.path.join(self.deep, "a", "b", "bovenin.md"), "x")
        write(os.path.join(self.evil, "bestand.md"), "x")
        write(os.path.join(self.outside, "README.md"), "x")
        write(os.path.join(self.secret_dir, "secret.txt"), "TOPGEHEIM")

    def entry(self, project_id, path, enabled=True, **extra):
        item = {"id": project_id, "path": path, "enabled": enabled}
        item.update(extra)
        return item

    def config(self, *entries, roots=None):
        return {
            "allowed_roots": roots if roots is not None else [self.allowed],
            "projects": list(entries),
        }

    def write_config(self, config, name="config.json"):
        path = os.path.join(self.base, name)
        write(path, json.dumps(config))
        return path


def by_id(result, project_id):
    for project in result["projects"]:
        if project["id"] == project_id:
            return project
    raise AssertionError(f"project {project_id} niet in resultaat")


class ScannerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="scanner_test_")
        self.addCleanup(self._tmp.cleanup)
        self.fx = Fixture(self._tmp.name)


# --------------------------------------------------------------------------
# 1 tot 5: functionele scenario's
# --------------------------------------------------------------------------

class TestValidAndDisabled(ScannerTestCase):
    def test_01_valid_enabled_project(self):
        cfg = self.fx.config(self.fx.entry(
            "hub", self.fx.valid, name="Testhub", tags=["test", "hub"],
            profile={"type": "synthetisch"}))
        project = by_id(ps.scan_projects(cfg), "hub")

        self.assertEqual(project["state"], "scanned")
        est = project["established"]
        self.assertEqual(est["name"], "Testhub")
        self.assertEqual(est["tags"], ["test", "hub"])
        self.assertEqual(est["profile"], {"type": "synthetisch"})
        self.assertTrue(est["within_allowed_roots"])
        self.assertTrue(est["path_exists"])
        self.assertTrue(est["is_directory"])
        self.assertTrue(est["has_git_folder"])

        derived = project["derived"]
        key_files = {k["path"]: k for k in derived["key_files"]}
        for expected in ("README.md", "PROJECT_STATE.md", "HUB_MANIFEST.json",
                         "AI_CONTEXT.json", "dashboard.html"):
            self.assertIn(expected, key_files)
        self.assertTrue(key_files["HUB_MANIFEST.json"]["json_valid"])
        self.assertFalse(key_files["AI_CONTEXT.json"]["json_valid"])

        docs = [d["path"] for d in derived["documentation"]["listed"]]
        self.assertIn("README.md", docs)
        self.assertIn("docs/gids.md", docs)
        self.assertIn("sub/diep/notities.txt", docs)

        self.assertIn(".git", derived["ignored_directories"])
        self.assertIn("node_modules", derived["ignored_directories"])
        self.assertNotIn("node_modules/pakket/index.js", json.dumps(project))

    def test_02_disabled_project_is_not_touched(self):
        # Pad bestaat niet: een uitgeschakeld project mag dan NIET path_missing geven,
        # want dat zou betekenen dat het pad toch is bekeken.
        cfg = self.fx.config(
            self.fx.entry("uit", self.fx.disabled, enabled=False),
            self.fx.entry("uit_bestaat_niet", os.path.join(self.fx.allowed, "bestaat_niet"),
                          enabled=False))
        result = ps.scan_projects(cfg)
        for project_id in ("uit", "uit_bestaat_niet"):
            project = by_id(result, project_id)
            self.assertEqual(project["state"], "disabled")
            self.assertIsNone(project["derived"])
            self.assertIsNone(project["established"]["path_exists"])
        self.assertNotIn("geheim_niet_lezen", json.dumps(result))

    def test_03_missing_path_does_not_stop_scan(self):
        cfg = self.fx.config(
            self.fx.entry("weg", os.path.join(self.fx.allowed, "bestaat_niet")),
            self.fx.entry("hub", self.fx.valid))
        result = ps.scan_projects(cfg)
        self.assertEqual(by_id(result, "weg")["state"], "path_missing")
        self.assertEqual(by_id(result, "hub")["state"], "scanned")

    def test_03b_path_is_a_file(self):
        target = os.path.join(self.fx.allowed, "los_bestand.md")
        write(target, "x")
        project = by_id(ps.scan_projects(self.fx.config(self.fx.entry("f", target))), "f")
        self.assertEqual(project["state"], "not_a_directory")

    def test_04_invalid_config_per_entry(self):
        cfg = self.fx.config(
            "geen object",
            {"enabled": True, "path": self.fx.valid},                      # id ontbreekt
            self.fx.entry("a", self.fx.valid),
            self.fx.entry("a", self.fx.valid),                             # dubbel id
            {"id": "geen_pad", "enabled": True},
            {"id": "pad_getal", "path": 42, "enabled": True},
            {"id": "relatief", "path": "relatief/pad", "enabled": True},
            {"id": "geen_enabled", "path": self.fx.valid},
            {"id": "enabled_tekst", "path": self.fx.valid, "enabled": "ja"},
            {"id": "tags_fout", "path": self.fx.valid, "enabled": True, "tags": "niet-lijst"},
            {"id": "profile_fout", "path": self.fx.valid, "enabled": True, "profile": 5},
            self.fx.entry("goed", self.fx.valid))
        result = ps.scan_projects(cfg)
        states = {p["id"]: p["state"] for p in result["projects"]}
        self.assertEqual(states["entry-1"], "invalid_config")
        self.assertEqual(states["entry-2"], "invalid_config")
        self.assertEqual(states["a"], "invalid_config")  # tweede 'a' wint de naam; eerste is gescand
        for bad in ("geen_pad", "pad_getal", "relatief", "geen_enabled",
                    "enabled_tekst", "tags_fout", "profile_fout"):
            self.assertEqual(states[bad], "invalid_config", bad)
        self.assertEqual(states["goed"], "scanned")
        scanned_a = [p for p in result["projects"] if p["id"] == "a" and p["state"] == "scanned"]
        self.assertEqual(len(scanned_a), 1)

    def test_04b_unusable_config_files_and_structures(self):
        with self.assertRaises(ps.ConfigError):
            ps.parse_config([])                                   # geen object
        with self.assertRaises(ps.ConfigError):
            ps.parse_config({"projects": []})                     # geen allowed_roots
        with self.assertRaises(ps.ConfigError):
            ps.parse_config({"allowed_roots": [], "projects": []})
        with self.assertRaises(ps.ConfigError):
            ps.parse_config({"allowed_roots": ["relatief"], "projects": []})
        with self.assertRaises(ps.ConfigError):
            ps.parse_config({"allowed_roots": [self.fx.allowed], "projects": "x"})

        kapot = os.path.join(self.fx.base, "kapot.json")
        write(kapot, "{ geen json")
        with self.assertRaises(ps.ConfigError):
            ps.run_scan(kapot)
        with self.assertRaises(ps.ConfigError):
            ps.run_scan(os.path.join(self.fx.base, "bestaat_niet.json"))

    def test_04c_config_with_utf8_bom(self):
        path = os.path.join(self.fx.base, "bom.json")
        with open(path, "w", encoding="utf-8-sig") as handle:
            json.dump(self.fx.config(self.fx.entry("hub", self.fx.valid)), handle)
        self.assertEqual(by_id(ps.run_scan(path), "hub")["state"], "scanned")

    def test_05_file_types_are_counted(self):
        project = by_id(ps.scan_projects(
            self.fx.config(self.fx.entry("hub", self.fx.valid))), "hub")
        cats = project["derived"]["file_categories"]
        exts = project["derived"]["file_extensions"]
        self.assertGreaterEqual(cats["documentation"], 4)
        self.assertEqual(cats["code"], 2)        # script.py, dashboard.html
        self.assertEqual(cats["data"], 3)        # data.csv, 2x json
        self.assertEqual(cats["media"], 1)       # foto.PNG (hoofdletterongevoelig)
        self.assertEqual(cats["archive"], 1)
        self.assertEqual(cats["other"], 1)       # zonder extensie
        self.assertEqual(exts[".png"], 1)
        self.assertEqual(exts["(geen)"], 1)

    def test_05b_never_invents_status(self):
        project = by_id(ps.scan_projects(
            self.fx.config(self.fx.entry("hub", self.fx.valid))), "hub")
        missing = {m["field"] for m in project["missing"]}
        self.assertTrue({"status", "progress", "next_steps"} <= missing)
        self.assertNotIn("status", project["established"])
        self.assertNotIn("status", project["derived"])

    def test_05c_limits_are_reported(self):
        deep = by_id(ps.scan_projects(
            self.fx.config(self.fx.entry("deep", self.fx.deep)), max_depth=2), "deep")
        codes = {u["code"] for u in deep["uncertain"]}
        self.assertIn("depth_limit_reached", codes)
        listed = json.dumps(deep["derived"]["documentation"])
        self.assertIn("a/b/bovenin.md", listed)
        self.assertNotIn("te_diep.md", listed)

        small = by_id(ps.scan_projects(
            self.fx.config(self.fx.entry("hub", self.fx.valid)), max_entries=3), "hub")
        self.assertEqual(small["state"], "partial")
        self.assertIn("scan_truncated", {u["code"] for u in small["uncertain"]})


# --------------------------------------------------------------------------
# 6 en 7: padbeveiliging, links en junctions
# --------------------------------------------------------------------------

class TestPathSafety(ScannerTestCase):
    def test_06_path_outside_allowed_root(self):
        cfg = self.fx.config(
            self.fx.entry("buiten", self.fx.outside),
            self.fx.entry("traversal", os.path.join(self.fx.allowed, "..", "outside_project")),
            self.fx.entry("prefix", self.fx.evil),
            self.fx.entry("niet_bestaand_buiten", os.path.join(self.fx.base, "nergens")))
        result = ps.scan_projects(cfg)
        for project_id in ("buiten", "traversal", "prefix", "niet_bestaand_buiten"):
            project = by_id(result, project_id)
            self.assertEqual(project["state"], "outside_allowed_roots", project_id)
            self.assertIsNone(project["derived"])
            # Buiten de toegestane locaties wordt niet eens gekeken of het pad bestaat.
            self.assertIsNone(project["established"]["path_exists"])
        text = json.dumps(result)
        self.assertNotIn("bestand.md", text)

    def test_06b_windows_path_rules_with_ntpath(self):
        w = ntpath
        self.assertTrue(ps.is_within("J:\\GIT\\PROJECTS\\X", "j:\\git\\projects", w))   # hoofdletters
        self.assertTrue(ps.is_within("J:\\GIT\\PROJECTS", "J:\\GIT\\PROJECTS\\", w))     # gelijk
        self.assertTrue(ps.is_within("J:\\GIT\\PROJECTS\\A\\..\\B", "J:\\GIT\\PROJECTS", w))
        self.assertFalse(ps.is_within("J:\\GIT\\PROJECTS_EVIL\\X", "J:\\GIT\\PROJECTS", w))
        self.assertFalse(ps.is_within("D:\\GIT\\PROJECTS\\X", "J:\\GIT\\PROJECTS", w))   # andere schijf
        self.assertFalse(ps.is_within("J:\\GIT\\PROJECTS\\..\\ELDERS", "J:\\GIT\\PROJECTS", w))
        self.assertFalse(ps.is_within("relatief", "J:\\GIT\\PROJECTS", w))

    def test_07a_symlink_to_outside_is_not_followed(self):
        link_dir = os.path.join(self.fx.valid, "link_naar_buiten")
        link_file = os.path.join(self.fx.valid, "link_naar_geheim.txt")
        try:
            os.symlink(self.fx.secret_dir, link_dir, target_is_directory=True)
            os.symlink(os.path.join(self.fx.secret_dir, "secret.txt"), link_file)
        except (OSError, NotImplementedError, AttributeError) as exc:
            self.skipTest(f"Symlinks maken niet mogelijk op dit systeem: {exc}")

        result = ps.scan_projects(self.fx.config(self.fx.entry("hub", self.fx.valid)))
        project = by_id(result, "hub")
        links = [u for u in project["uncertain"] if u["code"] == "links_not_followed"][0]
        found = {item["path"]: item["kind"] for item in links["sample"]}
        self.assertEqual(set(found), {"link_naar_buiten", "link_naar_geheim.txt"})
        self.assertEqual(set(found.values()), {"symlink"})
        text = json.dumps(result)
        # De bestandsnaam in de doelmap en de inhoud mogen nergens voorkomen.
        self.assertNotIn("secret.txt", text.replace("link_naar_geheim.txt", ""))
        self.assertNotIn("TOPGEHEIM", text)
        self.assertNotIn("outside_secret", json.dumps(project["derived"]))
        # De links zelf tellen niet mee als bestanden of mappen van het project.
        self.assertNotIn("link_naar_buiten", json.dumps(project["derived"]["file_extensions"]))

    def test_07b_project_path_itself_is_symlink_to_outside(self):
        link = os.path.join(self.fx.allowed, "proj_link_buiten")
        try:
            os.symlink(self.fx.outside, link, target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError) as exc:
            self.skipTest(f"Symlinks maken niet mogelijk op dit systeem: {exc}")
        project = by_id(ps.scan_projects(
            self.fx.config(self.fx.entry("l", link))), "l")
        self.assertEqual(project["state"], "outside_allowed_roots")
        self.assertIsNone(project["derived"])

    @unittest.skipUnless(os.name == "nt", "Alleen Windows: junction maken met mklink /J")
    def test_07c_windows_junction_to_outside_is_not_followed(self):
        junction = os.path.join(self.fx.valid, "junction_naar_buiten")
        done = subprocess.run(
            ["cmd", "/c", "mklink", "/J", junction, self.fx.secret_dir],
            capture_output=True, text=True)
        if done.returncode != 0:
            self.skipTest(f"Junction maken mislukt: {done.stderr or done.stdout}")
        result = ps.scan_projects(self.fx.config(self.fx.entry("hub", self.fx.valid)))
        text = json.dumps(result)
        self.assertIn("junction_naar_buiten", text)
        self.assertNotIn("secret.txt", text)
        self.assertNotIn("TOPGEHEIM", text)


# --------------------------------------------------------------------------
# 8: foutafhandeling bij leesrechten en onverwachte fouten
# --------------------------------------------------------------------------

class TestErrorHandling(ScannerTestCase):
    def test_08a_permission_denied_simulated(self):
        real_scandir = os.scandir

        def fake_scandir(path="."):
            if os.fspath(path).endswith("docs"):
                raise PermissionError(13, "Permission denied", os.fspath(path))
            return real_scandir(path)

        cfg = self.fx.config(self.fx.entry("hub", self.fx.valid))
        with mock.patch("project_scanner.os.scandir", side_effect=fake_scandir):
            project = by_id(ps.scan_projects(cfg), "hub")
        self.assertEqual(project["state"], "partial")
        unreadable = [u for u in project["uncertain"] if u["code"] == "unreadable_entries"][0]
        self.assertEqual(unreadable["sample"][0]["path"], "docs")
        # De rest van het project is wel gescand.
        self.assertGreater(project["derived"]["counts"]["files"], 5)

    def test_08b_project_root_unreadable_simulated(self):
        real_scandir = os.scandir
        root = os.path.realpath(self.fx.valid)

        def fake_scandir(path="."):
            if os.path.realpath(os.fspath(path)) == root:
                raise PermissionError(13, "Permission denied", os.fspath(path))
            return real_scandir(path)

        cfg = self.fx.config(self.fx.entry("dicht", self.fx.valid),
                             self.fx.entry("deep", self.fx.deep))
        with mock.patch("project_scanner.os.scandir", side_effect=fake_scandir):
            result = ps.scan_projects(cfg)
        self.assertEqual(by_id(result, "dicht")["state"], "access_denied")
        self.assertEqual(by_id(result, "deep")["state"], "scanned")

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "Echte chmod-test niet mogelijk: Windows of uitgevoerd als root")
    def test_08c_permission_denied_real_chmod(self):
        locked = os.path.join(self.fx.valid, "locked")
        write(os.path.join(locked, "x.md"), "x")
        os.chmod(locked, 0o000)
        self.addCleanup(os.chmod, locked, 0o755)
        project = by_id(ps.scan_projects(
            self.fx.config(self.fx.entry("hub", self.fx.valid))), "hub")
        self.assertEqual(project["state"], "partial")

    def test_08d_unexpected_error_is_isolated_per_project(self):
        real_scan_tree = ps._scan_tree

        def exploding(real_root, max_depth, max_entries):
            if real_root.endswith("proj_valid"):
                raise RuntimeError("synthetische fout")
            return real_scan_tree(real_root, max_depth, max_entries)

        cfg = self.fx.config(self.fx.entry("kapot", self.fx.valid),
                             self.fx.entry("deep", self.fx.deep))
        with mock.patch.object(ps, "_scan_tree", side_effect=exploding):
            result = ps.scan_projects(cfg)
        self.assertEqual(by_id(result, "kapot")["state"], "error")
        self.assertEqual(by_id(result, "deep")["state"], "scanned")
        self.assertEqual(result["summary"]["by_state"], {"error": 1, "scanned": 1})


# --------------------------------------------------------------------------
# Originelen intact, uitvoer, opdrachtregel, statische veiligheidscontroles
# --------------------------------------------------------------------------

class TestReadOnlyAndOutput(ScannerTestCase):
    def test_09_original_files_unchanged(self):
        try:
            os.symlink(self.fx.secret_dir, os.path.join(self.fx.valid, "link"),
                       target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError):
            pass  # zonder symlink-rechten testen we de rest
        before = snapshot(self.fx.base)
        before_out = set(os.listdir(self.fx.out))
        cfg = self.fx.config(
            self.fx.entry("hub", self.fx.valid),
            self.fx.entry("uit", self.fx.disabled, enabled=False),
            self.fx.entry("deep", self.fx.deep),
            self.fx.entry("buiten", self.fx.outside))
        config_path = self.fx.write_config(cfg)
        before_with_config = snapshot(self.fx.base)

        ps.run_scan(config_path)
        ps.write_result(ps.run_scan(config_path), self.fx.out)

        after = snapshot(self.fx.base)
        new_files = set(os.listdir(self.fx.out)) - before_out
        self.assertEqual(len(new_files), 1)
        # Alles buiten de uitvoermap is byte-voor-byte, tijdstip-voor-tijdstip gelijk.
        strip = lambda state: {k: v for k, v in state.items()
                               if not k.startswith("out" + os.sep) and k != "out"}
        self.assertEqual(strip(before_with_config), strip(after))
        self.assertTrue(set(before) <= set(before_with_config))

    def test_10_output_is_new_file_never_overwrites(self):
        result = ps.scan_projects(self.fx.config(self.fx.entry("hub", self.fx.valid)))
        first = ps.write_result(result, self.fx.out)
        with open(first, "rb") as handle:
            content_before = handle.read()
        second = ps.write_result(result, self.fx.out)
        third = ps.write_result(result, self.fx.out)
        self.assertEqual(len({first, second, third}), 3)
        with open(first, "rb") as handle:
            self.assertEqual(handle.read(), content_before)
        with open(first, encoding="utf-8") as handle:
            loaded = json.load(handle)
        self.assertEqual(loaded["schema_version"], ps.RESULT_SCHEMA_VERSION)

    def test_10b_output_location_is_validated(self):
        result = ps.scan_projects(self.fx.config(self.fx.entry("hub", self.fx.valid)))
        with self.assertRaises(ps.OutputError):
            ps.write_result(result, os.path.join(self.fx.base, "bestaat_niet"))
        with self.assertRaises(ps.OutputError):
            ps.write_result(result, self.fx.valid)                       # in een project
        with self.assertRaises(ps.OutputError):
            ps.write_result(result, os.path.join(self.fx.valid, "docs"))  # onder een project
        with self.assertRaises(ps.OutputError):
            ps.write_result(result, "")
        self.assertEqual(os.listdir(self.fx.out), [])
        self.assertFalse(os.path.exists(os.path.join(self.fx.base, "bestaat_niet")))

    def test_11_cli_stdout_and_exit_codes(self):
        config_path = self.fx.write_config(
            self.fx.config(self.fx.entry("hub", self.fx.valid, name="Zoë")))
        buffer, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
            code = ps.main(["--config", config_path])
        self.assertEqual(code, 0)
        text = buffer.getvalue()
        text.encode("ascii")                       # stdout is altijd ASCII-veilig
        self.assertEqual(json.loads(text)["projects"][0]["established"]["name"], "Zoë")

        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(ps.main(["--config", os.path.join(self.fx.base, "nope.json")]), 1)
            self.assertEqual(
                ps.main(["--config", config_path, "--output-dir", self.fx.valid]), 2)
        self.assertEqual(os.listdir(self.fx.out), [])

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = ps.main(["--config", config_path, "--output-dir", self.fx.out])
        self.assertEqual(code, 0)
        self.assertEqual(len(os.listdir(self.fx.out)), 1)

    def test_12_scanner_is_also_importable_for_the_hub(self):
        self.assertTrue(callable(ps.run_scan))
        self.assertTrue(callable(ps.scan_projects))
        for bad in (-1, True, "3"):
            with self.assertRaises(ValueError):
                ps.scan_projects({"allowed_roots": [self.fx.allowed], "projects": []},
                                 max_depth=bad)

    def test_13_static_safety_no_network_no_modifying_calls(self):
        with open(SOURCE_PATH, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())

        allowed_imports = {"__future__", "argparse", "json", "os", "stat", "sys",
                           "datetime", "typing"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertTrue(imported <= allowed_imports, imported - allowed_imports)

        forbidden = {"remove", "unlink", "rmdir", "removedirs", "rename", "renames",
                     "replace", "rmtree", "move", "copy", "copy2", "copyfile",
                     "symlink", "link", "chmod", "chown", "truncate", "utime",
                     "mkdir", "makedirs", "urlopen", "socket", "system", "popen",
                     "Popen", "run", "call", "write_text", "write_bytes"}
        used = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertEqual(used & forbidden, set())

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "open":
                mode = None
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for keyword in node.keywords:
                    if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                        mode = keyword.value.value
                self.assertIn(mode, {"r", "x"}, f"open() met modus {mode!r} op regel {node.lineno}")


# --------------------------------------------------------------------------
# Versie 1.1: JSON-opslag, uitkomstcontrole en terugleggen
# --------------------------------------------------------------------------

FIXED_STEM = "project_scan_20261102_120000"


class StorageTestCase(ScannerTestCase):
    def good_config(self, **extra):
        cfg = self.fx.config(self.fx.entry("hub", self.fx.valid, name="Zo\u00eb \u00dcn\u00efcode",
                                           tags=["a", "b"], profile={"k": "v"}),
                             self.fx.entry("uit", self.fx.disabled, enabled=False))
        cfg.update(extra)
        return cfg

    def partial_config(self):
        return self.fx.config(self.fx.entry("hub", self.fx.valid),
                              self.fx.entry("weg", os.path.join(self.fx.allowed, "bestaat_niet")))

    def failed_config(self):
        return self.fx.config(self.fx.entry("weg", os.path.join(self.fx.allowed, "bestaat_niet")),
                              self.fx.entry("buiten", self.fx.outside),
                              {"id": "kapot", "enabled": True})

    def out_files(self, directory=None):
        return sorted(os.listdir(directory or self.fx.out))


class TestOutcome(StorageTestCase):
    def test_20_outcome_values(self):
        cases = [
            (self.good_config(), "complete"),
            (self.partial_config(), "partial"),
            (self.failed_config(), "failed"),
            (self.fx.config(self.fx.entry("uit", self.fx.disabled, enabled=False)), "nothing_to_scan"),
            (self.fx.config(), "nothing_to_scan"),
        ]
        for cfg, expected in cases:
            summary = ps.scan_projects(cfg)["summary"]
            self.assertEqual(summary["outcome"], expected)
            self.assertTrue(summary["outcome_note"])
        truncated = ps.scan_projects(self.fx.config(self.fx.entry("hub", self.fx.valid)),
                                     max_entries=3)
        self.assertEqual(truncated["summary"]["outcome"], "partial")


class TestJsonStorage(StorageTestCase):
    def test_21_successful_scan_is_saved_as_valid_utf8_json(self):
        result = ps.scan_projects(self.good_config())
        target = ps.write_result(result, self.fx.out)
        self.assertRegex(os.path.basename(target), r"^project_scan_\d{8}_\d{6}\.json$")
        with open(target, "rb") as handle:
            raw = handle.read()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "geen BOM verwacht")
        text = raw.decode("utf-8")                       # moet zonder fout kunnen
        self.assertTrue(text.endswith("\n"))
        self.assertIn("Zo\u00eb \u00dcn\u00efcode", text)   # echte tekens, geen \\u-escapes
        self.assertEqual(json.loads(text)["summary"]["outcome"], "complete")

    def test_22_roundtrip_keeps_all_fields(self):
        result = ps.scan_projects(self.good_config())
        loaded = ps.load_scan_result(ps.write_result(result, self.fx.out))
        self.assertEqual(loaded, json.loads(json.dumps(result)))
        hub = by_id(loaded, "hub")
        self.assertEqual(hub["established"]["name"], "Zo\u00eb \u00dcn\u00efcode")
        self.assertEqual(hub["established"]["tags"], ["a", "b"])
        self.assertEqual(hub["established"]["profile"], {"k": "v"})
        for section in ("established", "derived", "missing", "uncertain", "issues"):
            self.assertIn(section, hub)
        self.assertEqual(hub["derived"]["counts"], by_id(result, "hub")["derived"]["counts"])
        self.assertEqual(by_id(loaded, "uit")["state"], "disabled")
        self.assertEqual(loaded["scanner"]["version"], ps.SCANNER_VERSION)

    def test_23_existing_scan_is_never_overwritten(self):
        result = ps.scan_projects(self.good_config())
        oud = os.path.join(self.fx.out, FIXED_STEM + ".json")
        write(oud, "OUD BESTAND, NIET AANRAKEN")
        with mock.patch.object(ps, "_file_stem", return_value=FIXED_STEM):
            second = ps.write_result(result, self.fx.out)
            third = ps.write_result(result, self.fx.out)
        self.assertEqual(os.path.basename(second), FIXED_STEM + "_2.json")
        self.assertEqual(os.path.basename(third), FIXED_STEM + "_3.json")
        with open(oud, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "OUD BESTAND, NIET AANRAKEN")
        self.assertEqual(len(self.out_files()), 3)

    def test_24_failed_scan_is_not_saved(self):
        for cfg in (self.failed_config(), self.fx.config()):
            result = ps.scan_projects(cfg)
            with self.assertRaises(ps.NotSavedError):
                ps.write_result(result, self.fx.out)
            # Een vervalst 'complete'-label verandert dat niet: de uitkomst wordt herberekend.
            result["summary"]["outcome"] = "complete"
            with self.assertRaises(ps.NotSavedError):
                ps.write_result(result, self.fx.out)
        with self.assertRaises(ps.NotSavedError):
            ps.write_result({"projects": []}, self.fx.out)
        with self.assertRaises(ps.NotSavedError):
            ps.write_result("onzin", self.fx.out)
        self.assertEqual(self.out_files(), [])

    def test_25_partial_scan_is_saved_but_labelled(self):
        result = ps.scan_projects(self.partial_config())
        target = ps.write_result(result, self.fx.out)
        self.assertTrue(os.path.basename(target).endswith("_partial.json"))
        loaded = ps.load_scan_result(target)
        self.assertEqual(loaded["summary"]["outcome"], "partial")
        self.assertEqual(by_id(loaded, "weg")["state"], "path_missing")
        self.assertEqual(by_id(loaded, "hub")["state"], "scanned")

    def test_26_unusual_characters_do_not_leave_an_empty_file(self):
        result = ps.scan_projects(self.good_config())
        by_id(result, "hub")["established"]["name"] = "kapot\udc80teken"   # ongeldig in UTF-8
        target = ps.write_result(result, self.fx.out)
        self.assertGreater(os.path.getsize(target), 100)
        loaded = ps.load_scan_result(target)
        self.assertEqual(by_id(loaded, "hub")["established"]["name"], "kapot\udc80teken")

    def test_27_save_does_not_touch_projects(self):
        before = snapshot(self.fx.allowed)
        before_other = snapshot(self.fx.secret_dir)
        ps.write_result(ps.scan_projects(self.good_config()), self.fx.out)
        self.assertEqual(snapshot(self.fx.allowed), before)
        self.assertEqual(snapshot(self.fx.secret_dir), before_other)


class TestLoadScanResult(StorageTestCase):
    def saved(self):
        return ps.write_result(ps.scan_projects(self.good_config()), self.fx.out)

    def put(self, name, content):
        path = os.path.join(self.fx.base, name)
        write(path, content)
        return path

    def test_28_rejects_unusable_files(self):
        good_path = self.saved()
        with open(good_path, encoding="utf-8") as handle:
            good_text = handle.read()
        good = json.loads(good_text)

        def variant(label, **changes):
            data = json.loads(good_text)
            data.update(changes)
            return self.put("variant_%s.json" % label, json.dumps(data))   # elk een eigen bestand

        bad_files = {
            "afgebroken": self.put("afgebroken.json", good_text[: len(good_text) // 2]),
            "geen_json": self.put("geen.json", "dit is geen json"),
            "lijst": self.put("lijst.json", "[1, 2, 3]"),
            "leeg": self.put("leeg.json", ""),
            "ander_programma": variant("ander_programma", scanner={"name": "iets_anders", "version": "1"}),
            "nieuwe_hoofdversie": variant("nieuwe_hoofdversie", schema_version="2.0"),
            "versie_geen_tekst": variant("versie_geen_tekst", schema_version=1.1),
            "projects_ontbreekt": variant("projects_ontbreekt", projects="geen lijst"),
            "project_zonder_state": variant("project_zonder_state", projects=[{"id": "x"}]),
            "mislukte_scan": variant("mislukte_scan", summary={"outcome": "failed", "projects_total": 1}),
            "zonder_uitkomst": variant("zonder_uitkomst", summary={"projects_total": 1}),
            "bestaat_niet": os.path.join(self.fx.base, "nergens.json"),
        }
        self.assertEqual(len(set(bad_files.values())), len(bad_files), "varianten delen een bestand")
        for label, path in bad_files.items():
            with self.assertRaises(ps.ResultFileError, msg=label):
                ps.load_scan_result(path)
        with self.assertRaises(ps.ResultFileError):
            ps.load_scan_result("")
        # Het goede bestand blijft wel leesbaar en is niet veranderd door deze controles.
        self.assertEqual(ps.load_scan_result(good_path), good)

    def test_29_older_minor_version_is_accepted(self):
        path = self.saved()
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        data["schema_version"] = "1.0"
        legacy = self.put("v10.json", json.dumps(data))
        self.assertEqual(ps.load_scan_result(legacy)["schema_version"], "1.0")


class TestStorageCli(StorageTestCase):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ps.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_30_config_output_dir_saves_automatically(self):
        cfg_path = self.fx.write_config(self.good_config(output_dir=self.fx.out))
        code, out, err = self.run_main("--config", cfg_path)
        self.assertEqual(code, 0, err)
        self.assertIn("opgeslagen", out.lower())
        files = self.out_files()
        self.assertEqual(len(files), 1)
        loaded = ps.load_scan_result(os.path.join(self.fx.out, files[0]))
        self.assertEqual(loaded["config"]["output_dir"], self.fx.out)

    def test_31_no_save_prints_and_writes_nothing(self):
        cfg_path = self.fx.write_config(self.good_config(output_dir=self.fx.out))
        code, out, _ = self.run_main("--config", cfg_path, "--no-save")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["summary"]["outcome"], "complete")
        self.assertEqual(self.out_files(), [])

    def test_32_cli_output_dir_overrides_config_and_conflicts_are_refused(self):
        other = os.path.join(self.fx.base, "out2")
        os.makedirs(other)
        cfg_path = self.fx.write_config(self.good_config(output_dir=self.fx.out))
        code, _, err = self.run_main("--config", cfg_path, "--output-dir", other)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.out_files(), [])
        self.assertEqual(len(self.out_files(other)), 1)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                ps.main(["--config", cfg_path, "--output-dir", other, "--no-save"])
        self.assertEqual(raised.exception.code, 2)

    def test_33_failed_scan_gives_exit_3_and_saves_nothing(self):
        cfg_path = self.fx.write_config(dict(self.failed_config(), output_dir=self.fx.out))
        code, out, err = self.run_main("--config", cfg_path)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("mislukt", err)
        self.assertIn("weg: path_missing", err)
        self.assertEqual(self.out_files(), [])

        no_dir = self.fx.write_config(self.failed_config(), name="geen_uitvoermap.json")
        code, out, _ = self.run_main("--config", no_dir)       # naar het scherm: wel tonen
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["summary"]["outcome"], "failed")

    def test_34_partial_scan_via_cli_is_saved_and_labelled(self):
        cfg_path = self.fx.write_config(dict(self.partial_config(), output_dir=self.fx.out))
        code, out, _ = self.run_main("--config", cfg_path)
        self.assertEqual(code, 0)
        self.assertIn("partial", out)
        self.assertTrue(self.out_files()[0].endswith("_partial.json"))

    def test_35_unsafe_or_missing_output_locations(self):
        inside = os.path.join(self.fx.valid, "docs")
        missing = os.path.join(self.fx.base, "bestaat_niet")
        for number, location in enumerate((inside, missing)):
            cfg_path = self.fx.write_config(self.good_config(output_dir=location),
                                            name="cfg_%d.json" % number)
            code, _, err = self.run_main("--config", cfg_path)
            self.assertEqual(code, 2, err)
        self.assertEqual(self.out_files(), [])
        self.assertFalse(os.path.exists(missing))
        self.assertEqual(os.listdir(inside), ["gids.md"])

    def test_36_invalid_output_dir_in_config_stops_the_scan(self):
        for bad in ("relatief/pad", 5, "", ["lijst"]):
            with self.assertRaises(ps.ConfigError, msg=repr(bad)):
                ps.parse_config(dict(self.good_config(), output_dir=bad))
        parsed = ps.parse_config(dict(self.good_config(), output_dir=self.fx.out))
        self.assertEqual(parsed["output_dir"], self.fx.out)
        self.assertIsNone(ps.parse_config(self.good_config())["output_dir"])

    def test_37_cli_save_leaves_originals_untouched(self):
        cfg_path = self.fx.write_config(self.good_config(output_dir=self.fx.out))
        before = snapshot(self.fx.base)
        code, _, err = self.run_main("--config", cfg_path)
        self.assertEqual(code, 0, err)
        after = snapshot(self.fx.base)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        self.assertEqual({k for k in changed if not k.startswith("out")}, set())
        self.assertEqual(len([k for k in changed if k.startswith("out" + os.sep)]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
