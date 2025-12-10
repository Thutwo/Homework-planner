import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
import datetime
from db import (
    init_db,
    create_user,
    verify_user,
    list_tasks,
    add_task,
    mark_done,
    add_task_if_not_exists,
    delete_task,
)
from canvas_sync import fetch_planner_items, to_local_tasks


# --- Login window ---
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Homework Planner – Login")
        self.geometry("320x220")

        tk.Label(self, text="Username").pack(pady=4)
        self.u = tk.Entry(self, width=30)
        self.u.pack()

        tk.Label(self, text="Password").pack(pady=4)
        self.p = tk.Entry(self, width=30, show="*")
        self.p.pack()

        btns = tk.Frame(self)
        btns.pack(pady=12)
        tk.Button(btns, text="Login", width=10, command=self.do_login).grid(
            row=0, column=0, padx=5
        )
        tk.Button(btns, text="Register", width=10, command=self.do_register).grid(
            row=0, column=1, padx=5
        )

    def do_register(self):
        user, pw = self.u.get().strip(), self.p.get()
        if not user or not pw:
            messagebox.showwarning("Missing", "Enter username and password.")
            return
        if create_user(user, pw):
            messagebox.showinfo("Success", "Account created. You can log in now.")
        else:
            messagebox.showerror("Oops", "Username already exists.")

    def do_login(self):
        user, pw = self.u.get().strip(), self.p.get()
        uid = verify_user(user, pw)
        if uid is None:
            messagebox.showerror("Login failed", "Invalid credentials.")
            return
        self.destroy()
        PlannerWindow(uid).mainloop()


