from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from ui_extract_packet import import_packet_into_layout


REQUIRED_SCANNER_FILES = (
    Path("ui/views/main_window.py"),
    Path("ui/views/profile_manager.py"),
    Path("ui/app.py"),
    Path(".venv/bin/python"),
)

SUPPORTED_SCANNER_TARGETS = {"main_window", "profile_manager"}


def validate_scanner_repo_root(repo_root) -> Path:
    root = Path(repo_root).expanduser().resolve()
    if not root.exists():
        raise ValueError("Scanner repo root does not exist")
    if not root.is_dir():
        raise ValueError("Scanner repo root must be a directory")
    missing = [str(path) for path in REQUIRED_SCANNER_FILES if not (root / path).exists()]
    if missing:
        raise ValueError(f"Scanner repo missing required paths: {', '.join(missing)}")
    return root


def validate_scanner_probe_target(target: str) -> str:
    target = str(target).strip()
    if target not in SUPPORTED_SCANNER_TARGETS:
        raise ValueError(f"Unsupported scanner probe target: {target}")
    return target


def build_scanner_packet(repo_root, target: str = "main_window") -> dict:
    root = validate_scanner_repo_root(repo_root)
    target = validate_scanner_probe_target(target)
    python_bin = root / ".venv" / "bin" / "python"
    runtime_script = Path(__file__).resolve().parent / "scanner_ui_probe_runtime.py"
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    completed = subprocess.run(
        [str(python_bin), str(runtime_script), str(root), target],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(completed.stdout)


def build_scanner_main_window_packet(repo_root) -> dict:
    return build_scanner_packet(repo_root, target="main_window")


def build_scanner_profile_manager_packet(repo_root) -> dict:
    return build_scanner_packet(repo_root, target="profile_manager")


def load_scanner_probe(layout_model, repo_root, *, target: str = "main_window", destination: str = "replace") -> list[str]:
    packet = build_scanner_packet(repo_root, target=target)
    return import_packet_into_layout(layout_model, packet, destination=destination)


def load_scanner_main_window(layout_model, repo_root, destination: str = "replace") -> list[str]:
    return load_scanner_probe(layout_model, repo_root, target="main_window", destination=destination)


def load_scanner_profile_manager(layout_model, repo_root, destination: str = "replace") -> list[str]:
    return load_scanner_probe(layout_model, repo_root, target="profile_manager", destination=destination)


def load_scanner_main_window_replace(layout_model, repo_root) -> None:
    load_scanner_main_window(layout_model, repo_root, destination="replace")


def load_scanner_main_window_alongside(layout_model, repo_root) -> list[str]:
    return load_scanner_main_window(layout_model, repo_root, destination="alongside")


def load_scanner_main_window_in_bench(layout_model, repo_root) -> list[str]:
    return load_scanner_main_window(layout_model, repo_root, destination="bench")


def load_scanner_profile_manager_replace(layout_model, repo_root) -> None:
    load_scanner_profile_manager(layout_model, repo_root, destination="replace")


def load_scanner_profile_manager_alongside(layout_model, repo_root) -> list[str]:
    return load_scanner_profile_manager(layout_model, repo_root, destination="alongside")


def load_scanner_profile_manager_in_bench(layout_model, repo_root) -> list[str]:
    return load_scanner_profile_manager(layout_model, repo_root, destination="bench")
