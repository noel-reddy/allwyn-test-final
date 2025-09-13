import os
import re
import time
import redshift_connector
from contextlib import contextmanager
from scripts.lib.errors import ExecutionError, DiscoveryError

class ConnectionConfigError(Exception):
    pass

_DESTRUCTIVE_RE = re.compile(r"\\b(DROP|TRUNCATE)\\b", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"\\{\\{([A-Z0-9_]+)\\}\\}")  # {{VAR}}

def _env(name: str, default=None):
    return os.environ.get(name, default)

def _require_env(name: str):
    v = _env(name)
    if not v:
        raise ConnectionConfigError(f"Missing environment variable: {name}")
    return v

def _substitute_env(sql_text: str) -> str:
    # Replace {{VAR}} with env values; raise if missing
    missing = set()
    def repl(m):
        var = m.group(1)
        val = os.environ.get(var)
        if val is None:
            missing.add(var)
            return m.group(0)
        return str(val)
    out = _PLACEHOLDER_RE.sub(repl, sql_text)
    if missing:
        raise ExecutionError(f"Missing template variables in environment: {sorted(missing)}")
    return out

def _policy_check(sql_text: str):
    env = (os.environ.get("ENVIRONMENT") or "").lower()
    allow = (os.environ.get("ALLOW_DESTRUCTIVE") or "").lower() == "true"
    if env == "prod" and not allow:
        if _DESTRUCTIVE_RE.search(sql_text):
            raise ExecutionError("Policy block: destructive statements (DROP/TRUNCATE) not allowed in prod. Set ALLOW_DESTRUCTIVE=true to override with CAB approval.")

@contextmanager
def get_connection():
    host = _require_env("REDSHIFT_HOST")
    port = int(_env("REDSHIFT_PORT", "5439"))
    database = _require_env("REDSHIFT_DB")
    user = _require_env("REDSHIFT_USER")
    password = _require_env("REDSHIFT_PASSWORD")
    attempts = int(_env("CONNECT_RETRIES", "3"))
    delay = float(_env("CONNECT_RETRY_DELAY", "1.5"))

    last_err = None
    for i in range(1, attempts + 1):
        try:
            conn = redshift_connector.connect(
                host=host, port=port, database=database, user=user, password=password, ssl=True
            )
            yield conn
            try:
                conn.close()
            except Exception:
                pass
            return
        except Exception as e:
            last_err = e
            if i < attempts:
                time.sleep(delay)
            else:
                raise
    if last_err:
        raise last_err

def _split_sql(sql_text: str):
    # Split on ';' not inside single quotes. Minimal but reliable for demo.
    parts, stmt, in_str, esc = [], [], False, False
    for ch in sql_text:
        if ch == "'" and not esc:
            in_str = not in_str
        if ch == ";" and not in_str:
            parts.append(''.join(stmt).strip())
            stmt = []
        else:
            stmt.append(ch)
        esc = (ch == "\\" and not esc)
    tail = ''.join(stmt).strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p and not p.isspace()]

def execute_file(conn, path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw_sql = f.read()

    # Parameter substitution and policy checks at the file level
    sql = _substitute_env(raw_sql)
    _policy_check(sql)

    cur = conn.cursor()
    rows_total = 0
    t0 = time.monotonic()
    try:
        statements = _split_sql(sql)
        if not statements:
            return {"message": "SKIPPED (empty file)", "statements_count": 0, "rows_affected_total": 0, "elapsed_ms": 0}
        for s in statements:
            cur.execute(s)
            try:
                rc = cur.rowcount
                if isinstance(rc, int) and rc >= 0:
                    rows_total += rc
            except Exception:
                pass
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {"message": f"OK ({len(statements)} statements)", "statements_count": len(statements), "rows_affected_total": rows_total, "elapsed_ms": elapsed_ms}
    except Exception as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        # Return minimal info; runner will mark failed and handle rollback
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
