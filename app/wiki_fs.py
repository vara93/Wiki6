import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

CONTENT_ROOT = Path(os.environ.get("WIKI_CONTENT_ROOT", "/opt/wiki/content")).resolve()
TRASH_ROOT = CONTENT_ROOT / ".trash"
INDEX_FILE = Path(os.environ.get("WIKI_INDEX_FILE", "/opt/wiki/.index.json")).resolve()

ALLOWED_CHILDREN = {
    None: {"company"},
    "root": {"company"},
    "company": {"dc"},
    "dc": {"section", "document", "service", "server", "network"},
    "section": {"section", "document", "service", "server", "network"},
    "document": set(),
    "service": set(),
    "server": set(),
    "network": set(),
}


class WikiPathError(Exception):
    """Raised when a resolved path is outside the content root or violates structure."""


def ensure_content_root() -> None:
    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    TRASH_ROOT.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def validate_system_name(name: str) -> str:
    if not name or any(ch in name for ch in ["/", "\\", ".."]):
        raise WikiPathError("Invalid system name. Use latin letters, digits, '-' or '_'.")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if not set(name) <= allowed:
        raise WikiPathError("Invalid system name. Use latin letters, digits, '-' or '_'.")
    return name


def resolve_path(rel_path: str, allow_nonexistent: bool = True) -> Path:
    safe_rel = rel_path.strip().lstrip("/")
    candidate = (CONTENT_ROOT / safe_rel).resolve()
    if not str(candidate).startswith(str(CONTENT_ROOT)):
        raise WikiPathError("Path traversal detected")
    if not allow_nonexistent and not candidate.exists():
        raise FileNotFoundError(rel_path)
    return candidate


def path_to_url(rel_path: str) -> str:
    cleaned = rel_path.strip().lstrip("/")
    return cleaned


