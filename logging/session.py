import datetime
import json
import os
import threading
import uuid


class SessionLogger:
    def __init__(self, config: dict):
        self.session_dir = config.get("logging", {}).get(
            "session_dir", "/var/log/kafka-os/sessions")
        self.intel_log = config.get("logging", {}).get(
            "intelligence_log", "/var/log/kafka-os/intelligence.jsonl")
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.intel_log), exist_ok=True)
        self._lock = threading.Lock()
        self._sessions = {}

    def _ts(self):
        return datetime.datetime.utcnow().isoformat() + "Z"

    def start_session(self, username, remote_ip):
        session_id = str(uuid.uuid4())[:8]
        path = os.path.join(self.session_dir, f"{session_id}_{username}_{remote_ip}.jsonl")
        with self._lock:
            self._sessions[(username, remote_ip)] = {
                "id": session_id,
                "path": path,
                "start": self._ts(),
                "commands": [],
                "credentials_tried": [],
            }
        self._write_event(username, remote_ip, "session_start", {
            "username": username,
            "remote_ip": remote_ip,
        })

    def end_session(self, username):
        for key in list(self._sessions):
            if key[0] == username:
                session = self._sessions[key]
                self._write_event(username, key[1], "session_end", {
                    "duration_commands": len(session.get("commands", [])),
                })
                self._flush_intel(session, key[1])
                with self._lock:
                    del self._sessions[key]
                break

    def log_input(self, username, text):
        self._write_event(username, None, "input", {"text": text})
        # Credential detection heuristic
        lower = text.lower()
        if any(k in lower for k in ("password", "passwd", "pass", "secret", "key", "token")):
            self._record_intel(username, "potential_credential", text)
        session = self._get_session(username)
        if session:
            session["commands"].append(text)

    def log_output(self, username, text):
        self._write_event(username, None, "output", {"text": text[:200]})

    def _get_session(self, username):
        with self._lock:
            for key, val in self._sessions.items():
                if key[0] == username:
                    return val
        return None

    def _write_event(self, username, remote_ip, event_type, data):
        session = self._get_session(username)
        if not session:
            return
        entry = {
            "ts": self._ts(),
            "event": event_type,
            "session_id": session["id"],
            **data,
        }
        try:
            with open(session["path"], "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def _record_intel(self, username, intel_type, value):
        session = self._get_session(username)
        entry = {
            "ts": self._ts(),
            "type": intel_type,
            "username": username,
            "session_id": session["id"] if session else "unknown",
            "value": value,
        }
        try:
            with open(self.intel_log, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def _flush_intel(self, session, remote_ip):
        if session.get("commands"):
            entry = {
                "ts": self._ts(),
                "type": "session_summary",
                "session_id": session["id"],
                "remote_ip": remote_ip,
                "command_count": len(session["commands"]),
                "commands": session["commands"][-50:],
            }
            try:
                with open(self.intel_log, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception:
                pass
