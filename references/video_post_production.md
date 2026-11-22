# Video Post-Production & `surgical-media` Visual Polish

Plastic Surgery enhances `surgical-media` videos across two non-destructive modes. Both modes preserve audio-first timing, narration, attributions, and credits.

---

## 1. Two Video Surgery Modes

| Mode | When to Use | What Changes | Output |
| :--- | :--- | :--- | :--- |
| **Mode A: Storyboard & 3D Pre-Render Surgery** *(Preferred)* | `storyboard.json` (or `storyboard.styled.json`) is available | `style.palette`, `style.grade`, `camera` easings/transitions, personality layers, `scene_spec` lighting, custom `.mjs` / `.glb` | Re-rendered master MP4 via `surgical-media/scripts/render_engine.py` (zero generation loss) |
| **Mode B: Single-Pass FFmpeg Finishing Surgery** | Only a rendered `.mp4` exists, or platform delivery adaptation is needed | Single-pass `filter_complex` (grade, captions, FPS/scale, BT.709, two-pass `loudnorm`, `+faststart`) | New finished MP4 (`final.polished.mp4`; original master untouched) |

---

## 2. Zero-Regression Video Contract (Immutable Fields)

- **Storyboard Immutables**: `meta.seed`, `format.{width,height,fps}` (unless explicit platform adaptation), `scenes[].scene_id`, `start_sec`, `duration_sec`, `vo_wav`, `narration`, `words[]`, `sfx_events[]`, `anchors_3d[].{anchor_id,label,metric,local_pos}`, `attribution` / `source_tag`, `credits.json`, `CREDITS.md`, and AI-disclosure flags.
- **MP4 Immutables**: VO A/V sync (`<= 150 ms` drift), attribution badges inside safe zones, and the original source file.

---

## 3. Mode A Playbook: `surgical-media` Storyboard & 3D Polish

1. **Pre-Op Audit**:
   ```bash
   python3 scripts/preflight_video_polish.py path/to/storyboard.json --safe-mode strict --json
   python3 scripts/preflight_visual_lint.py path/to/threejs_dir --fail-on high
   python3 scripts/preflight_gltf_budget.py path/to/asset.glb --tier medium --fail-on high
   ```
3. **Polish & Validate** (non-destructive, SHA-256 immutable proof):
   ```bash
   python3 scripts/polish_surgical_media.py storyboard \
     --in path/to/storyboard.json --out path/to/storyboard.polished.json \
     --look preserve --safe-mode strict --report reports/polish_action.json
   python3 scripts/preflight_video_polish.py path/to/storyboard.polished.json --fail-on high
   ```
   Then validate and render inside `surgical-media`:
   ```bash
   python3 scripts/storyboard.py storyboard.polished.json
   python3 scripts/style_lint.py storyboard.polished.json
   python3 scripts/render_engine.py --storyboard storyboard.polished.json --thumbnails /tmp/sm_thumbs
   python3 scripts/render_engine.py --storyboard storyboard.polished.json --output final.mp4 --quality final
   ```

---

## 4. Mode B Playbook: Single-Pass FFmpeg Finishing Recipes

### 4.1 Frame-Rate Normalization + BT.709 + `+faststart`

```bash
ffmpeg -y -i input.mp4 \
  -vf "fps=30,format=yuv420p,scale=1920:1080:flags=lanczos" \
  -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart \
  output.mp4
```

### 4.2 Tactile Filmic Grade + Anti-Banding Grain + Subtle Vignette

```bash
ffmpeg -y -i input.mp4 \
  -vf "eq=contrast=1.05:brightness=0.02:saturation=1.08,vignette=PI/6,noise=alls=3:allf=t+u,fps=30,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a copy -movflags +faststart \
  graded.mp4
```

### 4.3 Burned-In Captions Inside Social Safe Zones

```bash
# 16:9 (MarginV=80); for 9:16 strict ad-safe, raise MarginV=680 on 1080x1920
ffmpeg -y -i input.mp4 \
  -vf "subtitles=captions.srt:force_style='FontSize=28,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Shadow=1,MarginV=80,Alignment=2',fps=30,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a copy -movflags +faststart \
  captioned.mp4
```

### 4.4 Two-Pass EBU R128 Audio Loudness Mastering

```bash
# Pass 1: Measure integrated loudness (-14 LUFS target, -1.5 dBTP ceiling)
ffmpeg -hide_banner -i input.mp4 \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" \
  -f null - 2> loudnorm_pass1.log

# Pass 2: Apply linear gain using measured_I, measured_TP, measured_LRA, measured_thresh, offset
ffmpeg -y -i input.mp4 \
  -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=-23.2:measured_TP=-4.1:measured_LRA=8.5:measured_thresh=-34.2:offset=0.1:linear=true" \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart \
  mastered.mp4
```

