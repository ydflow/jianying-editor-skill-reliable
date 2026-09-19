---
name: audio-voice-generative
description: Rules for generating TTS voiceover and sourcing/downloading background music.
metadata:
  tags: tts, voiceover, bgm, audio
---

# Audio & Voice Rules

## 1) TTS (Preferred)

Use `project.add_tts_intelligent(...)` for narration.

```python
seg = project.add_tts_intelligent(
    "你好，我是全自动剪辑助手。",
    speaker="zh_male_huoli",
    start_time="0s",
    track_name="AudioTrack",
)
```

Recommended speakers:

- `zh_male_huoli`
- `zh_female_xiaopengyou`
- `zh_male_xionger_stream_gpu`
- `zh_female_inspirational`

## 2) TTS + Subtitles Sync

Use `project.add_narrated_subtitles(...)` when you need aligned narration and subtitles in one call.

```python
project.add_narrated_subtitles(
    "欢迎来到 AI 剪辑教程。今天我们演示自动旁白与字幕对齐。",
    speaker="zh_female_xiaopengyou",
    start_time="1s",
    track_name="Subtitles",
)
```

## 3) BGM / SFX Sourcing

Data files:

- `data/jy_cached_audio.csv`: local synced music paths
- `data/cloud_music_library.csv`: cloud music index
- `data/cloud_sound_effects.csv`: cloud sound effects index

Valid APIs in this repo:

- Cloud assets (music/video/sfx): `project.add_cloud_media(query, ...)`
- Explicit cloud music helper: `project.add_cloud_music(query, ...)`
- Local audio file: `project.add_audio_safe(path, ...)`

### Current Recommended Music

When the request says “use the recommended music in JianYing,” inspect the
currently visible **音频 > 音乐素材 > 推荐音乐** list. Treat title, availability,
membership state, and preview as current-session evidence. Do not call a song
from `cloud_music_library.csv` “recommended” unless it was observed in that
UI during the same edit.

Analyze the video’s pace, mood, dialogue and duration, then rank a small set
of currently downloadable candidates. The default operating assumption is that
the user has an active JianYing membership, so membership tracks are eligible.
Preview the selected track before applying it. If the track cannot be downloaded
or its ID is unavailable, stop that selection and choose another eligible
visible candidate; never create a placeholder audio path.

Examples:

```python
# cloud bgm by id
bgm = project.add_cloud_media("7546546694282676275", start_time="0s", duration="12s", track_name="BGM_Track")
if bgm:
    bgm.volume = 0.6

# cloud sfx by id (also through add_cloud_media)
project.add_cloud_media("7135753343380606242", start_time="5s", duration="2s", track_name="SFX_Track")
```

## 4) Mandatory Mixing Rule

When narration and background music coexist, set BGM volume to `0.6` by default.

## 5) Fallback

If cloud/local assets are unavailable, use royalty-free web audio, download to local file, then call `add_audio_safe(...)`.