def load_meta(folder: Path) -> Dict:
    meta_path = folder / "meta.json"
    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_meta(folder: Path, meta: Dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    meta.setdefault("created", _now_iso())
    meta["updated"] = _now_iso()
    with (folder / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def default_meta(name: str, type_value: str = "document") -> Dict:
    return {"title": name, "type": type_value, "created": _now_iso(), "updated": _now_iso()}


def slugify(title: str) -> str:
    translit = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ы": "y",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    text = title.lower().strip()
    text = "".join(translit.get(ch, ch) for ch in text)
    text = text.replace(" ", "-")
    out = "".join(ch for ch in text if ch.isalnum() or ch in "-_")
    out = out.strip("-_")
    return out or "node"


def generate_unique_name(parent: Path, base: str) -> str:
    candidate = base
    counter = 2
    while (parent / candidate).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def node_type(folder: Path, parent_is_root: bool = False) -> str:
    if folder == CONTENT_ROOT:
        return "root"
    meta = load_meta(folder)
    return meta.get("type", "section" if not parent_is_root else "company")


def allowed_children(parent_type: str | None) -> set:
    return ALLOWED_CHILDREN.get(parent_type, set())


def validate_child_type(parent_type: str | None, child_type: str) -> None:
    if child_type not in allowed_children(parent_type):
        raise WikiPathError(f"Нельзя создавать {child_type} внутри {parent_type or 'root'}")


def list_companies() -> List[Dict]:
    companies: List[Dict] = []
    for item in sorted(CONTENT_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        meta = load_meta(item)
        if meta.get("type") != "company":
            continue
        companies.append(
            {
                "name": item.name,
                "title": meta.get("title", item.name),
                "type": meta.get("type", "company"),
                "path": item.relative_to(CONTENT_ROOT).as_posix(),
            }
        )
    return companies


def build_tree(base: Path = CONTENT_ROOT, parent_type: str | None = None) -> List[Dict]:
    nodes: List[Dict] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        meta = load_meta(entry)
        entry_type = meta.get("type")
        parent_ctx = parent_type or "root"
        if entry_type not in allowed_children(parent_ctx):
            continue
        node = {
            "name": entry.name,
            "title": meta.get("title", entry.name),
            "type": entry_type,
            "path": entry.relative_to(CONTENT_ROOT).as_posix(),
            "children": build_tree(entry, entry_type),
        }
        nodes.append(node)
    return nodes


def build_subtree(rel_path: str) -> Dict:
    base = resolve_path(rel_path or "")
    meta = load_meta(base)
    t = meta.get("type", "section")
    return {
        "name": base.name if base != CONTENT_ROOT else "",
        "title": meta.get("title", base.name),
        "type": t,
        "path": base.relative_to(CONTENT_ROOT).as_posix() if base != CONTENT_ROOT else "",
        "children": build_tree(base, t),
    }


def read_markdown(markdown_path: Path) -> str:
    with markdown_path.open("r", encoding="utf-8") as f:
        return f.read()


def write_markdown(markdown_path: Path, content: str) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with markdown_path.open("w", encoding="utf-8") as f:
        f.write(content)
    save_meta(markdown_path.parent, load_meta(markdown_path.parent))


def ensure_index(folder: Path, type_value: str, title: str) -> None:
    index_path = folder / "index.md"
    if index_path.exists():
        return
    if type_value == "company":
        body = f"# {title}\n\n## Описание\n\nДобавьте описание компании.\n\n## ЦОДы\n- "
    elif type_value == "dc":
        body = f"# {title}\n\n## Описание ЦОД\n\nДобавьте детали площадки.\n\n## Разделы\n- "
    elif type_value == "section":
        body = f"# {title}\n\n## Раздел\n\nДобавьте контент раздела."
    elif type_value == "service":
        body = f"# {title}\n\nИспользуйте вкладки сервиса для детального описания."
    else:
        body = f"# {title}\n\nДобавьте контент."
    create_markdown_page(folder, "index.md", title, body)


def create_folder(parent_rel: str, name: str | None, type_value: str = "document", title: str | None = None) -> Path:
    parent = resolve_path(parent_rel)
    parent_type = node_type(parent, parent == CONTENT_ROOT)
    validate_child_type(parent_type if parent_type != "root" else None, type_value)
    parent.mkdir(parents=True, exist_ok=True)
    if not name:
        name = slugify(title or "node")
    name = validate_system_name(name)
    name = generate_unique_name(parent, name)
    new_folder = parent / name
    new_folder.mkdir(parents=False, exist_ok=False)
    meta = load_meta(new_folder) or default_meta(title or name, type_value)
    meta["title"] = title or meta.get("title", name)
    meta["type"] = type_value
    save_meta(new_folder, meta)
    ensure_index(new_folder, type_value, meta["title"])
    return new_folder


def create_markdown_page(folder: Path, filename: str, title: str, body: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    write_markdown(folder / filename, f"# {title}\n\n{body}")


def create_service_template(folder: Path, title: str) -> None:
    templates: List[Tuple[str, str]] = [
        ("overview.md", "Обзор"),
        ("passport.md", "Паспорт"),
        ("architecture.md", "Архитектура"),
        ("operations.md", "Эксплуатация"),
        ("incidents.md", "Аварии"),
        ("docs.md", "Документы"),
        ("service-network.md", "Сеть сервиса"),
    ]
    for filename, tab_title in templates:
        create_markdown_page(folder, filename, tab_title, f"Контент раздела «{tab_title}» сервиса {title}.")


def create_server_template(folder: Path, title: str) -> None:
    body = "\n".join(
        [
            "| Параметр | Значение |",
            "| --- | --- |",
            "| Роль |  |",
            "| ОС |  |",
            "| CPU/RAM |  |",
            "| Сеть |  |",
            "| Доступы |  |",
            "| Бэкапы |  |",
        ]
    )
    create_markdown_page(folder, "index.md", title or "Паспорт сервера", body)


def create_network_template(folder: Path, title: str) -> None:
    body = "\n".join(
        [
            "## Сегменты",
            "- ",
            "## VLAN",
            "- ",
            "## Подсети",
            "- ",
            "## Маршрутизация",
            "- ",
            "## ACL",
            "- ",
        ]
    )
    create_markdown_page(folder, "index.md", title or "Сеть", body)


def create_document_template(folder: Path, title: str) -> None:
    body = "\n".join(
        [
            "## Цель",
            "",
            "## Описание",
            "",
            "## Вложения",
            "- Добавьте файлы в папку `assets/`",
        ]
    )
    create_markdown_page(folder, "index.md", title or "Документ", body)


def create_page(parent_rel: str, name: str | None, title: str, type_value: str) -> Path:
    folder = create_folder(parent_rel, name, type_value, title)
    if type_value == "service":
        create_service_template(folder, title)
    elif type_value == "server":
        create_server_template(folder, title)
    elif type_value == "network":
        create_network_template(folder, title)
    else:
        create_document_template(folder, title)
    ensure_index(folder, type_value, title)
    return folder


def save_service_network(rel_path: str, items: List[Dict]) -> Path:
    folder = resolve_path(rel_path, allow_nonexistent=False)
    meta = load_meta(folder)
    meta["service_network"] = {"items": items}
    save_meta(folder, meta)
    # regenerate markdown
    lines = ["# Сеть сервиса", "", "| Name | IP | Mask | Gateway | DNS |", "| --- | --- | --- | --- | --- |"]
    for row in items:
        lines.append(
            f"| {row.get('name','')} | {row.get('ip','')} | {row.get('mask','')} | {row.get('gateway','')} | {row.get('dns','')} |"
        )
    write_markdown(folder / "service-network.md", "\n".join(lines))
    return folder


def upload_file(target_rel: str, filename: str, data: bytes) -> Path:
    target_folder = resolve_path(target_rel)
    assets = target_folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    dest = assets / filename
    with dest.open("wb") as f:
        f.write(data)
    return dest


def move_to_trash(target_rel: str) -> Path:
    target = resolve_path(target_rel, allow_nonexistent=False)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    relative = target.relative_to(CONTENT_ROOT)
    trash_destination = TRASH_ROOT / timestamp / relative
    trash_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(trash_destination))
    return trash_destination


def list_recent_changes(limit: int = 10) -> List[Dict]:
    records: List[Tuple[datetime, Dict]] = []
    for root, dirs, files in os.walk(CONTENT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if "meta.json" in files:
            folder = Path(root)
            meta = load_meta(folder)
            updated_str = meta.get("updated")
            try:
                updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.utcnow()
            except ValueError:
                updated_dt = datetime.utcnow()
            records.append(
                (
                    updated_dt,
                    {
                        "title": meta.get("title", folder.name),
                        "type": meta.get("type", "document"),
                        "path": folder.relative_to(CONTENT_ROOT).as_posix(),
                        "updated": updated_dt,
                    },
                )
            )
    sorted_records = sorted(records, key=lambda x: x[0], reverse=True)
    return [r[1] for r in sorted_records[:limit]]


def list_children(rel_path: str) -> List[Dict]:
    base = resolve_path(rel_path or "")
    parent_type = node_type(base, base == CONTENT_ROOT)
    children: List[Dict] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        meta = load_meta(entry)
        entry_type = meta.get("type")
        if entry_type not in allowed_children(parent_type if parent_type != "root" else None):
            continue
        children.append(
            {
                "name": entry.name,
                "title": meta.get("title", entry.name),
                "type": entry_type,
                "path": entry.relative_to(CONTENT_ROOT).as_posix(),
            }
        )
    return children


def breadcrumbs(rel_path: str) -> List[Dict]:
    crumbs: List[Dict] = [{"title": "Главная", "path": ""}]
    segments = [seg for seg in rel_path.split("/") if seg]
    current_parts: List[str] = []
    for segment in segments:
        current_parts.append(segment)
        folder = resolve_path("/".join(current_parts))
        meta = load_meta(folder)
        crumbs.append({"title": meta.get("title", folder.name), "path": "/".join(current_parts)})
    return crumbs


def bootstrap_demo() -> None:
    if any(CONTENT_ROOT.iterdir()):
        return
    company_a = create_folder("", "Company_A", "company", "Компания A")
    dc_a = create_folder("Company_A", "DC_Prokhorova", "dc", "DC Prokhorova")
    rds = create_page("Company_A/DC_Prokhorova", "RDS_Farm", "RDS Farm", "service")
    save_meta(rds, {"title": "RDS Farm", "type": "service"})
    exch = create_page("Company_A/DC_Prokhorova", "EXCH_DAG", "Exchange DAG", "service")
    save_meta(exch, {"title": "Exchange DAG", "type": "service"})

    company_b = create_folder("", "Company_B", "company", "Компания B")
    dc_b = create_folder("Company_B", "DC_Mashkova", "dc", "DC Mashkova")
    for node in [company_a, company_b, dc_a, dc_b]:
        save_meta(node, load_meta(node))
