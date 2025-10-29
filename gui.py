import tkinter as tk
from tkinter import messagebox
from planner import load_data, save_data

def refresh_list():
    listbox.delete(0, tk.END)
    for i, t in enumerate(load_data()):
        status = "✅" if t["done"] else "⏳"
        listbox.insert(tk.END, f"{i+1}. {t['task']} (Due: {t['due']}) {status}")

def add_task():
    task = task_entry.get()
    due = due_entry.get()
    if not task or not due:
        messagebox.showwarning("Warning", "Please fill out both fields.")
        return
    tasks = load_data()
    tasks.append({"task": task, "due": due, "done": False})
    save_data(tasks)
    task_entry.delete(0, tk.END)
    due_entry.delete(0, tk.END)
    refresh_list()

def mark_done():
    sel = listbox.curselection()
    if not sel:
        messagebox.showinfo("Info", "Select a task first.")
        return
    idx = sel[0]
    tasks = load_data()
    tasks[idx]["done"] = True
    save_data(tasks)
    refresh_list()

def remove_task():
    sel = listbox.curselection()
    if not sel:
        messagebox.showinfo("Info", "Select a task first.")
        return
    idx = sel[0]
    tasks = load_data()
    del tasks[idx]
    save_data(tasks)
    refresh_list()

root = tk.Tk()
root.title("Homework Planner 📝")
root.geometry("400x400")

tk.Label(root, text="Task:").pack()
task_entry = tk.Entry(root, width=40)
task_entry.pack()

tk.Label(root, text="Due Date:").pack()
due_entry = tk.Entry(root, width=45)
due_entry.pack()

tk.Button(root, text="Add Task", command=add_task).pack(pady=5)
tk.Button(root, text="Mark Complete", command=mark_done).pack(pady=5)
tk.Button(root, text="Remove", command=remove_task).pack(pady=5)

listbox = tk.Listbox(root, width=50)
listbox.pack(pady=10)

refresh_list()
root.mainloop()
