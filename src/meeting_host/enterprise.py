"""Local enterprise workspace: scoped access, encrypted records and content-free views."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import secrets
import sqlite3
import time
from pathlib import Path

from aiohttp import web
from .security import EnvelopeStore, load_kek, prepare_private_dir

ROLES = {"viewer", "operator", "manager", "observer", "support"}
PURPOSES = {"meeting_review", "incident_review"}
SERVICE_STATES = {"ok", "degraded", "unavailable", "unknown"}
COMPONENTS = {"discord", "stt", "tts", "chair"}
ACTOR = web.RequestKey("enterprise_actor", dict)


def metrics(events):
    """Allowlisted numeric projection. No topic/name/text/reason/path survives."""
    duration = 0.0
    speakers = set()
    utterances = interventions = 0
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("data"), dict):
            raise ValueError("Invalid event")
        t = event.get("t", 0)
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or not 0 <= t <= 86400:
            raise ValueError("Invalid event time")
        duration = max(duration, t)
        data = event["data"]
        if event.get("kind") == "meeting":
            people = data.get("participants", [])
            if not isinstance(people, list) or any(not isinstance(p, str) for p in people):
                raise ValueError("Invalid participants")
            speakers.update(people)
        if event.get("kind") == "utterance":
            utterances += 1
        if event.get("kind") == "spoken":
            interventions += 1
    return dict(duration_seconds=round(duration, 1), participants=len(speakers),
                utterances=utterances, interventions=interventions)


class Workspace:
    def __init__(self, path: Path, kek: bytes, identities: list[dict]):
        self.identities = {}
        for item in identities:
            item = dict(item)
            token = item.pop("token")
            if len(token) < 32 or item.get("role") not in ROLES:
                raise ValueError("Invalid identity token or role")
            if not all(isinstance(item.get(k), str) and item[k] for k in ("id", "tenant")):
                raise ValueError("Identity needs id and tenant")
            digest = hashlib.sha256(token.encode()).hexdigest()
            if digest in self.identities or any(i["id"] == item["id"] for i in self.identities.values()):
                raise ValueError("Duplicate identity")
            self.identities[digest] = item
        prepare_private_dir(path.parent)
        if path.is_symlink():
            raise ValueError("Database must not be a symlink")
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        path.chmod(0o600)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meetings (
          id TEXT PRIMARY KEY, tenant TEXT NOT NULL, policy TEXT NOT NULL,
          expires REAL NOT NULL, aggregate TEXT NOT NULL, blob BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS grants (meeting TEXT, actor TEXT, PRIMARY KEY(meeting, actor));
        CREATE TABLE IF NOT EXISTS audit (at REAL, tenant TEXT, actor TEXT, action TEXT, outcome TEXT);
        CREATE TABLE IF NOT EXISTS health (tenant TEXT, component TEXT, state TEXT, at REAL,
          PRIMARY KEY(tenant,component));
        ''')
        self.store = EnvelopeStore(kek)
        self.sessions = {}
        self.attempts = {}

    def identify(self, token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        for expected, identity in self.identities.items():
            if hmac.compare_digest(expected, digest):
                return identity
        return None

    def audit(self, actor, action, outcome):
        self.db.execute("INSERT INTO audit VALUES (?,?,?,?,?)", (time.time(), actor["tenant"],
            hashlib.sha256(actor["id"].encode()).hexdigest()[:16], action, outcome))
        self.db.commit()

    def expire(self):
        with self.db:
            self.db.execute("DELETE FROM grants WHERE meeting IN (SELECT id FROM meetings WHERE expires<=?)", (time.time(),))
            self.db.execute("DELETE FROM meetings WHERE expires<=?", (time.time(),))
            self.db.execute("DELETE FROM audit WHERE at<?", (time.time()-90*86400,))

    def ingest(self, actor, events, policy, days):
        if actor["role"] != "operator":
            raise web.HTTPForbidden()
        if policy not in {"team", "regulated"} or type(days) is not int or not 1 <= days <= 30:
            raise ValueError("Invalid policy or retention")
        if not isinstance(events, list) or not 1 <= len(events) <= 10000:
            raise ValueError("Expected 1..10000 events")
        aggregate = metrics(events)
        mid = secrets.token_hex(16)
        blob = self.store.encrypt_text(json.dumps(events, ensure_ascii=False), meeting_id=mid, artifact_type="events")
        with self.db:
            self.db.execute("INSERT INTO meetings VALUES (?,?,?,?,?,?)", (mid, actor["tenant"], policy,
                time.time()+days*86400, json.dumps(aggregate), blob))
        self.audit(actor, "import", "ok")
        return mid


def create_app(ws: Workspace, origin: str):
    if not (origin.startswith("https://") or origin.startswith("http://127.0.0.1:")):
        raise ValueError("Use HTTPS or loopback")

    @web.middleware
    async def boundary(request, handler):
        try:
            if request.method not in {"GET", "HEAD"} and request.headers.get("Origin") != origin:
                raise web.HTTPForbidden(reason="Origin rejected")
            if request.path.startswith("/api/") and request.path != "/api/login":
                session = ws.sessions.get(request.cookies.get("enterprise", ""))
                if not session or session[1] <= time.time():
                    raise web.HTTPUnauthorized()
                request[ACTOR] = session[0]
            response = await handler(request)
        except web.HTTPException as exc:
            response = web.json_response({"error": exc.reason}, status=exc.status)
        except (ValueError, KeyError, TypeError):
            response = web.json_response({"error": "Invalid request"}, status=400)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "Content-Security-Policy":
            "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'"})
        return response

    async def login(request):
        now = time.time()
        ws.attempts = {k: v for k, v in ws.attempts.items() if v[1] > now}
        key = request.remote
        count, until = ws.attempts.get(key, (0, now+60))
        if count >= 10 or len(ws.attempts) >= 10000:
            raise web.HTTPTooManyRequests()
        ws.attempts[key] = (count+1, until)
        body = await request.json()
        actor = ws.identify(body["token"])
        if not actor:
            raise web.HTTPUnauthorized()
        ws.sessions = {k: v for k, v in ws.sessions.items() if v[1] > now}
        if len(ws.sessions) >= 10000:
            raise web.HTTPServiceUnavailable()
        sid = secrets.token_urlsafe(32)
        ws.sessions[sid] = (actor, now+1800)
        response = web.json_response({"role": actor["role"]})
        response.set_cookie("enterprise", sid, httponly=True, samesite="Strict",
                            secure=origin.startswith("https://"), max_age=1800, path="/")
        ws.audit(actor, "login", "ok")
        return response

    async def logout(request):
        ws.sessions.pop(request.cookies.get("enterprise"), None)
        response = web.json_response({"ok": True})
        response.del_cookie("enterprise", path="/")
        return response

    def require(request, roles):
        actor = request[ACTOR]
        if actor["role"] not in roles:
            ws.audit(actor, "access", "denied")
            raise web.HTTPForbidden()
        return actor

    def meeting(request):
        ws.expire()
        row = ws.db.execute("SELECT * FROM meetings WHERE id=? AND tenant=?",
            (request.match_info["mid"], request[ACTOR]["tenant"])).fetchone()
        if row is None:
            raise web.HTTPNotFound()
        return row

    async def me(request):
        a = request[ACTOR]
        return web.json_response({"role": a["role"], "tenant": a["tenant"],
                                  "regulated_content": a.get("regulated_content") is True})

    async def analytics(request):
        actor = require(request, {"operator", "manager", "observer", "viewer"})
        ws.expire()
        rows = ws.db.execute("SELECT id,policy,aggregate FROM meetings WHERE tenant=?", (actor["tenant"],)).fetchall()
        if actor["role"] == "viewer":
            allowed = {r[0] for r in ws.db.execute("SELECT meeting FROM grants WHERE actor=?", (actor["id"],))}
            rows = [r for r in rows if r["id"] in allowed]
        items = [{"id": r["id"], "policy": r["policy"], **json.loads(r["aggregate"])} for r in rows]
        return web.json_response({"meetings": items, "count": len(items),
            "total_minutes": round(sum(i["duration_seconds"] for i in items)/60, 1)})

    async def content(request):
        actor = require(request, {"operator", "viewer"})
        row = meeting(request)
        granted = actor["role"] == "operator" or ws.db.execute(
            "SELECT 1 FROM grants WHERE meeting=? AND actor=?", (row["id"], actor["id"])).fetchone()
        purpose = (await request.json()).get("purpose")
        if not granted or purpose not in PURPOSES or (row["policy"] == "regulated" and actor.get("regulated_content") is not True):
            ws.audit(actor, "content", "denied")
            raise web.HTTPForbidden()
        text = ws.store.decrypt_text(row["blob"], meeting_id=row["id"], artifact_type="events", purpose=purpose, operator=True)
        ws.audit(actor, "content:"+purpose, "ok")
        return web.json_response({"events": json.loads(text)})

    async def ingest(request):
        actor = require(request, {"operator"})
        body = await request.json()
        mid = ws.ingest(actor, body["events"], body.get("policy", "team"), body.get("days", 7))
        return web.json_response({"id": mid}, status=201)

    async def grants(request):
        actor = require(request, {"operator"})
        row = meeting(request)
        if row["policy"] == "regulated" and actor.get("regulated_content") is not True:
            raise web.HTTPForbidden()
        if request.method == "GET":
            candidates = [dict(id=a["id"], granted=bool(ws.db.execute("SELECT 1 FROM grants WHERE meeting=? AND actor=?",
                (row["id"], a["id"])).fetchone())) for a in ws.identities.values()
                if a["tenant"] == actor["tenant"] and a["role"] == "viewer"]
            return web.json_response({"viewers": candidates})
        body = await request.json()
        target = next((a for a in ws.identities.values() if a["id"] == body.get("actor") and
                       a["tenant"] == actor["tenant"] and a["role"] == "viewer"), None)
        if target is None or type(body.get("allow")) is not bool:
            raise ValueError("Invalid grant")
        with ws.db:
            if body["allow"]:
                ws.db.execute("INSERT OR IGNORE INTO grants VALUES (?,?)", (row["id"], target["id"]))
            else:
                ws.db.execute("DELETE FROM grants WHERE meeting=? AND actor=?", (row["id"], target["id"]))
        ws.audit(actor, "grant" if body["allow"] else "revoke", "ok")
        return web.json_response({"ok": True})

    async def health(request):
        actor = require(request, {"operator", "support"})
        if request.method == "POST":
            require(request, {"operator"})
            body = await request.json()
            if body.get("component") not in COMPONENTS or body.get("state") not in SERVICE_STATES:
                raise ValueError("Use allowlisted component/state")
            with ws.db:
                ws.db.execute("INSERT OR REPLACE INTO health VALUES (?,?,?,?)", (actor["tenant"], body["component"], body["state"], time.time()))
        rows = {r["component"]: r for r in ws.db.execute("SELECT * FROM health WHERE tenant=?", (actor["tenant"],))}
        return web.json_response({"components": [dict(component=c,
            state=rows[c]["state"] if c in rows and time.time()-rows[c]["at"] < 300 else "unknown",
            updated_at=rows[c]["at"] if c in rows else None) for c in sorted(COMPONENTS)]})

    async def audit(request):
        actor = require(request, {"operator"})
        return web.json_response({"entries": [dict(r) for r in ws.db.execute(
            "SELECT at,actor,action,outcome FROM audit WHERE tenant=? ORDER BY at DESC LIMIT 100", (actor["tenant"],))]})

    async def purge(request):
        actor = require(request, {"operator"})
        row = meeting(request)
        with ws.db:
            ws.db.execute("DELETE FROM grants WHERE meeting=?", (row["id"],))
            ws.db.execute("DELETE FROM meetings WHERE id=?", (row["id"],))
        ws.audit(actor, "delete", "ok")
        return web.json_response({"ok": True})

    app = web.Application(middlewares=[boundary], client_max_size=4*1024*1024)
    app.add_routes([web.post('/api/login', login), web.post('/api/logout', logout), web.get('/api/me', me),
        web.get('/api/analytics', analytics), web.post('/api/meetings', ingest),
        web.post('/api/meetings/{mid}/content', content), web.get('/api/meetings/{mid}/grants', grants),
        web.post('/api/meetings/{mid}/grants', grants), web.delete('/api/meetings/{mid}', purge),
        web.get('/api/health', health), web.post('/api/health', health), web.get('/api/audit', audit)])
    async def index(request):
        return web.FileResponse(Path(__file__).parent/'enterprise_ui'/'index.html')
    app.router.add_get('/', index)
    app.router.add_static('/ui/', Path(__file__).parent/'enterprise_ui')
    async def retention(app):
        import asyncio
        async def sweep():
            while True:
                ws.expire()
                await asyncio.sleep(60)
        task = asyncio.create_task(sweep())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        ws.db.close()
    app.cleanup_ctx.append(retention)
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--identities', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8890)
    args = parser.parse_args()
    if args.identities.is_symlink() or args.identities.stat().st_mode & 0o077:
        raise ValueError('Identities file must be private (0600)')
    ws = Workspace(args.database, load_kek(), json.loads(args.identities.read_text()))
    web.run_app(create_app(ws, f'http://127.0.0.1:{args.port}'), host='127.0.0.1', port=args.port,
                access_log=None)


if __name__ == '__main__':
    main()
