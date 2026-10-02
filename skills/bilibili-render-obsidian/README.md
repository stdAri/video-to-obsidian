<p align="center"><img src="assets/icon.png" width="128" alt="icon"></p>

<h1 align="center">Bilibili Render Obsidian</h1>

<p align="center">
  <b>One skill to turn any Bilibili lecture into a professional, figure-rich Obsidian note.</b><br>
  一个把 B 站课程视频变成专业图文 Obsidian 笔记的 Claude Code Skill
</p>

<p align="center">
  Subtitles · Key Frames · Formulas · Clickable Timestamps · One-Click Publish<br>
  字幕提取 · 关键帧截图 · 公式排版 · 可点击时间戳 · 一键入库
</p>

<p align="center">
  <!-- 徽章占位：按需替换为真实 badge 链接 -->
  <img alt="platform" src="https://img.shields.io/badge/platform-Claude%20Code-blueviolet">
  <img alt="output" src="https://img.shields.io/badge/output-Obsidian%20Markdown-7C3AED">
  <img alt="lang" src="https://img.shields.io/badge/notes-%E4%B8%AD%E6%96%87-red">
</p>

<p align="center">
  <a href="#english">English</a> | <a href="#中文">中文</a>
</p>

---

<a id="中文"></a>

## 中文

把 B 站视频链接丢给 Claude，得到一篇**不比人工讲义薄**的 Obsidian 笔记：封面、信息卡、编号章节、公式、Mermaid 图、逐张人工目检挑选的关键帧——每张截图带可见图注和**可点击的时间戳**，点一下跳回 B 站对应位置。写完自动通过 Obsidian CLI 入库并逐字节校验。

### 特性

- **四级字幕回退**：B 站登录态 AI 字幕（`ai-zh`）→ 搬运视频的 YouTube 原片字幕 → 本地语音转写（需用户同意）→ 纯画面模式。AI 字幕的同音错别字按画面文字校对，绝不照抄
- **两阶段选帧**：全片低速采样拼总览图 → 候选窗口逐秒全分辨率抽取 → 每张图都经视觉确认（非 OCR、非时间戳猜测），剔除过渡帧、遮挡帧、半拉开的动画页
- **教学法写作**：动机 → 直觉 → 机制 → 例子 → 要点，不按字幕时间顺序流水账；重点概念用 Obsidian callout 标出，视频之外的补充单独标注
- **完整的时间溯源**：图注格式 `*图 N：……。[HH:MM:SS–HH:MM:SS](视频链接?t=秒)*`，全部可点击
- **安全发布**：只经 Obsidian CLI 写库（eval + base64，避开转义损坏和 UTF-8 劈字符），发布前预检、拒绝覆写、写后逐字节校验、嵌入图片逐一核对
- **配套样式**：`figure-center.css` 让图片与斜体图注在两种视图下居中（斜体门控，不误伤普通段落）

### 使用方法

在 Claude Code 里直接发 B 站链接：

```
https://www.bilibili.com/video/BV1xxxxxxx 把这个视频总结一下放到 inbox
```

支持 `bilibili.com/video/BV…` 和 `b23.tv` 短链；分 P 视频会先列出分 P 并询问处理范围。笔记默认落在库的收件箱目录，图片附件在库的附件目录（可在库规则里改）。

### 依赖

| 工具 | 用途 |
|---|---|
| `yt-dlp` | 元数据、字幕、视频与封面下载 |
| `ffmpeg` | 抽帧 |
| ImageMagick (`magick`) | 拼接候选图、裁剪 |
| `jq` | 元数据摘要 |
| Obsidian 桌面端 + CLI | 笔记入库的唯一通道 |
| 本地 STT 工具（可选） | 无字幕时的语音转写 |

首次运行会从 **Edge** 浏览器读取一次 B 站登录 cookie（macOS 可能弹钥匙串授权，选"始终允许"），存为工作目录下的 `cookies.txt` 复用；该文件含登录令牌，只留在库外工作目录，绝不进库、不进 git。

### 输出规格

