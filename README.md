<div align="center">

# video-to-obsidian

<img src="skills/bilibili-render-obsidian/assets/icon.png" alt="icon" width="160" />

**Turn video lectures into professional, figure-rich Obsidian notes — in one message.**
**把视频讲座变成专业图文 Obsidian 笔记，一条消息的事。**

Subtitles · Key Frames · Formulas · Clickable Timestamps · One-Click Publish
字幕提取 · 关键帧截图 · 公式排版 · 可点击时间戳 · 一键入库

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Claude%20Code-blueviolet)](#-quick-start--快速开始)
[![Skills](https://img.shields.io/badge/Skills-2-orange)](#-skills--一览)
[![Notes](https://img.shields.io/badge/Notes-%E4%B8%AD%E6%96%87-red)](#-features--特性)
[![Stars](https://img.shields.io/github/stars/stdAri/video-to-obsidian?style=flat&logo=github&color=gold)](https://github.com/stdAri/video-to-obsidian/stargazers)

[English](#english) · [中文](#中文) · [Quick Start](#-quick-start--快速开始) · [Skills](#-skills--一览)

</div>

---

🌱 *These are Claude Code **skills**, not a platform — drop them into your own `.claude/skills/` and they work with your vault, your rules.*
🌱 *这不是一个平台，而是两个 Claude Code **skill**——拷进你自己的 `.claude/skills/` 即可，用的是你的库、你的规则。*

<a id="中文"></a>

## ✨ 特性

- 🎬 **丢链接就出笔记**：B 站 / YouTube 链接发给 Claude，得到一篇不比人工讲义薄的 Obsidian 笔记——封面、信息卡、编号章节、公式、Mermaid 图、逐张人工目检的关键帧
- 📝 **四级字幕回退**：登录态 AI 字幕 → 搬运视频的原片字幕 → 语音转写（须经你同意）→ 纯画面模式；AI 字幕的同音错别字按画面文字校对，绝不照抄
- 🖼️ **两阶段选帧**：全片低速采样拼总览 → 候选窗口逐秒全分辨率抽取 → 每帧直接视觉确认（非 OCR、非时间戳猜测），剔除过渡帧、遮挡帧、没拉完的动画页
- ⏱️ **时间戳可点击**：每张截图下的斜体图注带时间区间，点一下跳回视频对应秒数
- 🎓 **教学法写作**：动机 → 直觉 → 机制 → 例子 → 要点，不按字幕顺序流水账；核心概念进 callout，视频之外的补充单独标注
- 🔒 **安全发布**：只经 Obsidian CLI 写库（eval + base64，避开转义损坏与 UTF-8 劈字符），发布前预检、拒绝覆写、写后逐字节校验
- 🎨 **配套居中样式**：`figure-center.css` 让图片与斜体图注在两种视图下居中（斜体门控，不误伤普通段落）

## 📦 Skills 一览

| Skill | 平台 | 说明 |
|-------|------|------|
| [`bilibili-render-obsidian`](skills/bilibili-render-obsidian/) | Bilibili (B站) | 登录后的 AI 字幕（`ai-zh`）优先；搬运视频取原片字幕；支持分 P、简介时间轴解析 |
| [`youtube-render-obsidian`](skills/youtube-render-obsidian/) | YouTube | 人工字幕优先、自动字幕兜底；以视频章节为大纲 |

两个 skill 共享同一套写作规则、选帧流程与 Obsidian 输出格式，只有素材获取阶段有平台差异。各自目录下有独立的详细 README。

## 🚀 Quick Start · 快速开始

1. **安装 skill**（二选一或都装）：

   ```sh
   git clone https://github.com/stdAri/video-to-obsidian.git
   cp -r video-to-obsidian/skills/bilibili-render-obsidian <你的vault>/.claude/skills/
   cp -r video-to-obsidian/skills/youtube-render-obsidian  <你的vault>/.claude/skills/
   ```

2. **装依赖**：`yt-dlp`、`ffmpeg`、ImageMagick、`jq`，以及运行中的 Obsidian 桌面端 + 其 CLI。

   ```sh
   brew install yt-dlp ffmpeg imagemagick jq
   ```

3. **发链接**：在 Claude Code 里直接说——

   ```
   https://www.bilibili.com/video/BV1xxxxxxx 把这个视频总结一下放到 inbox
   ```

   笔记落在库的**收件箱目录**，图片附件在库的**附件目录**（具体位置按各库自己的规则解析）。

> 💡 首次运行会从 **Edge** 读一次视频站登录 cookie（macOS 可能弹钥匙串授权，选「始终允许」），缓存为工作目录下的 `cookies.txt` 复用；它含登录令牌，只留在库外、绝不进 vault、不进 git。

## 📖 与 PDF 版的关系

本仓库以 [wdkns-skills](https://github.com/wdkns/wdkns-skills) 的 `bilibili-render-pdf` / `youtube-render-pdf` 为蓝本：素材获取、选帧规范与教学写作标准保持一致，交付物从 `.tex` + PDF 换成 Obsidian 笔记，并按实际跑通的经验补充了细则。

| 方面 | PDF 版 | 本仓库 |
|------|--------|--------|
| 交付物 | `.tex` + 编译后的 PDF | 收件箱 `<标题>.md` + 附件目录中的图片 |
| 重点框 | `importantbox` / `knowledgebox` / `warningbox` | `[!important]` / `[!info]` / `[!warning]` callout |
| 图片出处 | 同页脚注写时间区间 | 图下**可见**斜体图注，时间区间可点击跳回视频 |

## 🧩 项目结构

```
video-to-obsidian/
├── skills/
│   ├── bilibili-render-obsidian/   # B 站 skill（含独立详细 README）
│   │   ├── SKILL.md                # 主流程：获取、选帧、写作、发布规范
│   │   ├── assets/                 # 笔记模板、居中 CSS、图标
│   │   └── scripts/publish_note.py # 入库发布与校验（仅标准库）
│   └── youtube-render-obsidian/    # YouTube skill（同构）
├── README.md
└── LICENSE                         # GPL-3.0
```

## ❓ FAQ

**Q：笔记为什么是中文的？**
A：写作规范就是面向中文讲义设计的；保留 Transformer 这类通用英文术语。想要其他语言，改 SKILL.md 的写作规则即可。

**Q：没有字幕的视频怎么办？**
A：skill 会停下来问你：用本地语音转写、走纯画面模式、还是放弃。绝不会背着你装 Whisper。

**Q：会覆盖我库里已有的笔记吗？**
A：不会。发布脚本发现同名笔记会直接拒绝；写入只走 Obsidian CLI，写后逐字节校验。

## 📜 License

GNU GPL-3.0，详见 [LICENSE](LICENSE)。

---

<a id="english"></a>

## ✨ Features

- 🎬 **Link in, note out**: paste a Bilibili / YouTube URL and get an Obsidian note no thinner than a hand-written lecture note — cover, info callout, numbered sections, display math, Mermaid diagrams, and eye-verified key frames
- 📝 **Four-level subtitle fallback**: logged-in AI subtitles → original-video subtitles for re-uploads → speech-to-text (only with your approval) → visual-only mode; homophone errors corrected against on-screen text, never copied verbatim
- 🖼️ **Two-pass frame recall**: whole-video contact sheets → 1-second full-res candidates per figure window → every frame confirmed by direct visual inspection; transitional and obstructed frames rejected
- ⏱️ **Clickable timestamps**: every caption carries its time range and jumps back to that exact second in the video
- 🎓 **Pedagogical writing**: motivation → intuition → mechanism → example → takeaway — never a chronological subtitle dump; supplements not from the video are marked as such
- 🔒 **Safe publishing**: writes only through the Obsidian CLI (eval + base64), with preflight checks, overwrite refusal, and byte-identical verification
- 🎨 **Centering snippet included**: `figure-center.css` centers figures and their *italic* captions in both views (italic-gated)

## 🚀 Quick Start

```sh
git clone https://github.com/stdAri/video-to-obsidian.git
cp -r video-to-obsidian/skills/bilibili-render-obsidian <your-vault>/.claude/skills/
brew install yt-dlp ffmpeg imagemagick jq   # plus Obsidian desktop + its CLI
```

Then paste a video URL in Claude Code. The note lands in the vault's inbox folder and attachments in its attachment folder, both resolved from the vault's own rules. Login cookies are read once from Edge and cached as `cookies.txt` outside the vault — it never enters the vault or git.

See each skill's own README for the full pipeline details: [bilibili](skills/bilibili-render-obsidian/) · [youtube](skills/youtube-render-obsidian/).

## 📜 License

GNU GPL-3.0 — see [LICENSE](LICENSE).

---

<div align="center">
<i>If these skills save you an afternoon, a ⭐ goes a long way.</i>
</div>
