import urllib.parse
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import markdown

from . import search, wiki_fs

app = FastAPI(title="Internal Wiki")
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/content", StaticFiles(directory=wiki_fs.CONTENT_ROOT, html=True), name="content")


def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=[
            "extra",
            "admonition",
            "codehilite",
            "fenced_code",
            "tables",
            "toc",
        ],
        output_format="html5",
    )


def shared_context(current_path: str = "", current_type: str = "root"):
    return {"companies": wiki_fs.list_companies(), "current_path": current_path, "current_type": current_type}


@app.on_event("startup")
async def startup_event():
    wiki_fs.ensure_content_root()
    wiki_fs.bootstrap_demo()
    search.build_index()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    context = {
        "request": request,
        "recent": wiki_fs.list_recent_changes(),
        **shared_context(""),
    }
    return templates.TemplateResponse("index.html", context)


def _resolve_folder_and_file(rel_path: str, tab: Optional[str] = None) -> Path:
    resolved = wiki_fs.resolve_path(rel_path or "")
    if resolved.is_dir():
        if tab:
            candidate = resolved / tab
            if candidate.suffix != ".md":
                candidate = candidate.with_suffix(".md")
            return candidate
        return resolved / "index.md"
    return resolved


def _validate_exists(path: Path) -> None:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")


@app.get("/view", response_class=HTMLResponse)
async def view_root(request: Request):
    return await view_page(request, path="", tab=None)


@app.get("/view/{path:path}", response_class=HTMLResponse)
async def view_page(request: Request, path: str, tab: Optional[str] = None):
    decoded_path = urllib.parse.unquote(path or "")
    folder = wiki_fs.resolve_path(decoded_path or "")
    if not folder.exists():
        context = {
            "request": request,
            "missing_path": decoded_path,
            **shared_context(decoded_path, "root"),
        }
        return templates.TemplateResponse("not_found.html", context, status_code=404)
    meta = wiki_fs.load_meta(folder if folder.is_dir() else folder.parent)
    entity_type = meta.get("type", "document")
    breadcrumbs = wiki_fs.breadcrumbs(decoded_path)
    content_html = ""
    active_tab = tab
    service_tabs = []
    has_index = False
    index_path = folder / "index.md" if folder.is_dir() else folder

    if entity_type == "service" and folder.is_dir():
        tab_files = [
            ("overview.md", "Обзор"),
            ("passport.md", "Паспорт"),
            ("architecture.md", "Архитектура"),
            ("operations.md", "Эксплуатация"),
            ("incidents.md", "Аварии"),
            ("docs.md", "Документы"),
            ("service-network.md", "Сеть сервиса"),
        ]
        active_tab = tab or "overview.md"
        for filename, title in tab_files:
            file_path = folder / filename
            html = render_markdown(wiki_fs.read_markdown(file_path)) if file_path.exists() else ""
            service_tabs.append({"key": filename, "title": title, "html": html, "exists": file_path.exists()})
            if filename == active_tab:
                content_html = html
        if not content_html and index_path.exists():
            has_index = True
            content_html = render_markdown(wiki_fs.read_markdown(index_path))
    else:
        md_file = _resolve_folder_and_file(decoded_path, tab)
        if md_file.exists():
            has_index = True
            content_html = render_markdown(wiki_fs.read_markdown(md_file))

    context = {
        "request": request,
        "path": decoded_path,
        "meta": meta,
        "breadcrumbs": breadcrumbs,
        "content_html": content_html,
        "service_tabs": service_tabs,
        "active_tab": active_tab,
        "has_index": has_index,
        **shared_context(decoded_path, entity_type),
    }
    return templates.TemplateResponse("view.html", context)


@app.get("/edit/{path:path}", response_class=HTMLResponse)
async def edit_page(request: Request, path: str, tab: Optional[str] = None):
    md_path = _resolve_folder_and_file(path, tab)
    parent = md_path.parent
    try:
        wiki_fs.resolve_path(path if md_path.is_dir() else md_path.relative_to(wiki_fs.CONTENT_ROOT).as_posix())
    except wiki_fs.WikiPathError as e:
        raise HTTPException(status_code=400, detail=str(e))
    parent.mkdir(parents=True, exist_ok=True)
    content = ""
    if md_path.exists():
        content = wiki_fs.read_markdown(md_path)
    meta = wiki_fs.load_meta(parent)
    breadcrumbs = wiki_fs.breadcrumbs(parent.relative_to(wiki_fs.CONTENT_ROOT).as_posix())
    context = {
        "request": request,
        "meta": meta,
        "path": parent.relative_to(wiki_fs.CONTENT_ROOT).as_posix(),
        "file_name": md_path.name,
        "content": content,
        "breadcrumbs": breadcrumbs,
        **shared_context(parent.relative_to(wiki_fs.CONTENT_ROOT).as_posix()),
    }
    return templates.TemplateResponse("edit.html", context)


