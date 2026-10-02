---
name: youtube-render-obsidian
description: Generate a professional, detailed, figure-rich Chinese Obsidian note from a YouTube lecture, tutorial, or technical talk, and publish it into the user's Obsidian vault. Use when the user provides a YouTube URL and wants structured teaching notes in Obsidian (not a PDF) that combine the video's title, chapters, diagrams, formulas, code, subtitle explanations, the original cover, key frames with visible captions and clickable timestamps back to the video, and a final synthesis section.
---

# YouTube Render Obsidian

Use this skill to turn a YouTube video into a complete Obsidian note (Obsidian Flavored Markdown plus local image attachments) and publish it into the user's vault.

This skill keeps the source acquisition, figure-selection, and teaching standards of `youtube-render-pdf` (wdkns-skills), and replaces the LaTeX/PDF delivery with an Obsidian delivery. Markdown is only the carrier: the note must not be thinner than the PDF version would be.

Do not create LaTeX or render a PDF unless the user explicitly asks for it.

## YouTube-Specific Handling

| Aspect | Handling |
|--------|----------|
| **Subtitles** | Prefer manual subtitles over auto-generated ones. Pick the track matching the spoken language; auto-generated tracks are acceptable when no manual track exists. Otherwise ask the user before transcribing with a user-configured speech-to-text MCP, or use visual-only mode |
| **Chapters** | Use the uploader's chapters (from metadata) as the primary outline and splitting boundaries; when metadata has none, parse the timeline in the description |
| **Login / cookies** | Usually not needed. Only for age-restricted, members-only, or "Sign in to confirm you're not a bot" errors: read cookies from a browser once (**Edge first**, other installed browsers as fallback), save them to `cookies.txt`, and use that file for later calls |
| **Language** | Lectures are often in English; write the note in Chinese, keep established English terms, and quote short original English phrases only when the wording itself matters |
| **URL formats** | Support `youtube.com/watch?v=`, `youtu.be/`, `/live/`, and `/shorts/`; strip tracking parameters. For playlist URLs (`&list=`), ask which videos to process |
| **Sponsor segments** | Skip sponsor reads and self-promotion; they are not teaching content |

## Goal

Produce a professional Chinese lecture note in the user's Obsidian vault from a YouTube URL.

The output must:

- use the video's actual teaching content rather than subtitle transcription alone
- carry the video's original cover image at the top of the note
- include all necessary high-value key frames as figures, each with a **visible** caption and a clickable timestamp that jumps back to the video
- end with a final synthesis section that includes the speaker's substantive closing discussion and your own distilled takeaways
- be structured with numbered `##` / `###` headings and valid Obsidian Flavored Markdown (frontmatter, callouts, `$$` math, wikilink embeds, Mermaid)
- be written into the vault through the Obsidian CLI and verified on disk as part of the final delivery

## Pedagogical Standard

The notes must read like a strong human teacher is guiding the reader through the material.

- organize each major section so the reader first understands the motivation, then the main idea, then the mechanism, then the example or evidence, and finally the takeaway
- be patient and explicit about logical transitions; make it clear why the speaker introduces a concept, what problem it solves, and how the next idea follows
- aim for deep-but-accessible explanations: keep the technical depth, but introduce formalism only after giving intuition in plain language
- when a section is dense, break it into smaller subsections that progressively build understanding rather than compressing everything into one long derivation
- do not dump subtitle content in chronological order; rewrite it into a teaching sequence with clear intent, contrast, and buildup

## Before You Start

1. **Find the vault and read its rules.**
   Resolve the open vault from `~/Library/Application Support/obsidian/obsidian.json` (the entry with `"open": true`), or ask the user.
   Read the vault's `CLAUDE.md` / `AGENTS.md` if present and follow them. They override the defaults below (inbox folder, attachment folder, whether files may be written directly).

2. **Default vault layout** (override from the vault rules):
   - note: the vault's inbox folder (`Inbox/` unless its rules say otherwise) — do not file it elsewhere on the user's behalf
   - attachments: the vault's attachment root (`attachments/` unless its rules say otherwise), in a short topic subfolder

