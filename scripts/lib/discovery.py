import os
from typing import List, Tuple

def is_sql_file(path: str) -> bool:
    return os.path.isfile(path) and path.lower().endswith(".sql")

def discover_from_folder(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")
    files = [f for f in os.listdir(folder) if f.lower().endswith(".sql")]
    def sort_key(name: str):
        head = name.split('_', 1)[0]
        return (int(head) if head.isdigit() else 999999, name.lower())
    files.sort(key=sort_key)
    return [os.path.join(folder, f) for f in files]

def validate_execution_order(folder: str, order_csv: str) -> List[str]:
    names = [n.strip() for n in order_csv.split(',') if n.strip()]
    if not names:
        return []
    paths = [os.path.join(folder, n) for n in names]
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        raise FileNotFoundError(f"execution_order references missing files: {missing}")
    return paths

def plan(sql_path: str, execution_order: str) -> Tuple[str, list]:
    sql_path = sql_path.strip()
    if is_sql_file(sql_path):
        return ("file", [sql_path])
    # assume folder
    if not os.path.isdir(sql_path):
        raise FileNotFoundError(f"Path not found: {sql_path}")
    if execution_order and execution_order.strip():
        return ("folder_explicit", validate_execution_order(sql_path, execution_order))
    return ("folder_auto", discover_from_folder(sql_path))
