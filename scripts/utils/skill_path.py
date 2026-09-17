import os
from typing import List, Optional, Tuple


def _build_candidates(start_dir: str) -> List[str]:
    """
    Build candidate skill roots for different editors/layouts.
    """
    cwd = os.getcwd()
    parents = [start_dir, os.path.join(start_dir, ".."), os.path.join(start_dir, "..", "..")]
    editor_paths = []
    for base in (start_dir, cwd):
        for skill_name in ("jianying-editor-reliable", "jianying-editor"):
            editor_paths.extend(
                [
                    os.path.join(base, ".agents", "skills", skill_name),
                    os.path.join(base, ".agent", "skills", skill_name),
                    os.path.join(base, ".trae", "skills", skill_name),
                    os.path.join(base, ".claude", "skills", skill_name),
                    os.path.join(base, "skills", skill_name),
                ]
            )
    return parents + editor_paths


def resolve_skill_root(start_dir: str) -> Tuple[Optional[str], List[str]]:
    """
    Resolve skill root by environment variable first, then candidate probing.
    Returns (resolved_root, attempted_paths).
    """
    attempted: List[str] = []

    env_root = os.getenv("JY_SKILL_ROOT", "").strip()
    if env_root:
        env_root = os.path.abspath(env_root)
        attempted.append(env_root)
        if os.path.exists(os.path.join(env_root, "scripts", "jy_wrapper.py")):
            return env_root, attempted

    for p in _build_candidates(start_dir):
        ap = os.path.abspath(p)
        attempted.append(ap)
        if os.path.exists(os.path.join(ap, "scripts", "jy_wrapper.py")):
            return ap, attempted

    return None, attempted


def ensure_skill_scripts_on_path(start_dir: str) -> str:
    """
    Resolve skill root and prepend its scripts path to sys.path.
    Raises ImportError with tried paths when not found.
    """
    import sys

    root, attempted = resolve_skill_root(start_dir)
    if not root:
        msg = "Could not find jianying-editor skill root.\nTried:\n- " + "\n- ".join(attempted)
        raise ImportError(msg)

    scripts_dir = os.path.join(root, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    return root
