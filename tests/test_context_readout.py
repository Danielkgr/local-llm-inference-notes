"""Context reporting uses synthetic metadata and never returns chat bodies from SQL."""

from __future__ import annotations

import json
import sqlite3

from conftest import TOOLS, load_script


def test_only_usage_metadata_crosses_the_sql_boundary(tmp_path, monkeypatch):
    module = load_script(TOOLS / "context-readout.py", "context_readout")
    path = tmp_path / "chat ?#%.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE chat (chat TEXT, updated_at INTEGER)")
        messages = {
            "first": {"role": "assistant", "model": "model", "usage": {"prompt_n": 200}},
            "last": {
                "role": "assistant",
                "model": "model",
                "usage": {"input_tokens": 100},
                "content": "PRIVATE FIXTURE CONTENT",
            },
            "user": {"role": "user", "content": "PRIVATE FIXTURE CONTENT"},
        }
        con.executemany(
            "INSERT INTO chat VALUES (?, ?)",
            [
                (json.dumps({"history": {"messages": messages}}), 2),
                ("invalid JSON", 1),
            ],
        )
    connect = sqlite3.connect
    returned = []

    class Connection:
        def __init__(self, *args, **kwargs):
            self.con = connect(*args, **kwargs)

        def execute(self, query, parameters):
            rows = self.con.execute(query, parameters).fetchall()
            returned.extend(rows)
            return rows

        def close(self):
            self.con.close()

    monkeypatch.setattr(module.sqlite3, "connect", Connection)
    assert module.chat_stats(str(path), 2) == {"model": (100, 200, 2)}
    assert all(len(row) == 2 for row in returned)
    assert "PRIVATE" not in repr(returned)


def test_malformed_metadata_and_recent_chat_limit(tmp_path):
    module = load_script(TOOLS / "context-readout.py", "context_readout")
    path = tmp_path / "chat.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE chat (chat TEXT, updated_at INTEGER)")
        for index, messages in enumerate(
            [
                {"old": {"role": "assistant", "model": "old", "usage": {"prompt_n": 900}}},
                {"bad": "not an object"},
                {"bad": {"role": "assistant", "model": [], "usage": {"prompt_n": "bad"}}},
                {"ok": {"role": "assistant", "model": "new", "usage": {"prompt_n": 12}}},
            ]
        ):
            con.execute(
                "INSERT INTO chat VALUES (?, ?)",
                (json.dumps({"history": {"messages": messages}}), index),
            )
    assert module.chat_stats(str(path), 3) == {"new": (12, 12, 1)}


def test_context_is_per_slot_and_ignores_comments(tmp_path):
    module = load_script(TOOLS / "context-readout.py", "context_readout")
    config = tmp_path / "config.yaml"
    config.write_text("""models:
  model:
    cmd: |
      server -c 786432 --parallel 3 # old -c 100
    aliases: [alias]
  other:
    cmd: server --ctx-size=8192 -np 2
""")
    contexts, aliases = module.configured_ctx(str(config))
    assert contexts == {"model": 262144, "other": 4096}
    assert aliases == {"alias": "model"}
