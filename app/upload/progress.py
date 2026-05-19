# app/upload/progress.py

from app.upload.task_store import task_progress

def update_progress(task_id: str, **kwargs):
    old = task_progress.get(task_id, {})

    new = {**old, **kwargs}

    if old == new:
        return

    task_progress[task_id] = new


def get_progress(task_id: str):
    return task_progress.get(task_id)