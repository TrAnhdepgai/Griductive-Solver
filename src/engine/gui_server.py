"""Serve the GUI and connect it to LocalGameEngine and LogicAgent.

Run from the repository root with ``python -m src.engine.gui_server``.
"""
from __future__ import annotations

import json
import uuid
import argparse
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.agent.agent import LogicAgent, classify_state, explain
from src.agent.interface import ACCEPTED
from src.agent.local_engine import LocalGameEngine
from src.logic.model import Puzzle
from src.engine.daily import RETENTION_MONTHS, DailyStore, puzzle_id

ROOT = Path(__file__).resolve().parents[2]
GUI = ROOT / "gui"
PUZZLES = ROOT / "puzzles"
games: dict[str, LocalGameEngine] = {}
DAILY = DailyStore()


def gui_clue(clue):
    d = clue.to_dict()
    d["type"] = d.pop("clue_type")
    if "person" in d:
        person = d.pop("person")
        d["a"] = person
        if d["type"] == "FACT": d["cell"] = person
    if "person2" in d: d["b"] = d.pop("person2")
    def region(r):
        if not r: return None
        x = {"kind": r["region_type"].upper()}
        if x["kind"] == "EXPLICIT": x["kind"] = "CELLS"
        for key in ("row", "col", "cell", "cells", "cell1", "cell2", "sub_regions"):
            if key in r: x["index" if key in ("row", "col") else key] = r[key]
        return x
    if "region" in d: d["region"] = region(d["region"])
    if "region2" in d: d["right"] = region(d.pop("region2"))
    if "region" in d and d["type"] in ("COMPARE", "COUNT_COMPARE"): d["left"] = d.pop("region")
    if "compare_op" in d: d["op"] = d.pop("compare_op")
    return d


def _stats(engine):
    """Size of KB_t and DPLL effort needed to classify the current public state.

    Computed once per distinct state (cached on the engine), from the public state only."""
    state = engine.public_state()
    cache = engine.__dict__.setdefault("_gui_stats", {})
    key = tuple(sorted(state.proved.items()))
    if key not in cache:
        cls = classify_state(state)
        s = cls.stats.as_dict()
        cache[key] = {"kb": cls.kb.stats(),
                      "sat": {"calls": s["calls"], "decisions": s["decisions"], "propagations": s["propagations"],
                              "backtracks": s["backtracks"], "conflicts": s["conflicts"],
                              "ms": round(s["runtime_s"] * 1000, 3)},
                      "forced": len(cls.forced), "consistent": cls.consistent}
    return cache[key]


def _total(engine):
    """Cumulative DPLL effort over every distinct state visited in this game."""
    tot = {"calls": 0, "decisions": 0, "propagations": 0, "backtracks": 0}
    for v in engine.__dict__.get("_gui_stats", {}).values():
        for k in tot:
            tot[k] += v["sat"][k]
    return tot


