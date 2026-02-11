#!/usr/bin/env python3
"""Dzener Linux Edition (community reimplementation).

A small local app that mirrors the workflow described in the Windows build:
- submit links for promotion
- auto-process other users' tasks
- receive points for each completed action
"""

from __future__ import annotations

import json
import random
import argparse
import textwrap
import time
import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

DATA_DIR = Path.home() / ".dzener-linux"
DATA_FILE = DATA_DIR / "state.json"
POINTS_PER_TASK = 2


@dataclass
class Task:
    url: str
    kind: str  # article | video
    desired_actions: List[str]
    owner: str


@dataclass
class UserState:
    nickname: str
    points: int
    submitted_tasks: List[Task]
    completed_tasks: int


def _default_state() -> UserState:
    return UserState(nickname="linux-user", points=0, submitted_tasks=[], completed_tasks=0)


def load_state() -> UserState:
    if not DATA_FILE.exists():
        return _default_state()

    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    tasks = [Task(**task) for task in raw.get("submitted_tasks", [])]
    return UserState(
        nickname=raw.get("nickname", "linux-user"),
        points=int(raw.get("points", 0)),
        submitted_tasks=tasks,
        completed_tasks=int(raw.get("completed_tasks", 0)),
    )


def save_state(state: UserState) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_header(state: UserState) -> None:
    print("\n" + "=" * 58)
    print("Dzener Linux Edition — локальный клиент обмена активностью")
    print("=" * 58)
    print(f"Пользователь: {state.nickname}")
    print(f"Баланс: {state.points} баллов")
    print(f"Выполнено задач: {state.completed_tasks}")
    print("=" * 58 + "\n")


def validate_url(url: str) -> bool:
    prefixes = ("https://dzen.ru/", "https://zen.yandex.ru/", "https://")
    return url.startswith(prefixes) and "." in url


def input_actions() -> List[str]:
    actions_catalog = {
        "1": "дочитывание/досмотр",
        "2": "лайк",
        "3": "дизлайк",
        "4": "подписка",
        "5": "сохранение в закладки",
        "6": "комментарий",
        "7": "лайк/дизлайк комментария",
    }
    print("Выберите действия через запятую (например 1,2,4):")
    for code, title in actions_catalog.items():
        print(f"  {code}. {title}")

    selected = input("> ").strip()
    codes = [item.strip() for item in selected.split(",") if item.strip()]
    actions = [actions_catalog[c] for c in codes if c in actions_catalog]
    return actions or ["дочитывание/досмотр"]


def add_task(state: UserState) -> None:
    url = input("Введите ссылку на публикацию/видео Дзена: ").strip()
    if not validate_url(url):
        print("❌ Некорректный URL. Попробуйте снова.")
        return

    kind = input("Тип материала (article/video): ").strip().lower()
    if kind not in {"article", "video"}:
        kind = "article"

    actions = input_actions()
    state.submitted_tasks.append(Task(url=url, kind=kind, desired_actions=actions, owner=state.nickname))
    save_state(state)
    print("✅ Материал добавлен в очередь обмена активностью.")


def generate_exchange_tasks() -> List[Task]:
    demo_urls = [
        "https://dzen.ru/a/demo_article_1",
        "https://dzen.ru/video/watch/demo_2",
        "https://zen.yandex.ru/media/demo_3",
        "https://dzen.ru/a/demo_article_4",
    ]
    users = ["alice", "bob", "charlie", "mike"]
    pool = []
    for _ in range(6):
        url = random.choice(demo_urls)
        pool.append(
            Task(
                url=url,
                kind="video" if "video" in url else "article",
                desired_actions=["дочитывание/досмотр", random.choice(["лайк", "подписка", "сохранение в закладки"])],
                owner=random.choice(users),
            )
        )
    return pool


def emulate_view(task: Task) -> None:
    duration_min = random.randint(1, 3)
    print(f"\n▶ Обработка: {task.url}")
    print(f"  Автор задания: {task.owner}")
    print(f"  Тип: {task.kind}")
    print(f"  Действия: {', '.join(task.desired_actions)}")
    print(f"  Эмуляция вовлеченности: {duration_min} мин")
    time.sleep(0.5)


