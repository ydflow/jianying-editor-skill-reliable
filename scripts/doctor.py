"""Read-only environment diagnostics for JianYing Editor Reliable."""

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

from utils.formatters import get_default_drafts_root


def _read_requirements(skill_root: Path) -> list[tuple[str, str]]:
    requirements = []
    path = skill_root / "requirements.txt"
    if not path.exists():
        return requirements
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line:
            name, expected = line.split("==", 1)
        else:
            name, expected = line, ""
        requirements.append((name.strip(), expected.strip()))
    return requirements


def _package_status(skill_root: Path) -> list[dict]:
    result = []
    for name, expected in _read_requirements(skill_root):
        try:
            actual = importlib.metadata.version(name)
            state = "ok" if not expected or actual == expected else "version_mismatch"
        except importlib.metadata.PackageNotFoundError:
            actual = None
            state = "missing"
        result.append(
            {"name": name, "expected": expected or None, "actual": actual, "state": state}
        )
    return result


def _detect_windows_jianying() -> dict:
    if sys.platform != "win32":
        return {"installed": None, "version": None, "executable": None}

    candidates = []
    version = None
    try:
        import winreg

        roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
        uninstall_paths = (
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
            r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        for root in roots:
            for uninstall_path in uninstall_paths:
                try:
                    with winreg.OpenKey(root, uninstall_path) as parent:
                        for index in range(winreg.QueryInfoKey(parent)[0]):
                            try:
                                with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as item:
                                    name = str(winreg.QueryValueEx(item, "DisplayName")[0])
                                    if "剪映" not in name and "jianying" not in name.lower():
                                        continue
                                    try:
                                        version = str(
                                            winreg.QueryValueEx(item, "DisplayVersion")[0]
                                        )
                                    except OSError:
                                        pass
                                    for value_name in ("InstallLocation", "DisplayIcon"):
                                        try:
                                            value = str(
                                                winreg.QueryValueEx(item, value_name)[0]
                                            ).strip('"')
                                            if value:
                                                candidates.append(value)
                                        except OSError:
                                            pass
                            except OSError:
                                continue
                except OSError:
                    continue
    except ImportError:
        pass

    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        candidates.extend(
            [
                os.path.join(local_app_data, "JianyingPro", "Apps", "JianyingPro.exe"),
                os.path.join(local_app_data, "JianyingPro", "JianyingPro.exe"),
            ]
        )

    expanded = []
    for candidate in candidates:
        candidate = candidate.split(",", 1)[0]
        expanded.append(candidate)
        if os.path.isfile(candidate):
            expanded.append(os.path.join(os.path.dirname(candidate), "JianyingPro.exe"))
        elif os.path.isdir(candidate):
            expanded.append(os.path.join(candidate, "JianyingPro.exe"))

    executable = next(
        (
            os.path.abspath(path)
            for path in expanded
            if os.path.isfile(path) and os.path.basename(path).lower() == "jianyingpro.exe"
        ),
        None,
    )
    return {"installed": bool(executable or version), "version": version, "executable": executable}


def detect_jianying_installation() -> dict:
    if sys.platform == "win32":
        return _detect_windows_jianying()
    app_candidates = [
        "/Applications/JianyingPro.app",
        os.path.expanduser("~/Applications/JianyingPro.app"),
    ]
    app = next((path for path in app_candidates if os.path.exists(path)), None)
    return {"installed": bool(app), "version": None, "executable": app}


def _detect_playwright_browser() -> dict:
    """Resolve the Chromium executable required by the installed Playwright build."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = playwright.chromium.executable_path
    except Exception:
        executable = None

    executable = os.path.abspath(executable) if executable else None
    return {
        "installed": bool(executable and os.path.isfile(executable)),
        "executable": executable,
    }


def collect_diagnostics(
    skill_root: Optional[str] = None, drafts_root: Optional[str] = None
) -> dict:
    """Collect diagnostics without creating, changing, or deleting a draft."""
    root = Path(skill_root or Path(__file__).resolve().parents[1]).resolve()
    resolved_drafts_root = os.path.abspath(drafts_root or get_default_drafts_root())
    packages = _package_status(root)
    playwright_browser = _detect_playwright_browser()
    jianying = detect_jianying_installation()

    warnings = []
    if not os.path.isdir(resolved_drafts_root):
        warnings.append("drafts_root_missing")
    if shutil.which("ffmpeg") is None:
        warnings.append("ffmpeg_missing")
    if shutil.which("ffprobe") is None:
        warnings.append("ffprobe_missing")
    if any(package["state"] == "missing" for package in packages):
        warnings.append("python_dependencies_missing")
    if any(package["state"] == "version_mismatch" for package in packages):
        warnings.append("python_dependency_version_mismatch")
    if not playwright_browser["installed"]:
        warnings.append("playwright_browser_missing")

    version = jianying.get("version") or ""
    try:
        major, minor = [int(part) for part in version.split(".")[:2]]
    except (ValueError, TypeError):
        major, minor = None, None
    auto_export_supported = (
        sys.platform == "win32"
        and major is not None
        and (major < 5 or (major == 5 and (minor or 0) <= 9))
    )
    if sys.platform == "win32" and major is not None and not auto_export_supported:
        warnings.append("auto_export_unverified_for_installed_version")

    return {
        "ok": not any(
            warning
            in {
                "drafts_root_missing",
                "ffmpeg_missing",
                "ffprobe_missing",
                "python_dependencies_missing",
            }
            for warning in warnings
        ),
        "code": "ok" if not warnings else "warnings",
        "read_only": True,
        "platform": platform.platform(),
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "console": {
            "stdout_encoding": getattr(sys.stdout, "encoding", None),
            "stderr_encoding": getattr(sys.stderr, "encoding", None),
        },
        "commands": {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")},
        "packages": packages,
        "playwright_browser": playwright_browser,
        "jianying": {**jianying, "auto_export_supported": auto_export_supported},
        "drafts_root": resolved_drafts_root,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only JianYing environment diagnostics")
    parser.add_argument("--drafts-root", help="Override draft root for this check")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    result = collect_diagnostics(drafts_root=args.drafts_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"JianYing doctor: {result['code']}")
        print(f"Drafts root: {result['drafts_root']}")
        print(f"JianYing: {result['jianying']}")
        print(f"Warnings: {', '.join(result['warnings']) or 'none'}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