class MkdirPayload(BaseModel):
    parent: str = ""
    name: str
    title: str
    type: str = Field(alias="type")


class CreatePagePayload(BaseModel):
    parent: str = ""
    name: str
    title: str
    type: str = Field(alias="type")


class SavePayload(BaseModel):
    path: str
    file_name: str
    content: str


class TrashPayload(BaseModel):
    path: str


@app.post("/api/mkdir")
async def api_mkdir(payload: MkdirPayload):
    try:
        folder = wiki_fs.create_folder(payload.parent or "", payload.name, payload.type, payload.title)
    except wiki_fs.WikiPathError as e:
        raise HTTPException(
            status_code=400,
            detail={"ok": False, "error": str(e), "field": "name"},
        )
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail={"ok": False, "error": "Узел уже существует", "field": "name"},
        )
    search.update_index_for_path(folder.relative_to(wiki_fs.CONTENT_ROOT).as_posix())
    path_str = folder.relative_to(wiki_fs.CONTENT_ROOT).as_posix()
    return {"ok": True, "path": path_str, "view_url": f"/view/{path_str}", "title": payload.title}


@app.post("/api/create-page")
async def api_create_page(payload: CreatePagePayload):
    try:
        folder = wiki_fs.create_page(payload.parent or "", payload.name, payload.title, payload.type)
    except wiki_fs.WikiPathError as e:
        raise HTTPException(
            status_code=400,
            detail={"ok": False, "error": str(e), "field": "name"},
        )
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail={"ok": False, "error": "Узел уже существует", "field": "name"},
        )
    search.update_index_for_path(folder.relative_to(wiki_fs.CONTENT_ROOT).as_posix())
    path_str = folder.relative_to(wiki_fs.CONTENT_ROOT).as_posix()
    return {"ok": True, "path": path_str, "view_url": f"/view/{path_str}", "title": payload.title}


@app.post("/api/save")
async def api_save(payload: SavePayload):
    target_folder = wiki_fs.resolve_path(payload.path or "", allow_nonexistent=False)
    md_path = target_folder / payload.file_name
    wiki_fs.write_markdown(md_path, payload.content)
    search.update_index_for_path(payload.path)
    return {"ok": True, "saved": True, "path": payload.path, "file": payload.file_name}


@app.post("/api/upload")
async def api_upload(path: str = Form(...), file: UploadFile = File(...)):
    data = await file.read()
    dest = wiki_fs.upload_file(path or "", file.filename, data)
    search.update_index_for_path(path)
    path_str = path or ""
    return {
        "ok": True,
        "uploaded": dest.name,
        "url": f"/content/{dest.relative_to(wiki_fs.CONTENT_ROOT)}",
        "view_url": f"/view/{path_str}" if path_str else "/view",
    }


@app.post("/api/trash")
async def api_trash(payload: TrashPayload):
    moved = wiki_fs.move_to_trash(payload.path)
    search.update_index_for_path(payload.path)
    return {"ok": True, "trashed": payload.path, "moved_to": moved.as_posix()}


@app.get("/api/tree")
async def api_tree():
    return {"ok": True, "tree": wiki_fs.build_tree()}


@app.post("/save/{path:path}")
async def save_page(path: str, file_name: str = Form(...), content: str = Form(...)):
    target_folder = wiki_fs.resolve_path(path or "")
    md_path = target_folder / file_name
    wiki_fs.write_markdown(md_path, content)
    search.update_index_for_path(path)
    return RedirectResponse(url=f"/view/{path}", status_code=303)


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: Optional[str] = None):
    results = search.search(q or "")
    context = {"request": request, "results": results, "query": q or "", **shared_context("", "root")}
    return templates.TemplateResponse("search.html", context)


@app.exception_handler(wiki_fs.WikiPathError)
async def wiki_path_error_handler(request: Request, exc: wiki_fs.WikiPathError):
    if str(request.url.path).startswith("/api/"):
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc), "field": "path"})
    return HTMLResponse(content=f"<h3>Bad path: {exc}</h3>", status_code=400)
