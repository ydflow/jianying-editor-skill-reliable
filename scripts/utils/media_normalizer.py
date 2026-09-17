import hashlib
import json
import os
import subprocess
from typing import Optional


def _cache_root() -> str:
    configured = os.getenv("JY_CACHE_ROOT", "").strip()
    if configured:
        return os.path.abspath(configured)
    if os.name == "nt" and os.getenv("LOCALAPPDATA"):
        return os.path.join(os.environ["LOCALAPPDATA"], "JianYingEditorReliable", "cache")
    return os.path.join(os.path.expanduser("~"), ".cache", "jianying-editor-reliable")


def _norm_output_path(
    input_path: str,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    target_fps: Optional[float] = None,
) -> str:
    abs_in = os.path.abspath(input_path)
    stem, _ = os.path.splitext(os.path.basename(abs_in))
    stat = os.stat(abs_in)
    cache_key = "|".join(
        [
            abs_in,
            str(stat.st_size),
            str(stat.st_mtime_ns),
            str(target_width or "source"),
            str(target_height or "source"),
            str(target_fps or "source"),
        ]
    )
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:20]
    cache_dir = os.path.join(_cache_root(), "media")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{stem}.{digest}.__jy_norm__.mp4")


def _is_cache_fresh(src: str, dst: str) -> bool:
    if not os.path.exists(dst):
        return False
    try:
        return os.path.getmtime(dst) >= os.path.getmtime(src)
    except OSError:
        return False


def _probe_video(input_path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,pix_fmt,r_frame_rate",
        "-of",
        "json",
        input_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return {}
    try:
        streams = json.loads(proc.stdout or "{}").get("streams", [])
    except json.JSONDecodeError:
        return {}
    return streams[0] if streams else {}


def should_normalize_video_for_jianying(input_path: str) -> bool:
    info = _probe_video(input_path)
    if not info:
        return False
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    return (
        info.get("codec_name") != "h264"
        or info.get("pix_fmt") != "yuv420p"
        or width <= 0
        or height <= 0
        or width % 2 != 0
        or height % 2 != 0
    )


def normalize_video_for_jianying(
    input_path: str,
    force: bool = False,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    target_fps: Optional[float] = None,
) -> Optional[str]:
    """
    Convert video to JianYing-friendly MP4 before timeline import.

    Output profile:
    - Video: H.264 (libx264), yuv420p
    - Audio: AAC (optional if source has audio)
    - Geometry and frame rate: preserve source values unless explicitly requested
    """
    src = os.path.abspath(input_path)
    if not os.path.exists(src):
        return None
    if not force and not should_normalize_video_for_jianying(src):
        return src

    if bool(target_width) != bool(target_height):
        raise ValueError("target_width and target_height must be provided together")

    dst = _norm_output_path(src, target_width, target_height, target_fps)
    if _is_cache_fresh(src, dst):
        return dst

    if target_width and target_height:
        video_filter = (
            f"scale={int(target_width)}:{int(target_height)}:force_original_aspect_ratio=decrease,"
            f"pad={int(target_width)}:{int(target_height)}:(ow-iw)/2:(oh-ih)/2"
        )
    else:
        video_filter = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        src,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
    ]
    if target_fps:
        cmd.extend(["-r", str(target_fps)])
    cmd.append(dst)

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        print("❌ FFmpeg not found. Cannot normalize video for JianYing import.")
        return None
    except Exception as e:
        print(f"❌ Video normalization failed: {e}")
        return None

    if proc.returncode != 0 or not os.path.exists(dst):
        err = (proc.stderr or proc.stdout or "").strip()
        print(f"❌ Video normalization failed (ffmpeg={proc.returncode}): {err}")
        return None

    return dst


def normalize_webm_for_jianying(input_path: str) -> Optional[str]:
    return normalize_video_for_jianying(input_path, force=True)