### 4.5 Topic-Matched Intro/Outro Bumpers + Single-Pass Concat

Always pair generated video pads with `anullsrc` stereo 48 kHz audio, normalize all video/audio streams (`setsar=1,fps=30,format=yuv420p` and `aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS`), and escape colons (`\:`) inside `drawtext`:

```bash
ffmpeg -y \
  -i main.mp4 \
  -f lavfi -t 3 -i "anullsrc=r=48000:cl=stereo" \
  -f lavfi -t 4 -i "anullsrc=r=48000:cl=stereo" \
  -filter_complex "\
    color=c=0x0B0E18:size=1920x1080:rate=30:duration=3[ib];\
    [ib]drawtext=text='Topic Title':fontsize=72:fontcolor=0xF1F4FA:x=(w-text_w)/2:y=(h-text_h)/2-40,\
        drawtext=text='Key Question':fontsize=38:fontcolor=0x5E9EFF:x=(w-text_w)/2:y=(h-text_h)/2+40,\
        fade=t=in:st=0:d=0.4,fade=t=out:st=2.6:d=0.4,setsar=1,format=yuv420p[intro_v];\
    [1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[intro_a];\
    [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,eq=contrast=1.05:brightness=0.02:saturation=1.08,fps=30,format=yuv420p[main_v];\
    [0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[main_a];\
    color=c=0x0B0E18:size=1920x1080:rate=30:duration=4[ob];\
    [ob]drawtext=text='Sources\: See Description':fontsize=52:fontcolor=0xF1F4FA:x=(w-text_w)/2:y=(h-text_h)/2-20,\
        fade=t=in:st=0:d=0.4,fade=t=out:st=3.6:d=0.4,setsar=1,format=yuv420p[outro_v];\
    [2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[outro_a];\
    [intro_v][intro_a][main_v][main_a][outro_v][outro_a]concat=n=3:v=1:a=1[vout][acat]\
  " \
  -map "[vout]" -map "[acat]" \
  -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart \
  final_polished.mp4
```

### 4.6 Cross-Platform Aspect Adaptation (`16:9` -> `9:16` Blurred-Backdrop Reframe)

```bash
ffmpeg -y -i input_16x9.mp4 \
  -filter_complex "\
    [0:v]split=2[bg][fg];\
    [bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[bg_blur];\
    [fg]scale=1080:-2:force_original_aspect_ratio=decrease[fg_fit];\
    [bg_blur][fg_fit]overlay=(W-w)/2:(H-h)/2-120,fps=30,format=yuv420p[vout]\
  " \
  -map "[vout]" -map 0:a \
  -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a copy -movflags +faststart \
  shorts_9x16.mp4
```

### 4.7 Dual Safe-Zone QC Overlay (QC Only — Remove Before Delivery)

Never place `#` comments inside quoted FFmpeg filter strings:

```bash
# 9:16 (1080x1920): 0xFFB400 (amber) = organic (60,180,870,1360), 0xFF3030 (red) = strict (65,288,823,960)
ffmpeg -y -i final.mp4 \
  -vf "drawbox=x=60:y=180:w=870:h=1360:color=0xFFB400@0.35:t=3,drawbox=x=65:y=288:w=823:h=960:color=0xFF3030@0.45:t=3" \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  safezone_9x16_qc.mp4
```

---

## 5. Platform Spec & Safe-Zone Matrix

| Format | Resolution | FPS / Codec | Organic Safe Box | Strict Safe Box |
| :--- | :--- | :--- | :--- | :--- |
| **YouTube 1080p** | `1920x1080` | `30/60`, H.264 High@4.2 `yuv420p` | `1728x972` (90% action) | `1536x864` (80% title) |
| **Shorts / Reels / TikTok** | `1080x1920` | `30/60`, H.264 High@4.2 `yuv420p` | `x=60..930, y=180..1540` | `x=65..888, y=288..1248` |
| **Facebook Feed (4:5)** | `1440x1800` | `30`, H.264 High@4.2 `yuv420p` | `6%` inset | `10%` inset |
| **Square (1:1)** | `1080x1080` | `30`, H.264 High@4.2 `yuv420p` | `6%` inset | `10%` inset |

---

## 6. Hard QC Handoff

```bash
python3 scripts/polish_surgical_media.py video --in final.mp4 --out final_polished.mp4 --look cinematic_clean --loudnorm --qc-frames qc_frames --report reports/video_action.json
python3 scripts/preflight_video_polish.py final_polished.mp4 --measure-audio --measure-visual --fail-on high
# When delivering via surgical-media:
python3 /path/to/surgical-media/scripts/qc_gate.py --video final_polished.mp4 --format 9:16 --preset strict --frames-dir qc_frames --credits CREDITS.md --json qc_report.json
```
