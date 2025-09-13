#!/usr/bin/env python3
import os, sys, argparse
from scripts.lib.discovery import plan
from scripts.lib.logging_utils import RunLogger
from scripts.lib.executor import get_connection, execute_file
from scripts.lib.errors import DiscoveryError, ExecutionError

def _env_summary():
    keys = ["ENVIRONMENT", "SCHEMA_NAME"]
    out = {}
    for k in keys:
        v = os.environ.get(k)
        if v:
            out[k] = v
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        out["git_sha"] = sha[:12]
    return out

def main():
    p = argparse.ArgumentParser(description="Run SQL files against Redshift (batch transaction)")
    p.add_argument("--sql-path", required=True, help="Path to .sql file or folder of .sql files")
    p.add_argument("--execution-order", default="", help="Comma-separated filenames when sql-path is a folder")
    p.add_argument("--out-dir", default="", help="Directory to write run artifacts (evidence.json, logs, etc.)")
    args = p.parse_args()

    # Normalize and prepare output directory
    out_dir = args.out_dir.strip()
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        logger = RunLogger(root_dir=out_dir)
    else:
        # Fallback to previous behavior (whatever RunLogger uses by default)
        logger = RunLogger(root_dir="")

    try:
        mode, files = plan(args.sql_path, args.execution_order or "")
        if not files:
            raise DiscoveryError("No SQL files discovered.")
        logger.set_context(mode=mode, files=files, env_summary=_env_summary())
        logger.info(f"Mode: {mode} — {len(files)} file(s) to execute")
        if out_dir:
            logger.info(f"Artifacts directory: {os.path.abspath(out_dir)}")
    except Exception as e:
        logger.error(str(e))
        logger.finalize(False)
        sys.exit(2)

    ok = True
    try:
        with get_connection() as conn:
            conn.autocommit = False
            try:
                for path in files:
                    name = os.path.basename(path)
                    try:
                        logger.info(f"Executing: {name}")
                        res = execute_file(conn, path)  # returns dict with message/metrics
                        logger.step(name, "success", res)
                    except Exception as e:
                        logger.error(f"{name} failed: {e}")
                        logger.step(name, "failed", {"message": str(e)})
                        ok = False
                        raise
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                if ok:
                    ok = False
    finally:
        logger.finalize(ok)

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
