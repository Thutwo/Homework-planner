# canvas_sync.py
import os, requests, datetime

BASE_URL = os.getenv("CANVAS_BASE_URL")  # e.g. https://yourcampus.instructure.com
TOKEN    = os.getenv("CANVAS_TOKEN")    # get your token thru setting page in your canvas

def _api_get(path, params=None):
    if not BASE_URL or not TOKEN:
        raise RuntimeError("Set CANVAS_BASE_URL and CANVAS_TOKEN env vars.")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"{BASE_URL}{path}"
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def list_courses():
    # Only active, enrolled courses
    return _api_get("/api/v1/courses", params={"enrollment_state":"active","per_page":100})

def fetch_planner_items(start=None, end=None):
    """
    Pulls upcoming items shown in Canvas Planner (assignments, quizzes, etc).
    """
    if start is None:
        start = datetime.datetime.utcnow()
    if end is None:
        end = start + datetime.timedelta(days=30)

    params = {
        "start_date": start.isoformat() + "Z",
        "end_date": end.isoformat() + "Z",
        "per_page": 100
    }
    return _api_get("/api/v1/planner/items", params=params)

def to_local_tasks(planner_items):
    """
    Convert Canvas planner items to your app's task dicts:
      { task, due, done, course }
    """
    tasks = []
    for it in planner_items:
        # Common fields
        title = it.get("plannable", {}).get("title") or it.get("title") or "Untitled"
        due = it.get("plannable", {}).get("due_at") or it.get("plannable_date")
        course_name = None
        if it.get("context_type") == "Course":
            course_name = it.get("context_name")

        tasks.append({
            "task": title,
            "due": due,          # ISO string; you can format later
            "done": False,       # you control completion locally
            "course": course_name
        })
    return tasks
