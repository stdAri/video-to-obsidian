#!/usr/bin/env python3
"""Publish a draft Obsidian note and its images into a vault through the Obsidian CLI.

Why this script exists (lessons from real runs):
  - `obsidian create content=...` interprets `\\t` and `\\n` inside the content, which
    corrupts LaTeX such as `\\to`, `\\top`, `\\nabla`; long contents can also get a UTF-8
    character split at a buffer boundary. The note is therefore written with
    `obsidian eval` + base64 + `app.vault.create`.
  - The CLI can hang without output (not connected to the app, sandboxed, or an async
    eval that never resolves). Every call has a timeout, and success is judged by the
    file appearing on disk, not by CLI output or exit code.
  - Obsidian resolves `![[name.jpg]]` by file name, so attachment names must be unique
    across the vault; a generic `cover.jpg` is renamed to `<assets-subdir>_cover.jpg`.
  - Vault plugins may add frontmatter keys on save (e.g. `updated`); verification
    ignores those and requires the rest to be byte-identical.

Usage (run from the vault root with the vault's Python):
  publish_note.py --note WORK/note.md --figures-dir WORK/figures --title "中文标题" \\
      --assets-subdir "短主题名" --cover WORK/cover.jpg \\
      [--install-css SKILL/assets/figure-center.css] [--open] [--dry-run]

Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import filecmp
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

EMBED_RE = re.compile(r"!\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
PLUGIN_KEYS_RE = re.compile(r"^(updated|modified)\s*:")
FORBIDDEN_TITLE_CHARS = set('\\/:*?"<>|#^[]')
OBSIDIAN_JSON = Path.home() / "Library/Application Support/obsidian/obsidian.json"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(msg, flush=True)


def resolve_vault(arg: str | None) -> Path:
    if arg:
        vault = Path(arg).expanduser().resolve()
        if not (vault / ".obsidian").is_dir():
            die(f"{vault} is not an Obsidian vault (no .obsidian folder)")
        return vault
    if not OBSIDIAN_JSON.is_file():
        die("cannot find obsidian.json; pass --vault")
    vaults = json.loads(OBSIDIAN_JSON.read_text()).get("vaults", {})
    opened = [v["path"] for v in vaults.values() if v.get("open")]
    if len(opened) != 1:
        die(f"expected exactly one open vault, found {opened or 'none'}; pass --vault")
    return Path(opened[0])


def run_cli(args: list[str], timeout: float) -> tuple[bool, str]:
    """Run the Obsidian CLI. Returns (finished_in_time, combined output)."""
    try:
        proc = subprocess.run(
            ["obsidian", *args], capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        die("the `obsidian` CLI is not on PATH")
    except subprocess.TimeoutExpired:
        return False, ""
    # The CLI may exit non-zero even on success; callers inspect the output instead.
    return True, (proc.stdout + proc.stderr).strip()


def preflight(vault: Path, timeout: float) -> None:
    done, out = run_cli(["eval", "code=app.vault.getName()"], timeout)
    if not done:
        die(
            "the Obsidian CLI did not respond. Make sure the Obsidian app is running with "
            "the CLI enabled (restart Obsidian if needed); if this runs in a sandbox, "
            "retry outside it. Do not write vault files directly instead."
        )
    if "=>" not in out:
        die(f"unexpected CLI output: {out!r}")
    name = out.split("=>", 1)[1].strip()
    if name != vault.name:
        die(f"the CLI is connected to vault {name!r}, not {vault.name!r}; switch vaults first")


def index_vault(vault: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in vault.rglob("*"):
        rel = path.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts) or not path.is_file():
            continue
        index.setdefault(path.name, []).append(path)
    return index


def strip_plugin_keys(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    front = [ln for ln in text[4:end].split("\n") if not PLUGIN_KEYS_RE.match(ln)]
    return "---\n" + "\n".join(front) + text[end:]


def first_difference(a: str, b: str) -> str:
    for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1):
        if x != y:
            return f"line {i}: expected {x!r}, got {y!r}"
    return "length differs"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--note", required=True, type=Path, help="draft note (Markdown)")
    ap.add_argument("--figures-dir", required=True, type=Path, help="directory holding the embedded images")
    ap.add_argument("--title", required=True, help="note file name without .md")
    ap.add_argument("--assets-subdir", required=True, help="subfolder under the assets root")
    ap.add_argument("--cover", type=Path, help="cover image; renamed to <assets-subdir>_cover.<ext>")
    ap.add_argument("--vault", help="vault path (default: the open vault)")
    ap.add_argument("--inbox", default="Inbox", help="note folder inside the vault")
    ap.add_argument("--assets-root", default="attachments", help="attachment root inside the vault")
    ap.add_argument("--install-css", type=Path, help="CSS snippet to install and enable")
    ap.add_argument("--open", action="store_true", help="open the note in Obsidian afterwards")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and change nothing")
    ap.add_argument("--timeout", type=float, default=20.0, help="seconds to wait for each CLI step")
    args = ap.parse_args()

    if FORBIDDEN_TITLE_CHARS & set(args.title):
        die(f"title contains characters Obsidian links cannot handle: {''.join(sorted(FORBIDDEN_TITLE_CHARS & set(args.title)))}")
    if not args.note.is_file():
        die(f"draft not found: {args.note}")

    vault = resolve_vault(args.vault)
    inbox_dir = vault / args.inbox
    assets_dir = vault / args.assets_root / args.assets_subdir
    note_rel = f"{args.inbox}/{args.title}.md"
    note_path = vault / note_rel
    if not inbox_dir.is_dir():
        die(f"inbox folder does not exist: {inbox_dir}")
    if note_path.exists():
        die(f"note already exists, refusing to overwrite: {note_path}")

    text = args.note.read_text(encoding="utf-8")

    # Cover: give it a vault-unique name and rewrite references in the draft.
    sources: dict[str, Path] = {}
    if args.cover:
        if not args.cover.is_file():
            die(f"cover not found: {args.cover}")
        cover_name = f"{args.assets_subdir}_cover{args.cover.suffix.lower()}"
        text = text.replace(f"[[{args.cover.name}", f"[[{cover_name}")
        sources[cover_name] = args.cover

    embeds = list(dict.fromkeys(m.group(1).strip() for m in EMBED_RE.finditer(text)))
    if not embeds:
        die("the draft has no ![[...]] embeds; nothing to publish as attachments")
    for name in embeds:
        if name not in sources:
            sources[name] = args.figures_dir / name
    missing = [n for n in embeds if not sources[n].is_file()]
    if missing:
        die(f"embedded files not found: {missing}")

    index = index_vault(vault)
    to_copy: list[str] = []
    for name in embeds:
        clashes = [p for p in index.get(name, []) if p.parent != assets_dir]
        if clashes:
            die(f"{name!r} already exists elsewhere in the vault: {[str(p.relative_to(vault)) for p in clashes]}; rename the figure")
        target = assets_dir / name
        if target.exists():
            if not filecmp.cmp(target, sources[name], shallow=False):
                die(f"{target.relative_to(vault)} exists with different content")
            continue
        to_copy.append(name)

    info(f"vault:        {vault}")
    info(f"note:         {note_rel}")
    info(f"attachments:  {assets_dir.relative_to(vault)}/ ({len(embeds)} embeds, {len(to_copy)} to copy)")
    if args.dry_run:
        info("dry run: nothing changed")
        return

    preflight(vault, args.timeout)

    assets_dir.mkdir(parents=True, exist_ok=True)
    for name in to_copy:
        shutil.copy2(sources[name], assets_dir / name)

    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    code = (
        f"app.vault.create({json.dumps(note_rel)}, new TextDecoder().decode("
        f"Uint8Array.from(atob('{payload}'), c => c.charCodeAt(0)))).then(f => 'created ' + f.path)"
    )
    run_cli(["eval", f"code={code}"], args.timeout)  # may never return; judge by the file

    deadline = time.time() + args.timeout
    while not note_path.exists() and time.time() < deadline:
        time.sleep(0.5)
    if not note_path.exists():
        die(f"the note did not appear on disk within {args.timeout}s: {note_path}")
    time.sleep(1.0)  # let plugins finish their on-save frontmatter edits

    written = note_path.read_text(encoding="utf-8")
    if "�" in written:
        die("the written note contains U+FFFD (a broken UTF-8 character)")
    if strip_plugin_keys(written) != strip_plugin_keys(text):
        die(f"the written note differs from the draft ({first_difference(text, written)})")
    unresolved = [n for n in embeds if not (assets_dir / n).is_file()]
    if unresolved:
        die(f"embeds without a file in {assets_dir}: {unresolved}")
    info("verified:     note content identical to the draft (ignoring plugin-added keys); all embeds resolve")

    if args.install_css:
        css = args.install_css
        snippets = vault / ".obsidian" / "snippets"
        snippets.mkdir(parents=True, exist_ok=True)
        target = snippets / css.name
        if target.exists() and not filecmp.cmp(target, css, shallow=False):
            info(f"css:          {target.name} already exists with different content; left unchanged")
        else:
            if not target.exists():
                shutil.copy2(css, target)
            done, out = run_cli(
                ["eval", f"code=app.customCss.setCssEnabledStatus({json.dumps(css.stem)}, true); "
                         f"String(app.customCss.enabledSnippets.has({json.dumps(css.stem)}))"],
                args.timeout,
            )
            state = "enabled" if done and "true" in out else "installed (enable it in Settings > Appearance > CSS snippets)"
            info(f"css:          {target.name} {state}")

    if args.open:
        run_cli(["open", f"path={note_rel}"], args.timeout)
        info("opened in Obsidian")


if __name__ == "__main__":
    main()
