import os, json
from datetime import datetime

class RunLogger:
    def __init__(self, root_dir: str = "."):
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        self.run_id = f"run-{ts}"
        self.started_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        self.run_dir = os.path.join(root_dir, "artifacts", self.run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self._steps = []
        self._meta = {}

    def set_context(self, **kwargs):
        self._meta.update(kwargs)

    def info(self, msg: str):
        print(f"[INFO] {msg}")

    def warn(self, msg: str):
        print(f"[WARN] {msg}")

    def error(self, msg: str):
        print(f"[ERROR] {msg}")

    def step(self, filename: str, status: str, details=None):
        entry = {"file": filename, "status": status}
        if isinstance(details, dict):
            entry.update(details)
            to_write = json.dumps(details, indent=2)
        else:
            if details:
                entry["message"] = str(details)
            to_write = str(details) if details else status
        self._steps.append(entry)
        safe_name = filename.replace("/", "_")
        with open(os.path.join(self.run_dir, f"{safe_name}.log"), "w", encoding="utf-8") as f:
            f.write(to_write)

    def finalize(self, ok: bool):
        finished_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        summary = {
            "ok": ok,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": finished_at,
            **self._meta,
            "steps": self._steps,
        }
        with open(os.path.join(self.run_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        self.info(f"Evidence saved to: {self.run_dir}")
