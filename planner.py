import json
FILE = "data.json"

def load_data():
    try:
        with open(FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []  # handle empty file
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(tasks):
    with open(FILE, "w") as f:
        json.dump(tasks, f, indent=2)

def add_task():
    task = input("Enter your homework: ")
    due = input("Due date (e.g. 10/10): ")
    tasks = load_data()
    tasks.append({"task": task, "due": due, "done": False})
    save_data(tasks)
    print("Task added!")

def view_tasks():
    tasks = load_data()
    if not tasks:
        print("No tasks yet!")
        return
    for i, t in enumerate(tasks):
        status = "Done" if t["done"] else "Pending"
        print(f"{i+1}. {t['task']} (Due: {t['due']}) {status}")

def mark_complete():
    view_tasks()
    tasks = load_data()
    num = int(input("Enter task number to mark complete: "))
    tasks[num-1]["done"] = True
    save_data(tasks)
    print("Task completed!")
