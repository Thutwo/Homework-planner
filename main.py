# main.py
from planner import *

def main():
    while True:
        print("\n=== Homework Planner ===")
        print("1. Add Task")
        print("2. View Tasks")
        print("3. Mark Complete")
        print("4. Quit")

        choice = input("Choose: ")

        if choice == "1":
            add_task()
        elif choice == "2":
            view_tasks()
        elif choice == "3":
            mark_complete()
        elif choice == "4":
            print("Good luck studying! 📚")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
