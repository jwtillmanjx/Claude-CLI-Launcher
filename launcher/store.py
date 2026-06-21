"""Data layer: reading and writing the launcher's on-disk state.

Four files live next to the app (see ``config``):

    project-list-directories.csv   known projects + last-launched timestamps
    project-scan-directories.txt   parent dirs scanned for child projects
    project-excluded-directories.txt   projects the user removed (don't re-add)
    launcher.ini                   last-used model, model history, toggle states

A project is represented throughout as a ``[full_path, timestamp]`` list, where
timestamp is an ISO-8601 string or "" if it has never been launched.
"""

import configparser
import csv
import os

from .config import (CSV_PATH, EXCLUDED_PATH, INI_PATH, SCAN_PATH)


def _norm(path):
    """Case-insensitive, normalized path key for comparing Windows paths."""
    return os.path.normcase(os.path.normpath(path))


def ensure_files():
    """Create the three plain-text data files if they don't exist yet."""
    for path in (CSV_PATH, SCAN_PATH, EXCLUDED_PATH):
        if not os.path.exists(path):
            open(path, "w", encoding="utf-8").close()


# ── Excluded projects ────────────────────────────────────────────────────────
def read_excluded():
    """Return a set of normalized paths the user has explicitly removed."""
    ensure_files()
    excluded = set()
    with open(EXCLUDED_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                excluded.add(_norm(line))
    return excluded


def write_excluded(excluded):
    with open(EXCLUDED_PATH, "w", encoding="utf-8") as f:
        for path in sorted(excluded):
            f.write(path + "\n")


# ── Project list (CSV) ───────────────────────────────────────────────────────
def read_csv():
    """Return a list of ``[full_path, timestamp]`` rows, de-duplicated by path."""
    ensure_files()
    rows = []
    seen = set()
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            path = row[0].strip()
            timestamp = row[1].strip() if len(row) > 1 else ""
            key = _norm(path)
            if key not in seen:
                seen.add(key)
                rows.append([path, timestamp])
    return rows


def write_csv(rows):
    # QUOTE_ALL so paths containing commas survive the round-trip.
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        for row in rows:
            writer.writerow(row)


# ── Scan directories ─────────────────────────────────────────────────────────
def read_scan_dirs():
    ensure_files()
    dirs = []
    with open(SCAN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                dirs.append(line)
    return dirs


def write_scan_dirs(dirs):
    with open(SCAN_PATH, "w", encoding="utf-8") as f:
        for d in dirs:
            f.write(d + "\n")


# ── INI (model + options) ────────────────────────────────────────────────────
def _load_ini():
    """Return a ConfigParser for the ini (empty if missing or unreadable)."""
    cfg = configparser.ConfigParser(interpolation=None)
    if os.path.exists(INI_PATH):
        try:
            cfg.read(INI_PATH, encoding="utf-8")
        except Exception:
            pass
    return cfg


def _save_ini(cfg):
    with open(INI_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)


def read_model_config():
    """Return ``(selected_model, [history...])`` from the ini.

    Creates the ini with an empty Models section if it does not exist. History
    is stored as a single pipe-delimited value because model names contain
    characters (e.g. ``[1m]``) that would be ambiguous as ini keys.
    """
    if not os.path.exists(INI_PATH):
        write_model_config("", [])
        return "", []
    cfg = _load_ini()
    selected = cfg.get("Models", "selected", fallback="").strip()
    history = []
    for item in cfg.get("Models", "history", fallback="").split("|"):
        item = item.strip()
        if item and item not in history:
            history.append(item)
    return selected, history


def write_model_config(selected, history):
    """Persist the Models section, preserving any other sections in the ini."""
    cfg = _load_ini()
    if not cfg.has_section("Models"):
        cfg.add_section("Models")
    cfg.set("Models", "selected", selected or "")
    cfg.set("Models", "history", "|".join(history))
    _save_ini(cfg)


def read_options():
    """Return ``(skip_permissions, run_as_admin)`` booleans.

    Defaults match the original behavior: skip permissions ON, admin OFF.
    """
    cfg = _load_ini()
    skip = cfg.getboolean("Options", "skip_permissions", fallback=True)
    admin = cfg.getboolean("Options", "run_as_admin", fallback=False)
    return skip, admin


def write_options(skip_permissions, run_as_admin):
    """Persist the Options section, preserving any other sections in the ini."""
    cfg = _load_ini()
    if not cfg.has_section("Options"):
        cfg.add_section("Options")
    cfg.set("Options", "skip_permissions", "true" if skip_permissions else "false")
    cfg.set("Options", "run_as_admin", "true" if run_as_admin else "false")
    _save_ini(cfg)


# ── Project derivation ───────────────────────────────────────────────────────
def path_in_list(path, rows):
    """True if ``path`` already appears (case-insensitively) in ``rows``."""
    key = _norm(path)
    return any(_norm(row[0]) == key for row in rows)


def derive_projects(scan_dir, rows, excluded=None):
    """Append immediate child directories of ``scan_dir`` to ``rows``.

    Skips children already present or in ``excluded``. Mutates ``rows`` in place
    and returns the list of newly added full paths.
    """
    if excluded is None:
        excluded = set()
    added = []
    if not os.path.isdir(scan_dir):
        return added
    try:
        children = os.listdir(scan_dir)
    except OSError:
        return added
    for child in sorted(children):
        full = os.path.join(scan_dir, child)
        if (os.path.isdir(full)
                and not path_in_list(full, rows)
                and _norm(full) not in excluded):
            rows.append([full, ""])
            added.append(full)
    return added
