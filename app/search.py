import json
import os
from pathlib import Path
from typing import Dict, List

from . import wiki_fs


def _load_index() -> List[Dict]:
    if wiki_fs.INDEX_FILE.exists():
        with wiki_fs.INDEX_FILE.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def _save_index(entries: List[Dict]) -> None:
    wiki_fs.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with wiki_fs.INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _index_entry(rel_folder: str, meta: Dict, filename: str | None, content: str) -> Dict:
    return {
        "path": rel_folder,
        "file": filename or "",
        "title": meta.get("title", rel_folder.split("/")[-1] if rel_folder else ""),
        "type": meta.get("type", "document"),
        "content": content,
    }


def build_index() -> None:
    entries: List[Dict] = []
    for root, dirs, files in os.walk(wiki_fs.CONTENT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        folder = Path(root)
        rel_folder = folder.relative_to(wiki_fs.CONTENT_ROOT).as_posix()
        meta = wiki_fs.load_meta(folder)
        if not files or not any(f.endswith(".md") for f in files):
            entries.append(_index_entry(rel_folder, meta, None, ""))
        for file in files:
            if file.endswith(".md"):
                content = wiki_fs.read_markdown(folder / file)
                entries.append(_index_entry(rel_folder, meta, file, content))
    _save_index(entries)


def update_index_for_path(rel_path: str) -> None:
    entries = _load_index()
    entries = [e for e in entries if e.get("path") != rel_path]
    folder = wiki_fs.resolve_path(rel_path)
    if not folder.exists():
        _save_index(entries)
        return
    meta = wiki_fs.load_meta(folder)
    has_md = False
    for file in folder.iterdir():
        if file.is_file() and file.name.endswith(".md"):
            has_md = True
            entries.append(_index_entry(rel_path, meta, file.name, wiki_fs.read_markdown(file)))
    if not has_md:
        entries.append(_index_entry(rel_path, meta, None, ""))
    _save_index(entries)


def search(query: str) -> List[Dict]:
    results: List[Dict] = []
    if not query:
        return results
    q = query.lower()
    for entry in _load_index():
        haystack = f"{entry.get('title','')} {entry.get('content','')}".lower()
        if q in haystack:
            results.append(entry)
    return results