# --- Planner window (per-user) ---
class PlannerWindow(tk.Tk):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.title("Homework Planner 📝")
        self.geometry("520x520")
        # NEW: remember notifications so we don't spam
        self.notification_state = {}  # {task_id: set([threshold_seconds, ...])}

        # --- background state ---
        self.bg_color = "#f0f0f0"  # default window color
        self.bg_image = None       # keep reference to PhotoImage

        # background label that sits behind everything
        self.background_label = tk.Label(self, bg=self.bg_color)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.lower()  # send behind other widgets

        self.configure(bg=self.bg_color)

        # --- menu bar for appearance ---
        menubar = tk.Menu(self)
        appearance_menu = tk.Menu(menubar, tearoff=0)
        appearance_menu.add_command(
            label="Change Background Color...", command=self.change_bg_color
        )
        appearance_menu.add_command(
            label="Set Background Image...", command=self.change_bg_image
        )
        appearance_menu.add_command(
            label="Clear Background Image", command=self.clear_bg_image
        )
        menubar.add_cascade(label="Appearance", menu=appearance_menu)
        self.config(menu=menubar)

        # --- Clock + countdown area ---
        top_bar = tk.Frame(self, bg=self.bg_color)
        top_bar.pack(pady=4)

        self.clock_label = tk.Label(
            top_bar, text="Time: --:--:--", font=("Arial", 11, "bold"), bg=self.bg_color
        )
        self.clock_label.pack()

        self.countdown_label = tk.Label(
            self,
            text="Next due: (none)",
            font=("Arial", 11),
            bg=self.bg_color,
        )
        self.countdown_label.pack(pady=2)

        # --- Form for adding tasks ---
        self.form = tk.Frame(self, bg=self.bg_color)
        self.form.pack(pady=6)

        tk.Label(self.form, text="Task", bg=self.bg_color).grid(row=0, column=0, sticky="e")
        self.task_e = tk.Entry(self.form, width=35)
        self.task_e.grid(row=0, column=1, padx=6)

        tk.Label(self.form, text="Due", bg=self.bg_color).grid(row=1, column=0, sticky="e")
        self.due_e = tk.Entry(self.form, width=35)
        self.due_e.grid(row=1, column=1, padx=6)

        tk.Button(self, text="Add Task", command=self.on_add).pack(pady=6)

        # Canvas Sync Button
        tk.Button(self, text="Sync from Canvas", command=self.on_sync).pack(pady=4)

        # --- List of tasks ---
        self.listbox = tk.Listbox(self, width=60, height=16)
        self.listbox.pack(pady=8)

        tk.Button(self, text="Mark Complete", command=self.on_done).pack(pady=4)
        tk.Button(self, text="Remove Task", command=self.on_remove).pack(pady=4)

        self.refresh()
        self.update_clock_and_countdown()  # start the ticking

    # ---------- Appearance / Background ----------


    def change_bg_color(self):
        """Let the user pick a background color."""
        color = colorchooser.askcolor(initialcolor=self.bg_color)[1]
        if not color:
            return
        self.bg_color = color
        # window + background
        self.configure(bg=color)
        self.background_label.config(bg=color)

        # some key frames/labels
        self.form.config(bg=color)
        self.clock_label.config(bg=color)
        self.countdown_label.config(bg=color)

    def change_bg_image(self):
        """Let the user choose an image file as wallpaper."""
        path = filedialog.askopenfilename(
            title="Choose background image",
            filetypes=[
                ("Image files", "*.png *.gif *.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            # Tk's PhotoImage works best with PNG/GIF;
            # JPG might fail unless you install Pillow.
            img = tk.PhotoImage(file=path)
        except Exception as e:
            messagebox.showerror(
                "Image Error",
                f"Could not load image.\nTry a PNG or GIF file.\n\nDetails:\n{e}",
            )
            return

        self.bg_image = img  # keep reference
        self.background_label.config(image=self.bg_image)

    def clear_bg_image(self):
        """Remove any custom background image."""
        self.bg_image = None
        self.background_label.config(image="", bg=self.bg_color)

    # ---------- Clock + countdown ----------

    def update_clock_and_countdown(self):
        """Update the running clock and countdown every second and fire reminders."""
        now = datetime.datetime.now()
        # Clock display (full date + time)
        self.clock_label.config(text=now.strftime("Time: %Y-%m-%d %H:%M:%S"))

        # thresholds in seconds: (seconds_before_due, label)
        thresholds = [
            (24 * 3600, "1 day"),
            (12 * 3600, "12 hours"),
            (6 * 3600, "6 hours"),
            (3 * 3600, "3 hours"),
            (1 * 3600, "1 hour"),
        ]

        # Find closest upcoming due date for countdown
        rows = list_tasks(self.user_id)

        next_task_title = None
        next_due_dt = None

        for tid, title, due, done in rows:
            if done:
                continue
            if not due or due.lower() == "no due date":
                continue

            dt = self._parse_due_datetime(due)
            if dt is None:
                continue

            delta = dt - now
            seconds_left = int(delta.total_seconds())
            if seconds_left <= 0:
                continue  # already past

            # 1) Use this for the "closest due" countdown
            if next_due_dt is None or dt < next_due_dt:
                next_due_dt = dt
                next_task_title = title

            # 2) Check if we should pop a reminder for this task
            self._check_notifications_for_task(tid, title, dt, seconds_left, thresholds)

        if next_due_dt is None:
            self.countdown_label.config(text="Next due: (no upcoming tasks)")
        else:
            delta = next_due_dt - now
            total_seconds = int(delta.total_seconds())
            days = total_seconds // (24 * 3600)
            rem = total_seconds % (24 * 3600)
            hours = rem // 3600
            rem = rem % 3600
            minutes = rem // 60
            seconds = rem % 60
            self.countdown_label.config(
                text=f"Next due: {next_task_title} in {days}d {hours:02}h {minutes:02}m {seconds:02}s"
            )

        # schedule this function again in 1000 ms
        self.after(1000, self.update_clock_and_countdown)

    def _check_notifications_for_task(self, tid, title, due_dt, seconds_left, thresholds):
        """
        Show a reminder popup when a task is around 1d / 12h / 6h / 3h / 1h left.
        Each threshold fires only once per task.
        """
        fired = self.notification_state.setdefault(tid, set())

        for secs, label in thresholds:
            # "Window" of about 1 minute around the threshold
            if secs - 60 <= seconds_left <= secs + 60 and secs not in fired:
                fired.add(secs)
                messagebox.showinfo(
                    "Deadline reminder",
                    f'"{title}" is due in about {label}.\n'
                    f"Due at: {due_dt.strftime('%Y-%m-%d %H:%M')}",
                )

    def _parse_due_datetime(self, due_str: str):
        """Best-effort parse for due date strings, converting Canvas UTC to local time."""
        s = due_str.strip()

        # Local timezone (whatever your OS is set to, e.g. PST/PDT)
        local_tz = datetime.datetime.now().astimezone().tzinfo

        # Case 1: Canvas ISO with 'Z' (UTC), e.g. "2025-12-10T07:59:00Z"
        if s.endswith("Z"):
            try:
                # fromisoformat can't handle 'Z' directly in older Python,
                # so replace it with +00:00 (UTC)
                aware_utc = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
                local_dt = aware_utc.astimezone(local_tz)
                # Return naive local datetime (no tzinfo) so we can compare
                return local_dt.replace(tzinfo=None)
            except Exception:
                pass

        # Case 2: string already has an offset like "+00:00" or "-08:00"
        # fromisoformat will give us an aware datetime; convert to local
        try:
            dt = datetime.datetime.fromisoformat(s)
            if dt.tzinfo is not None:
                local_dt = dt.astimezone(local_tz)
                return local_dt.replace(tzinfo=None)
        except Exception:
            pass

        # Case 3: Manual local formats the user might type (no timezone info)
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.datetime.strptime(s, fmt)
            except Exception:
                continue

        return None
    # ---------- Task management ----------

    def refresh(self):
        self.listbox.delete(0, tk.END)
        rows = list_tasks(self.user_id)
        for tid, title, due, done in rows:
            status = "✅" if done else "⏳"
            self.listbox.insert(tk.END, f"[{tid}] {title} (Due: {due}) {status}")

    def on_add(self):
        title = self.task_e.get().strip()
        due = self.due_e.get().strip()
        if not title or not due:
            messagebox.showwarning("Missing", "Please enter both Task and Due.")
            return
        add_task(self.user_id, title, due)
        self.task_e.delete(0, tk.END)
        self.due_e.delete(0, tk.END)
        self.refresh()

    def on_done(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a task first.")
            return

        line = self.listbox.get(sel[0])
        try:
            tid = int(line.split("]")[0].strip("["))
        except Exception:
            messagebox.showerror("Error", "Could not parse task id.")
            return

        mark_done(self.user_id, tid)
        self.refresh()

    def on_remove(self):
        """Remove the selected task permanently."""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a task to remove.")
            return

        line = self.listbox.get(sel[0])
        try:
            tid = int(line.split("]")[0].strip("["))
        except Exception:
            messagebox.showerror("Error", "Could not parse task id.")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this task?\n\n{line}"
        )
        if confirm:
            delete_task(self.user_id, tid)
            self.refresh()

    def on_sync(self):
        """Sync tasks from Canvas into this user's task list."""
        try:
            items = fetch_planner_items()
            canvas_tasks = to_local_tasks(items)

            imported = 0
            for t in canvas_tasks:
                course = t.get("course") or ""
                base_title = t.get("task") or "Untitled"
                title = f"{course}: {base_title}" if course else base_title
                due = t.get("due") or "No due date"

                add_task_if_not_exists(self.user_id, title, due)
                imported += 1

            self.refresh()
            messagebox.showinfo(
                "Canvas Sync", f"Imported/updated about {imported} Canvas items."
            )
        except Exception as e:
            messagebox.showerror(
                "Canvas Sync Error", f"Could not sync from Canvas:\n{e}"
            )


if __name__ == "__main__":
    init_db()
    LoginWindow().mainloop()