3. **Check tools.**
   Required: `yt-dlp`, `ffmpeg`, `magick` (ImageMagick), `jq`, the Obsidian desktop app running with its CLI (`obsidian`).
   Speech-to-text (only when needed and approved): a speech-to-text MCP tool configured by the user (its desktop app, if any, must be running). **Never install Whisper or any other speech-to-text engine.**
   Probe the CLI with a trivial call first (see Publishing). If even `obsidian version` does not return, the CLI is not connected to the app: ask the user to restart Obsidian or enable the CLI, and do not fall back to writing vault files directly unless the user explicitly agrees.

4. **Create a working directory outside the vault** for all intermediate artifacts (video, audio, subtitles, candidate frames, contact sheets, draft note). Only the final note and the selected images ever enter the vault.

## Source Acquisition

### Metadata Inspection

1. Inspect metadata first:
   ```
   yt-dlp -J "<URL>" > meta.json
   ```
   Summarize it with `jq` (do not write ad-hoc `python3 -c` snippets; if Python is really needed, use the vault's `.venv/bin/python`):
   ```
   jq '{title, channel, upload_date, duration, chapters: (.chapters // [] | length),
        subtitles: (.subtitles // {} | keys), auto_captions: (.automatic_captions // {} | keys | length),
        heights: ([.formats[]?.height // empty] | unique)}' meta.json
   jq -r '.chapters[]? | "\(.start_time)\t\(.title)"' meta.json
   jq -r '.description' meta.json
   ```
   Record title, channel, `upload_date`, duration, chapters, formats, manual `subtitles`, and `automatic_captions`, and read the full description.

2. **Chapters from the description.** When `chapters` is empty, look for a timeline in the description (lines such as `0:00 Intro`, `12:42 - Context size`, `1:02:30 Title`). Convert it into a chapter list (start time, title, end = next start or video end) and use it as the outline and segment boundaries.

3. If the URL is a playlist or the user mentions several videos, list them and ask which to process.

4. **Cookies, only when needed.** If a request fails with an age-restriction, members-only, or bot-check error, read cookies from a browser once and save them to `cookies.txt`, then use `--cookies cookies.txt` for every later call:
   ```
   yt-dlp --cookies-from-browser edge --cookies cookies.txt -J "<URL>" > meta.json
   ```
   - **Edge first**: start with `edge` directly without probing installed browsers; use the user's browser instead if they name one.
   - If Edge fails (missing cookie database, or the error persists because Edge has no YouTube login), check which other browsers are installed and try `chrome`, `firefox`, `safari` in that order; a leftover browser folder without a profile database counts as not installed, and Safari needs Full Disk Access for the terminal app. Tell the user which browser was used; ask only when every browser fails.
   - `--cookies-from-browser` does not cache and re-decrypts the browser database on every call (possibly re-triggering the macOS Keychain prompt; tell the user to choose **Always Allow**), which is why the jar is saved once.
   - `cookies.txt` holds the login session: keep it only in the working directory outside the vault, never in the vault or a git repository, and delete it (or remind the user) at the end.

### Subtitle Acquisition (Three-Level Fallback)

**Priority 1: manual subtitles, then auto-generated**

```
yt-dlp --list-subs "<URL>"
yt-dlp --write-subs --sub-langs "<lang>" --convert-subs srt --skip-download -o "sub.%(ext)s" "<URL>"
# only when no manual track exists:
yt-dlp --write-auto-subs --sub-langs "<lang>" --convert-subs srt --skip-download -o "sub.%(ext)s" "<URL>"
```

- Choose `<lang>` to match the spoken language (e.g. `en`, `zh-Hans`); do not pick a machine-translated track when the original-language track exists.
- Auto-generated subtitles repeat text across overlapping cues ("rolling" captions). Deduplicate consecutive repeated text when reading, but keep timestamps for figure search.
- Correct recognition errors (names, model names, formulas) from context and on-screen text while writing; never copy them verbatim into the note.

**Priority 2: speech-to-text — ask first**

YouTube videos almost always have at least auto-generated captions; reaching this step is rare. Do **not** start transcription on your own. Stop and ask the user, stating why no usable subtitle track exists, and offering:

- transcribe the audio with the configured speech-to-text tool
- visual-only mode (Priority 3)
- stop here

Never install Whisper or any other speech-to-text tool. If a user-configured speech-to-text MCP tool is not available, say so and offer visual-only mode.

When the user agrees, extract mono 16 kHz audio (from the downloaded video if present, otherwise download audio only) and split it into chunks:

```
ffmpeg -v error -i video.mp4 -vn -ac 1 -ar 16000 audio.wav
mkdir -p stt && ffmpeg -v error -i audio.wav -f segment -segment_time 60 -c copy stt/chunk_%03d.wav
```

- Call `transcribe` once per chunk with `audio_file_path` = the chunk's **absolute** path, `audio_format` = `wav`, `language` = the spoken language (e.g. `en`, `zh`).
- The tool returns plain text, so rebuild timestamps from the chunk offsets: chunk `i` covers `[i*60, (i+1)*60)` seconds. Save the result as `stt.srt` (one cue per chunk, or per sentence spread evenly inside the chunk). Timestamps are therefore only accurate to the chunk; refine figure intervals from the frames. Use `-segment_time 30` when slides change quickly and finer timing matters.
- Correct recognition errors (names, model names, formulas) from context and on-screen text.

**Priority 3: visual-only mode**

Skip subtitles and rely on dense frame sampling. State this limitation in the note's info callout.

### Video and Cover Download

```
yt-dlp -f "bv*[height<=1080]+ba/b" --write-thumbnail --convert-thumbnails jpg -o "video.%(ext)s" "<URL>"
```

- YouTube thumbnails are often WebP; `--convert-thumbnails jpg` makes them embeddable everywhere. Prefer the highest-resolution thumbnail (`maxresdefault`).
- Rename the thumbnail to `cover.jpg` in the working directory; it is renamed again to a vault-unique name at publish time.
- 1080p is enough for frame extraction; use higher only when slides are too small to read.

### Read the Whole Transcript

Before outlining, read the entire subtitle file in a compact form, for example:

```
awk 'BEGIN{RS="";FS="\n"}{split($2,t," --> ");printf "[%s] %s\n",substr(t[1],1,8),$3}' sub.<lang>.srt
```

Use this `[hh:mm:ss] text` listing together with the chapter list to plan sections, locate figure intervals, and cite time ranges.

## Long Video Strategy

For longer videos, do not rely on a single monolithic pass.

- If the video is longer than 20 minutes, or the subtitle file contains more than 300 subtitle entries, split the work into smaller segments.
- Prefer chapter boundaries (from metadata or the description timeline) for splitting. If chapters are unavailable or too uneven, split by coherent time windows or subtitle ranges.
- Spawn subagents only when the user explicitly asks for sub-agents or parallel work; then process segments in parallel.
- Give each subagent a concrete segment boundary and require it to return: the segment's teaching goal, the core claims, important formulas or code, required figures with time provenance, and any ambiguities that need integration-time resolution.
- Keep a small overlap between neighboring segments when the explanation crosses boundaries, then deduplicate during integration.
- The main agent must integrate the segment outputs into one unified outline and one coherent final note, not a concatenation of chunk summaries.

## Teaching Content Rules

Build the notes from all of the following when available:

- video title and chapter structure
- the video's original cover image and key metadata
- on-screen diagrams, formulas, tables, plots, paper screenshots, and architecture slides
- subtitle explanations, examples, analogies, and verbal emphasis
- short high-signal original dialogue segments in interview, panel, podcast, or conversation videos, when the exact wording adds presence, humor, intuition, or unusually compact information
- code snippets shown or described in the talk

Skip content that does not contribute to the actual lesson:

- greetings and small talk
- routine back-and-forth that does not add information, tension, humor, intuition, or teaching value
- sponsorship and self-promotion
- channel logistics (subscribe, like, Patreon, merch, links in the description)
- closing pleasantries

Keep the speaker's closing discussion when it carries actual teaching value, such as synthesis, limitations, future work, tradeoffs, advice, or open questions (including questions the speaker poses to the audience).

## Writing Rules

1. Write the notes in Chinese unless the user explicitly requests another language. Keep established English terms (BatchNorm, Transformer) and give the Chinese name on first use.

2. Start from `assets/note-template.md`. Fill in the frontmatter and the info callout, then replace the body with the generated notes.

3. Structure:
   - one `#` title, then numbered sections `## 1 引言：…`, `## 2 …`, subsections `### 2.1 …`; follow the uploader's chapters when they reflect the teaching structure
   - end every major section with `### 本章小结`; add `### 拓展阅读` when there are one or two worthwhile external links
   - end the note with `## N 总结与延伸`
   - reconstruct the teaching flow; do not blindly mirror subtitle order
   - each section should answer, in order when applicable: what problem is being solved, why simpler views are insufficient, what the core idea is, how it works, and what the reader should retain

   Avoid overusing the "不是……而是……" sentence pattern. Do not use vague or overly abstract phrasing; ground claims in concrete mechanisms, examples, variables, steps, observed phenomena, timestamps, figures, or speaker-provided evidence.

4. Frontmatter (see the template): `title`, `aliases`, `tags`, `source` (canonical `watch?v=` URL without tracking or playlist parameters), `channel`, `published` (from `upload_date`), `duration`, `cover` (`"[[<cover file>]]"`), `created`, and `cssclasses: [figure-center]`. Do not add `updated`; vault plugins may add it automatically.

5. Put the cover right under the title (`![[<cover file>|500]]`), followed by an `> [!abstract] 视频信息` callout (channel, date, duration, link, processing scope/limitations, subtitle source) and a `> [!tip] 时间戳` callout telling the reader that figure timestamps are clickable.

6. Map the teaching signals of the PDF skill to Obsidian callouts, and use them deliberately and repeatedly when the content justifies it:

   | PDF box | Obsidian callout | Use for |
   |---|---|---|
   | `importantbox` | `> [!important] 标题` | core concepts, definitions, central claims, key mechanism summaries, compact restatements after dense explanations |
   | `knowledgebox` | `> [!info] 标题` | background, prerequisite reminders, history, engineering context, terminology comparisons |
   | `warningbox` | `> [!warning] 标题` | misunderstandings, hidden assumptions, causal confusions, easy implementation mistakes |
   | `dialoguebox` | `> [!quote] 原始对话片段（hh:mm:ss–hh:mm:ss）` | short high-signal dialogue in conversation videos, with speaker labels; give the Chinese meaning after short English quotes |

   - Knowledge that is **not in the video** (your own supplements or corrections) goes in `> [!info] 补充：…` so it stays distinguishable from the speaker's content.
   - Attribute the speaker's personal analogies and opinions to the speaker ("讲者认为…"), and correct or qualify them in a callout when they are imprecise.
   - Each callout carries a specific payload; routine exposition stays in normal prose.

7. Formulas:
   - first explain in plain Chinese what the formula expresses and why it appears
   - show it as display math with `$$` on their own lines
   - immediately follow with a flat list explaining every symbol
   - use inline `$...$` for symbols in prose
   - never put `|` or `\|` inside a Markdown table cell (it splits the column); use `\Vert` or move the math out of the table

8. Code: explain the role before a fenced block with a language tag, and summarize expected behavior after it when useful.

9. Cross references: refer to figures as "图 N" in prose; link to other sections of the same note with `[[#<exact heading text>|第 N 节]]` (the heading text must match exactly, including its number).

10. Diagrams you draw yourself: use a `mermaid` code block (quote labels, use `<br/>` for line breaks inside nodes). For data plots, generate an image with a script (matplotlib → SVG or PNG) into the figures directory and embed it like any other figure.

11. The final section `总结与延伸` must include:
    - the speaker's substantive closing discussion, excluding sign-off language and channel logistics
    - your structured distillation of the core claims, mechanisms, and practical implications (a comparison table works well when the video covers several methods)
    - your expanded synthesis: conceptual compression, cross-links between sections, careful generalization faithful to the video
    - concrete takeaways, open questions, or next steps when the material supports them

12. Do not emit `[cite]`-style placeholders anywhere.

## Figure Handling

Select figures by necessity and teaching value, not by an arbitrary quota or a bias toward keeping the note visually sparse.

Frame understanding must come from direct visual inspection: open candidate frames and contact sheets with the image-reading tool before deciding what they show. Do not use OCR as a substitute, and do not infer a frame's content from subtitles, filenames, or timestamps alone.

### Two-Pass Recall

Bias strongly toward recall before precision.

**Pass 1 — overview.** Sample the whole video and tile it into labeled contact sheets:

```
ffmpeg -v error -i video.mp4 -vf "fps=1/3,scale=480:-1" frames/c_%04d.jpg
```

Then build 6×5 montages (30 frames ≈ 90 s per sheet) with a timestamp label on each tile. For long lectures raise the interval (e.g. `fps=1/10`) and use chapters to decide where to sample densely. Use this overview to map which time ranges show which slides.

**Pass 2 — candidate windows.** For every figure you plan to use, extract full-resolution frames at 1-second steps across its subtitle-aligned interval and tile them (4 columns, labeled):

```
ffmpeg -v error -y -ss <t> -i video.mp4 -frames:v 1 -q:v 2 cand/<key>_<t>.jpg
magick montage <label/file pairs> -font <font file> -pointsize 22 -tile 4x -geometry 480x270+4+4 sheets/cand_<key>.jpg
```

Practical notes:

- Put `-ss` before `-i` for fast seeking.
- On macOS, `magick montage -label` fails with `unable to read font` unless a font file is given explicitly, e.g. `-font /System/Library/Fonts/Helvetica.ttc`. Without labels, tiles are row-major: tile index × sampling interval = time.
- Write loops that use arrays or associative arrays as a `bash` script file; the default macOS shell is zsh and `declare -A` / `${!arr[@]}` fail there with `bad substitution`.

### Frame Selection Checklist

Before inserting any video frame, inspect several nearby candidates from the same subtitle-aligned interval and apply this checklist. If any item fails, keep searching nearby rather than forcing an approximate match.

- Relevance: the frame directly supports the exact concept discussed in the surrounding paragraph.
- Required content visible: every visual element referenced in the text is already visible.
- Fully revealed state: for progressive slides, animations, whiteboards, or highlights, use the final fully populated readable state.
- Unobstructed: prefer the second where the presenter's pointer, laser dot, annotation pen, or a webcam overlay does not cover formulas, labels, or table cells. Burned-in captions and small overlays are acceptable when they do not hide key content.
- Not a transition: reject frames caught mid-fade, mid-zoom, or blurred.
- Best nearby candidate: prefer the most complete and most readable frame.
- Readability: text, formulas, labels, and diagram structure are legible.

Skip talking-head frames, intros, and end screens unless they carry teaching content.

### Frame Naming and Cropping

- Keep neutral timestamp names (`<key>_<seconds>.jpg`) for candidates. Assign a semantic name only after visually confirming the content, e.g. `attention_score_matrix.jpg`.
- Semantic names must describe what is visible, use lowercase ASCII with underscores, and be specific enough to be unique across the whole vault (Obsidian resolves `![[name.jpg]]` by file name).
- Crop when the useful region is small or surrounded by empty space, a webcam inset, or leftovers of other slides: `magick in.jpg -crop WxH+X+Y +repage out.jpg`. Always view the crop afterwards; adjust until no partial text from neighboring elements remains.
- Include every figure that is necessary to explain the content well; several figures in one section are fine when an idea builds in stages. Omit repetitive or low-information frames.

## Figure Captions and Time Provenance

Obsidian does **not** display image alt text, so a caption written only inside `![...](...)` is invisible. Every figure is therefore two consecutive lines — the embed, then an italic caption line with a clickable time range — with **no blank line between them**:

```markdown
![[attention_score_matrix.jpg|600]]
*图 4：注意力分数矩阵的完整展开。[00:12:31–00:12:46](https://www.youtube.com/watch?v=VIDEO_ID&t=751s)*
```

- Number figures sequentially (`图 1`, `图 2`, …) and refer to them by number in prose.
- The time range comes from the subtitle-aligned interval used to locate the figure (format `HH:MM:SS–HH:MM:SS`, en dash), not a vague chapter estimate. Crops keep the source frame's interval.
- The link target is `https://www.youtube.com/watch?v=<ID>&t=<start seconds>s`.
- Width: `|500`–`|650` for most slides, omit the width for dense full-width grids or tables, `|500` for the cover.
- Figures and captions stay outside callouts and outside tables.
- Keeping the caption directly under the embed is what lets `assets/figure-center.css` center both the image and its caption (together with `cssclasses: figure-center` in the frontmatter).

## Visualization

For concepts that remain hard to explain with only screenshots and prose, add accurate visualizations:

- process flows, evolution lines, pipelines, and architecture overviews → Mermaid
- curves and charts (scaling laws, training curves, benchmark results, ablations), distributions, heatmaps, geometric intuition → a script-generated SVG/PNG embedded as a figure
- summary tables that compress several methods into one comparison → a Markdown table

Do not add decorative graphics that do not teach anything.

## Publishing to the Vault

Publish with `scripts/publish_note.py` (standard library only). Run it with the vault's Python environment, variable first and project venv as fallback, from the vault root:

```
"${VTO_PYTHON:-.venv/bin/python}" <skill dir>/scripts/publish_note.py \
  --note <workdir>/note.md --figures-dir <workdir>/figures \
  --title "<中文标题>" --assets-subdir "<短主题名>" --cover cover.jpg \
  --install-css <skill dir>/assets/figure-center.css --open
```

What the script does, and why each step exists:

1. **Preflight**: probes the Obsidian CLI with a tiny `eval` and a timeout. The CLI can hang without output when it is not connected to the app (or is blocked by a sandbox); the script stops with a clear message instead of hanging.
2. **Refuses to overwrite**: stops if `<inbox>/<title>.md` already exists.
3. **Attachments**: collects every `![[...]]` embed in the draft, renames the cover to `<assets-subdir>_cover.<ext>` (and rewrites the draft's references), checks that no other file in the vault has the same name, and copies the images into `<assets-root>/<assets-subdir>/`.
4. **Writes the note through the CLI** with `eval` + base64 (`app.vault.create(...)`). Do **not** use `obsidian create content=...` for notes: the CLI interprets `\t` and `\n` inside `content`, which silently corrupts LaTeX such as `\to`, `\top`, `\nabla`, `\text`, and long contents can get a UTF-8 character split at a buffer boundary.
5. **Waits for the file on disk** rather than for CLI output (async `eval` calls may never return).
6. **Verifies**: the note body must be byte-identical to the draft except for frontmatter keys that vault plugins add on save (`updated`, `modified`); no `U+FFFD`; every embed resolves to a copied file.
7. **CSS** (with `--install-css`): installs `figure-center.css` into `.obsidian/snippets/` if missing and enables it; reports if a different version already exists instead of overwriting it.
8. **Opens** the note in Obsidian (with `--open`).

Use `--dry-run` to see the plan without touching the vault. If the vault forbids direct writes and the CLI is unavailable, stop and ask the user; do not write the file directly on your own.

`assets/figure-center.css` also resets `text-indent` on the figure and caption lines, because a common "first-line indent" snippet (`div.cm-line { text-indent: 2em }`) would otherwise push centered captions off-center in Live Preview.

## Final Checklist

Before delivery, verify all of the following:

- no important teaching content has been dropped, and no concrete but critical detail (numbers, names, years, results) has been lost during restructuring
- subtitle recognition errors were corrected and none leaked into the note
- the text and figures are aligned: each frame supports the surrounding explanation, necessary crops were applied, and each chosen frame is the fullest, unobstructed state rather than a transitional one
- every video-derived figure has a visible caption line with a clickable time range, and figure numbers are sequential
- the note is visually rich enough for teaching: check whether more key frames, a Mermaid diagram, or a comparison table would improve clarity
- your own supplements are marked as `补充` and separated from the speaker's claims
- all `$$` blocks and inline math render (no `\label`, `\ref`, or LaTeX-only environments), and no table cell contains `|` inside math
- the publish script reported success for attachments, write, and verification
- if cookies were used, `cookies.txt` exists only in the working directory, never in the vault

Optionally, when the user asks for a thorough pass, have an independent reviewer compare the note against the full subtitle file and report omissions only (no edits), then fill the gaps; repeat until the reviewer finds nothing important missing.

## Delivery

Deliver all of the following:

- the note in the vault inbox, opened in Obsidian
- the cover and all selected/cropped/generated images in `<assets-root>/<assets-subdir>/`
- the transcription `stt.srt` in the working directory, if speech-to-text transcription was used
- a short report: note path, attachment folder, verification result, figures count, the subtitle source used, any limitations (visual-only mode, auto-generated subtitles), and which intermediate files in the working directory can be deleted — list `cookies.txt` first if it was created, since it holds the login session

## Assets and Scripts

- `assets/note-template.md`: default note skeleton (frontmatter, cover, info callouts, figure and caption pattern)
- `assets/figure-center.css`: CSS snippet that centers figures and their caption lines in notes with `cssclasses: figure-center`
- `scripts/publish_note.py`: publishes the draft note and its images into the vault through the Obsidian CLI and verifies the result