def public_payload(pid, session, engine):
    state = engine.public_state()
    puzzle = Puzzle.from_dict(engine.full_puzzle)
    cells = {c.id: {"name": c.name or c.id, "job": c.profession, "look": ""} for c in state.cells}
    clues = {cid: gui_clue(puzzle.clues[cid]) for cid in state.revealed_clues}
    return {"id": pid, "session": session, "size": state.size, "characters": cells, "clues": clues,
            "initial_revealed": list(engine._puzzle["initial_revealed"]),
            "revealed": state.proved,
            "steps": len(state.proved) - len(engine._puzzle["initial_revealed"]),
            "stats": {**_stats(engine), "total": _total(engine)}}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(GUI), **kwargs)
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()
    def do_OPTIONS(self):
        self.send_response(204); self.end_headers()
    def send_json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/puzzles":
            items=[]
            for f in sorted(PUZZLES.glob("*.json")):
                p=Puzzle.load(f); items.append({"id":p.id,"size":p.size,"difficulty":p.difficulty,"file":f.name})
            return self.send_json(items)
        if path == "/api/daily":
            DAILY.prune()
            lo, hi = DAILY.window()
            return self.send_json({"today": hi.isoformat(), "earliest": lo.isoformat(),
                                   "retention_months": RETENTION_MONTHS, "ready": DAILY.ready_dates()})
        if path == "/api/state":
            query=parse_qs(urlparse(self.path).query)
            session=query.get("session", [""])[0]
            pid=query.get("id", [""])[0]
            return self.send_json(public_payload(pid, session, games[session])) if session in games else self.send_json({"error":"No active game"},404)
        return super().do_GET()
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
        path=urlparse(self.path).path; pid=body.get("id", "3x3_easy_01")
        if path == "/api/start":
            if body.get("date"):
                # Daily mode: one puzzle per calendar date, generated on first use, kept 6 months.
                try:
                    day=date.fromisoformat(body["date"]); file=DAILY.get(day); pid=puzzle_id(day)
                except ValueError as e:
                    return self.send_json({"error":str(e)},400)
                except RuntimeError as e:
                    return self.send_json({"error":f"Không tạo được puzzle: {e}"},500)
            else:
                file=next((p for p in PUZZLES.glob("*.json") if Puzzle.load(p).id==pid),None)
                if file is None: return self.send_json({"error":"Puzzle not found"},404)
            session=uuid.uuid4().hex
            games[session]=LocalGameEngine.load(str(file))
            payload=public_payload(pid,session,games[session])
            payload["date"]=games[session].full_puzzle.get("date"); payload["difficulty"]=games[session].full_puzzle.get("difficulty")
            return self.send_json(payload)

        elif path == "/api/upload":
            raw_puzzle = body.get("puzzle")
            if not isinstance(raw_puzzle, dict):
                return self.send_json({"error": "Dữ liệu file JSON không hợp lệ."}, 400)
            try:
                # Validate cấu trúc puzzle qua model Puzzle trước khi nạp vào engine
                parsed = Puzzle.from_dict(raw_puzzle)
                pid = parsed.id or "custom_puzzle"
                session = uuid.uuid4().hex
                games[session] = LocalGameEngine(raw_puzzle) if hasattr(LocalGameEngine, "__init__") and not isinstance(raw_puzzle, str) else LocalGameEngine.from_dict(raw_puzzle)
                payload = public_payload(pid, session, games[session])
                payload["difficulty"] = raw_puzzle.get("difficulty", "custom")
                return self.send_json(payload)
            except Exception as e:
                return self.send_json({"error": f"Lỗi đọc puzzle: {e}"}, 400)
        session=body.get("session", "")
        if session not in games: return self.send_json({"error":"Game session expired. Restart the puzzle."},404)
        engine=games[session]
        if path == "/api/reset": engine.restart(); engine.submissions=0; engine.__dict__.pop("_gui_stats", None)
        elif path == "/api/call":
            checked=_stats(engine); result=engine.submit_verdict(body["cell"],body["verdict"])
            if result.status != ACCEPTED:
                response={"status":result.status,"message":result.message,"checked":checked}
                if result.status == "NOT_PROVABLE":
                    cls=LogicAgent(engine).classify()
                    response["forced"]={c:cls.verdicts[c].value for c in cls.forced}
                response["state"]=public_payload(pid,session,engine)
                return self.send_json(response)
            response=public_payload(pid,session,engine)
            response["status"]=ACCEPTED; response["checked"]=checked
            return self.send_json(response)
        elif path in ("/api/hint","/api/step"):
            agent=LogicAgent(engine); hint=agent.hint()
            if hint.cell is None: return self.send_json({"status":"STUCK","message":hint.message})
            if path=="/api/hint":
                state=engine.public_state(); clues,_facts=explain(state,hint.cell,hint.verdict)
                return self.send_json({"status":"HINT","cell":hint.cell,"verdict":hint.verdict,"clues":clues,"message":hint.message})
            checked=_stats(engine); result=engine.submit_verdict(hint.cell,hint.verdict)
            return self.send_json({"status":result.status,"cell":hint.cell,"verdict":hint.verdict,"checked":checked})
        return self.send_json(public_payload(pid,session,engine))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Run the Griductive GUI and engine API")
    parser.add_argument("--port", type=int, default=8001)
    port=parser.parse_args().port
    print(f"Griductive GUI: http://127.0.0.1:{port}", flush=True)
    DAILY.warm_up()   # prune puzzles older than 6 months and pre-build today's puzzle in the background
    ThreadingHTTPServer(("127.0.0.1",port),Handler).serve_forever()