- 中文正文，编号章节 `## 1 …`，每节末 `### 本章小结`，全文末 `## N 总结与延伸`（含作者收尾、对比表、提炼与拓展阅读）
- 图片宽度统一 `|600`（封面 `|500`，dense 全宽大图省略宽度）
- 长视频（>20 分钟或字幕 >300 条）按章节边界分段处理再整合

### 目录结构

```
bilibili-render-obsidian/
├── SKILL.md                  # 主流程：获取、选帧、写作、发布规范
├── README.md                 # 本文件
├── assets/
│   ├── note-template.md      # 笔记骨架（frontmatter、callout、图注格式）
│   └── figure-center.css     # 图片+图注居中片段（斜体门控）
└── scripts/
    └── publish_note.py       # 入库发布与校验（仅标准库）
```

---

<a id="english"></a>

## English

Drop a Bilibili URL on Claude and get back an Obsidian note that is **no thinner than a hand-written lecture note**: cover image, info callout, numbered sections, display math, Mermaid diagrams, and key frames individually verified by eye — each with a visible caption and a **clickable timestamp** that jumps back to the exact moment in the video. The finished note is published into your vault through the Obsidian CLI and verified byte-for-byte.

### Features

- **Four-level subtitle fallback**: logged-in Bilibili AI subtitles (`ai-zh`) → original-video subtitles for re-uploads (e.g. YouTube) → local speech-to-text (only with your approval) → visual-only mode. Homophone errors in AI subtitles are corrected against on-screen text, never copied verbatim
- **Two-pass frame recall**: low-rate sampling of the whole video into labeled contact sheets → 1-second full-resolution candidates per figure window → every frame confirmed by direct visual inspection (no OCR, no timestamp guessing); transitional, obstructed, or half-revealed frames are rejected
- **Pedagogical writing**: motivation → intuition → mechanism → example → takeaway, never a chronological subtitle dump; core concepts go into Obsidian callouts, supplements not from the video are marked as such
- **Full time provenance**: captions read `*Fig. N: … [HH:MM:SS–HH:MM:SS](video?t=seconds)*`, all clickable
- **Safe publishing**: writes only through the Obsidian CLI (eval + base64, avoiding escape corruption and UTF-8 boundary splits), with preflight checks, overwrite refusal, byte-identical verification, and per-embed resolution checks
- **Companion styling**: `figure-center.css` centers figures and their *italic* captions in both Reading view and Live Preview (italic-gated, so plain paragraphs after an image are not mis-centered)

### Usage

Just paste a Bilibili link in Claude Code:

```
https://www.bilibili.com/video/BV1xxxxxxx summarize this video into my inbox
```

Both `bilibili.com/video/BV…` and `b23.tv` short links are supported; multi-part (分P) videos are listed first so you can pick the parts. Notes land in the vault's inbox folder by default, attachments in its attachment folder (configurable via vault rules).

### Requirements

| Tool | Purpose |
|---|---|
| `yt-dlp` | metadata, subtitles, video and cover download |
| `ffmpeg` | frame extraction |
| ImageMagick (`magick`) | contact sheets, cropping |
| `jq` | metadata summaries |
| Obsidian desktop + CLI | the only write path into the vault |
| local STT tool (optional) | speech-to-text when no subtitles exist |

On first run, Bilibili login cookies are read once from **Edge** (macOS may show a Keychain prompt — choose "Always Allow") and cached as `cookies.txt` in the working directory. This file holds your login token: it stays outside the vault, never enters git.

### Output Specification

- Chinese prose, numbered sections (`## 1 …`), each ending with `### 本章小结`, and a final `## N 总结与延伸` (speaker's closing discussion, comparison tables, distilled takeaways, further reading)
- Uniform figure width `|600` (cover `|500`; dense full-width grids keep natural width)
- Long videos (>20 min or >300 subtitle cues) are processed in chapter-aligned segments and integrated into one coherent note

### Repository Layout

```
bilibili-render-obsidian/
├── SKILL.md                  # main pipeline: acquisition, frame selection, writing, publishing rules
├── README.md                 # this file
├── assets/
│   ├── note-template.md      # note skeleton (frontmatter, callouts, caption format)
│   └── figure-center.css     # figure + caption centering snippet (italic-gated)
└── scripts/
    └── publish_note.py       # vault publishing & verification (standard library only)
```