def process_tasks(state: UserState) -> None:
    tasks = generate_exchange_tasks()
    print(f"Найдено {len(tasks)} заданий для выполнения.\n")
    processed = 0
    for task in tasks:
        emulate_view(task)
        state.points += POINTS_PER_TASK
        state.completed_tasks += 1
        processed += 1
        print(f"  +{POINTS_PER_TASK} балла начислено. Текущий баланс: {state.points}")

    save_state(state)
    print(f"\n✅ Выполнено заданий: {processed}. Баланс обновлен.")


def show_my_tasks(state: UserState) -> None:
    if not state.submitted_tasks:
        print("У вас пока нет добавленных материалов.")
        return

    print("\nВаши материалы в очереди:")
    for i, task in enumerate(state.submitted_tasks, start=1):
        print(f"{i}. [{task.kind}] {task.url}")
        print(f"   Действия: {', '.join(task.desired_actions)}")


def show_about() -> None:
    text = """
    Dzener Linux Edition — независимая Linux-реализация логики обмена действиями.

    Возможности:
    - добавление ссылок на статьи/видео;
    - автоматическая обработка общей очереди задач;
    - начисление баллов (+2 за задание);
    - сохранение локальной статистики в ~/.dzener-linux/state.json.
    """
    print(textwrap.dedent(text).strip())


class DzenerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Dzener Linux Edition")
        self.root.geometry("780x560")

        self.state = load_state()
        self.actions_vars: dict[str, tk.BooleanVar] = {}
        self.status_var = tk.StringVar()

        self._build_ui()
        self.refresh_header()
        self.refresh_my_tasks()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)

        header = ttk.Label(frame, text="Dzener Linux Edition — графический интерфейс", font=("Arial", 13, "bold"))
        header.pack(anchor="w")

        self.info_label = ttk.Label(frame, text="")
        self.info_label.pack(anchor="w", pady=(6, 12))

        add_box = ttk.LabelFrame(frame, text="Добавление материала", padding=10)
        add_box.pack(fill="x")

        ttk.Label(add_box, text="Ссылка:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(add_box, width=80)
        self.url_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=8)

        ttk.Label(add_box, text="Тип:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.kind_var = tk.StringVar(value="article")
        kind_box = ttk.Frame(add_box)
        kind_box.grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Radiobutton(kind_box, text="article", value="article", variable=self.kind_var).pack(side="left")
        ttk.Radiobutton(kind_box, text="video", value="video", variable=self.kind_var).pack(side="left", padx=(12, 0))

        actions_catalog = [
            "дочитывание/досмотр",
            "лайк",
            "дизлайк",
            "подписка",
            "сохранение в закладки",
            "комментарий",
            "лайк/дизлайк комментария",
        ]
        ttk.Label(add_box, text="Действия:").grid(row=2, column=0, sticky="nw", pady=(8, 0))
        actions_frame = ttk.Frame(add_box)
        actions_frame.grid(row=2, column=1, columnspan=3, sticky="w", pady=(8, 0))
        for idx, action in enumerate(actions_catalog):
            var = tk.BooleanVar(value=(idx == 0))
            self.actions_vars[action] = var
            ttk.Checkbutton(actions_frame, text=action, variable=var).grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 14))

        ttk.Button(add_box, text="Добавить материал", command=self.gui_add_task).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        add_box.columnconfigure(1, weight=1)

        actions_box = ttk.LabelFrame(frame, text="Операции", padding=10)
        actions_box.pack(fill="x", pady=(12, 0))
        ttk.Button(actions_box, text="Запустить автообработку", command=self.gui_process_tasks).pack(side="left")
        ttk.Button(actions_box, text="О программе", command=self.gui_show_about).pack(side="left", padx=8)

        tasks_box = ttk.LabelFrame(frame, text="Мои материалы", padding=10)
        tasks_box.pack(fill="both", expand=True, pady=(12, 0))

        self.tasks_text = tk.Text(tasks_box, wrap="word", height=12)
        self.tasks_text.pack(fill="both", expand=True)
        self.tasks_text.configure(state="disabled")

        status = ttk.Label(frame, textvariable=self.status_var)
        status.pack(anchor="w", pady=(8, 0))

    def refresh_header(self) -> None:
        self.info_label.config(
            text=(
                f"Пользователь: {self.state.nickname} | "
                f"Баланс: {self.state.points} баллов | "
                f"Выполнено задач: {self.state.completed_tasks}"
            )
        )

    def refresh_my_tasks(self) -> None:
        self.tasks_text.configure(state="normal")
        self.tasks_text.delete("1.0", "end")
        if not self.state.submitted_tasks:
            self.tasks_text.insert("end", "У вас пока нет добавленных материалов.\n")
        else:
            for idx, task in enumerate(self.state.submitted_tasks, start=1):
                self.tasks_text.insert("end", f"{idx}. [{task.kind}] {task.url}\n")
                self.tasks_text.insert("end", f"   Действия: {', '.join(task.desired_actions)}\n\n")
        self.tasks_text.configure(state="disabled")

    def selected_actions(self) -> List[str]:
        selected = [action for action, var in self.actions_vars.items() if var.get()]
        return selected or ["дочитывание/досмотр"]

    def gui_add_task(self) -> None:
        url = self.url_entry.get().strip()
        if not validate_url(url):
            messagebox.showerror("Ошибка", "Некорректный URL. Используйте https://...")
            return

        task = Task(
            url=url,
            kind=self.kind_var.get(),
            desired_actions=self.selected_actions(),
            owner=self.state.nickname,
        )
        self.state.submitted_tasks.append(task)
        save_state(self.state)

        self.url_entry.delete(0, "end")
        self.refresh_my_tasks()
        self.status_var.set("✅ Материал добавлен в очередь.")

    def gui_process_tasks(self) -> None:
        tasks = generate_exchange_tasks()
        processed = len(tasks)
        self.state.points += processed * POINTS_PER_TASK
        self.state.completed_tasks += processed
        save_state(self.state)

        self.refresh_header()
        self.status_var.set(f"✅ Выполнено заданий: {processed}, начислено {processed * POINTS_PER_TASK} баллов.")
        messagebox.showinfo("Автообработка завершена", f"Выполнено заданий: {processed}\nТекущий баланс: {self.state.points}")

    def gui_show_about(self) -> None:
        messagebox.showinfo(
            "О программе",
            textwrap.dedent(
                """
                Dzener Linux Edition — локальная Linux-реализация логики обмена действиями.

                Возможности:
                • добавление ссылок на статьи/видео;
                • автоматическая обработка очереди задач;
                • начисление баллов (+2 за задание);
                • сохранение статистики в ~/.dzener-linux/state.json.
                """
            ).strip(),
        )


def run_gui() -> None:
    root = tk.Tk()
    DzenerGUI(root)
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Dzener Linux Edition")
    parser.add_argument("--gui", action="store_true", help="Запустить графический интерфейс (Tkinter)")
    args = parser.parse_args()

    if args.gui:
        run_gui()
        return

    state = load_state()
    while True:
        print_header(state)
        print("1. Добавить публикацию/видео")
        print("2. Запустить автообработку заданий")
        print("3. Показать мои материалы")
        print("4. О программе")
        print("5. Выход")

        choice = input("\nВыберите действие: ").strip()
        if choice == "1":
            add_task(state)
        elif choice == "2":
            process_tasks(state)
        elif choice == "3":
            show_my_tasks(state)
        elif choice == "4":
            show_about()
        elif choice == "5":
            save_state(state)
            print("До свидания!")
            break
        else:
            print("Неизвестная команда.")

        input("\nНажмите Enter, чтобы продолжить...")


if __name__ == "__main__":
    main()
