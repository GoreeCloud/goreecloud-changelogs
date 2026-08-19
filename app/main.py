from __future__ import annotations

import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .db import connect, init_db

BASE = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="GoreeCloud Changelogs",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


def list_entries(q: str = "", project: str = "", limit: int = 100):
    with connect() as cx:
        params: list[object] = []
        where: list[str] = []
        join = "JOIN projects p ON p.id=e.project_id"
        if q.strip():
            join += " JOIN entries_fts f ON f.rowid=e.id"
            where.append("f.entries_fts MATCH ?")
            params.append(q.strip().replace('"', ""))
        if project:
            where.append("p.slug=?")
            params.append(project)
        sql = f"SELECT e.*,p.slug project_slug,p.name project_name FROM entries e {join}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.occurred_at DESC,e.id DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in cx.execute(sql, params)]


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", project: str = ""):
    with connect() as cx:
        projects = [
            dict(row)
            for row in cx.execute(
                "SELECT p.*,count(e.id) entry_count,max(e.occurred_at) latest "
                "FROM projects p LEFT JOIN entries e ON e.project_id=p.id "
                "GROUP BY p.id ORDER BY p.name"
            )
        ]
        count = cx.execute("SELECT count(*) c FROM entries").fetchone()["c"]
    entries = list_entries(q, project, 120)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"entries": entries, "projects": projects, "q": q, "project": project, "count": count},
    )


@app.get("/entry/{entry_id}", response_class=HTMLResponse)
def entry_page(request: Request, entry_id: int):
    with connect() as cx:
        row = cx.execute(
            "SELECT e.*,p.name project_name,p.slug project_slug "
            "FROM entries e JOIN projects p ON p.id=e.project_id WHERE e.id=?",
            (entry_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "entry.html", {"entry": dict(row)})


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(
        {
            "name": "GoreeCloud Changelogs",
            "short_name": "Changelogs",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0c1220",
            "theme_color": "#6d7cff",
            "icons": [
                {
                    "src": "/static/icon.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any maskable",
                }
            ],
        },
        media_type="application/manifest+json",
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/v1/projects")
def api_projects():
    with connect() as cx:
        return [dict(row) for row in cx.execute("SELECT * FROM projects ORDER BY name")]


@app.get("/api/v1/entries")
def api_entries(q: str = "", project: str = "", limit: int = Query(100, ge=1, le=500)):
    return list_entries(q, project, limit)


@app.get("/api/v1/entries/{entry_id}")
def api_entry(entry_id: int):
    with connect() as cx:
        row = cx.execute(
            "SELECT e.*,p.slug project_slug,p.name project_name "
            "FROM entries e JOIN projects p ON p.id=e.project_id WHERE e.id=?",
            (entry_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404)
    return dict(row)


class EntryCreate(BaseModel):
    project_slug: str = Field(min_length=1, max_length=80)
    project_name: str = Field(min_length=1, max_length=120)
    occurred_at: str
    title: str = Field(min_length=1, max_length=240)
    category: str = ""
    summary: str = ""
    purpose: str = ""
    affected: str = ""
    previous_state: str = ""
    changes: str = ""
    implementation: str = ""
    validation: str = ""
    final_state: str = ""
    limitations: str = ""
    rollback: str = ""
    follow_up: str = ""
    release: str = ""
    environment: str = ""
    source_ref: str = ""
    supersedes_id: int | None = None


@app.post("/api/v1/entries", status_code=201)
def create_entry(data: EntryCreate, authorization: str | None = Header(default=None)):
    expected = os.getenv("CHANGELOGS_WRITE_TOKEN", "")
    if not expected:
        raise HTTPException(503, "write API disabled")
    supplied = (authorization or "").removeprefix("Bearer ")
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(401, "unauthorized", headers={"WWW-Authenticate": "Bearer"})

    slug = re.sub(r"[^a-z0-9-]+", "-", data.project_slug.lower()).strip("-")
    if not slug:
        raise HTTPException(422, "invalid project slug")

    with connect() as cx:
        cx.execute(
            "INSERT INTO projects(slug,name) VALUES(?,?) "
            "ON CONFLICT(slug) DO UPDATE SET name=excluded.name",
            (slug, data.project_name),
        )
        project_id = cx.execute("SELECT id FROM projects WHERE slug=?", (slug,)).fetchone()["id"]
        fields = [
            "occurred_at",
            "title",
            "category",
            "summary",
            "purpose",
            "affected",
            "previous_state",
            "changes",
            "implementation",
            "validation",
            "final_state",
            "limitations",
            "rollback",
            "follow_up",
            "release",
            "environment",
            "source_ref",
            "supersedes_id",
        ]
        values = [getattr(data, field) for field in fields]
        qmarks = ",".join("?" for _ in values)
        cursor = cx.execute(
            f"INSERT INTO entries(project_id,{','.join(fields)}) VALUES(?,{qmarks})",
            [project_id, *values],
        )
        entry_id = cursor.lastrowid
    return {"id": entry_id, "status": "created"}
