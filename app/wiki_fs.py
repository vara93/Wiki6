import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

CONTENT_ROOT = Path(os.environ.get("WIKI_CONTENT_ROOT", "/opt/wiki/content")).resolve()
TRASH_ROOT = CONTENT_ROOT / ".trash"
INDEX_FILE = Path(os.environ.get("WIKI_INDEX_FILE", "/opt/wiki/.index.json")).resolve()


class WikiPathError(Exception):
    """Raised when a resolved path is outside the content root."""


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


def list_companies() -> List[Dict]:
    companies: List[Dict] = []
    for item in sorted(CONTENT_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        meta = load_meta(item)
        companies.append(
            {
                "name": item.name,
                "title": meta.get("title", item.name),
                "type": meta.get("type", "company"),
                "path": item.relative_to(CONTENT_ROOT).as_posix(),
            }
        )
    return companies


def build_tree(base: Path = CONTENT_ROOT) -> List[Dict]:
    nodes: List[Dict] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        meta = load_meta(entry)
        node = {
            "name": entry.name,
            "title": meta.get("title", entry.name),
            "type": meta.get("type", "document"),
            "path": entry.relative_to(CONTENT_ROOT).as_posix(),
            "children": build_tree(entry),
        }
        nodes.append(node)
    return nodes


def read_markdown(markdown_path: Path) -> str:
    with markdown_path.open("r", encoding="utf-8") as f:
        return f.read()


def write_markdown(markdown_path: Path, content: str) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with markdown_path.open("w", encoding="utf-8") as f:
        f.write(content)
    save_meta(markdown_path.parent, load_meta(markdown_path.parent))


def create_folder(parent_rel: str, name: str, type_value: str = "document", title: str | None = None) -> Path:
    validate_system_name(name)
    parent = resolve_path(parent_rel)
    parent.mkdir(parents=True, exist_ok=True)
    new_folder = parent / name
    new_folder.mkdir(parents=False, exist_ok=False)
    meta = load_meta(new_folder) or default_meta(title or name, type_value)
    meta["title"] = title or meta.get("title", name)
    meta["type"] = type_value
    save_meta(new_folder, meta)
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


def create_page(parent_rel: str, name: str, title: str, type_value: str) -> Path:
    folder = create_folder(parent_rel, name, type_value, title)
    if type_value == "service":
        create_service_template(folder, title)
    elif type_value == "server":
        create_server_template(folder, title)
    elif type_value == "network":
        create_network_template(folder, title)
    else:
        create_document_template(folder, title)
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
