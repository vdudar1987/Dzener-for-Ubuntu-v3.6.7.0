#!/usr/bin/env python3
"""Dzener Linux Edition (community reimplementation).

A local Linux app that mirrors the workflow described in the Windows build:
- submit links for promotion
- process exchange tasks
- receive points for each completed action
"""

from __future__ import annotations

import argparse
import json
import random
import textwrap
import time
import tkinter as tk
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any
from urllib.parse import urlparse

APP_VERSION = "3.7.0"
DATA_DIR = Path.home() / ".dzener-linux"
DATA_FILE = DATA_DIR / "state.json"
POINTS_PER_TASK = 2
EXCHANGE_TASK_COUNT = 6

ACTION_CATALOG = {
    "1": "дочитывание/досмотр",
    "2": "лайк",
    "3": "дизлайк",
    "4": "подписка",
    "5": "сохранение в закладки",
    "6": "комментарий",
    "7": "лайк/дизлайк комментария",
}
DEFAULT_ACTION = "дочитывание/досмотр"


@dataclass
class Task:
    url: str
    kind: str  # article | video
    desired_actions: list[str]
    owner: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserState:
    nickname: str
    points: int
    submitted_tasks: list[Task]
    completed_tasks: int
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProcessReport:
    processed: int
    points_added: int


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> UserState:
    return UserState(nickname="linux-user", points=0, submitted_tasks=[], completed_tasks=0)


def _load_json_state() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {}

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        corrupted = DATA_FILE.with_suffix(".corrupted.json")
        try:
            DATA_FILE.rename(corrupted)
        except OSError:
            pass
        return {}


def load_state() -> UserState:
    raw = _load_json_state()
    if not raw:
        return _default_state()

    tasks = []
    for task_raw in raw.get("submitted_tasks", []):
        try:
            tasks.append(
                Task(
                    url=task_raw["url"],
                    kind=task_raw.get("kind", "article"),
                    desired_actions=task_raw.get("desired_actions", [DEFAULT_ACTION]),
                    owner=task_raw.get("owner", raw.get("nickname", "linux-user")),
                    created_at=task_raw.get("created_at", _iso_now()),
                )
            )
        except KeyError:
            continue

    return UserState(
        nickname=raw.get("nickname", "linux-user"),
        points=max(0, int(raw.get("points", 0))),
        submitted_tasks=tasks,
        completed_tasks=max(0, int(raw.get("completed_tasks", 0))),
        last_updated=raw.get("last_updated", _iso_now()),
    )


def save_state(state: UserState) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state.last_updated = _iso_now()
    DATA_FILE.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def print_header(state: UserState) -> None:
    print("\n" + "=" * 62)
    print(f"Dzener Linux Edition v{APP_VERSION} — локальный клиент")
    print("=" * 62)
    print(f"Пользователь: {state.nickname}")
    print(f"Баланс: {state.points} баллов")
    print(f"Выполнено задач: {state.completed_tasks}")
    print(f"Последнее обновление: {state.last_updated}")
    print("=" * 62 + "\n")


def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False

    host = parsed.netloc.lower()
    return host.endswith("dzen.ru") or host.endswith("zen.yandex.ru")


def input_actions() -> list[str]:
    print("Выберите действия через запятую (например 1,2,4):")
    for code, title in ACTION_CATALOG.items():
        print(f"  {code}. {title}")

    selected = input("> ").strip()
    codes = [item.strip() for item in selected.split(",") if item.strip()]
    actions = [ACTION_CATALOG[c] for c in codes if c in ACTION_CATALOG]
    return actions or [DEFAULT_ACTION]


def add_task(state: UserState) -> None:
    url = input("Введите ссылку на публикацию/видео Дзена: ").strip()
    if not validate_url(url):
        print("❌ Некорректный URL. Нужна ссылка на dzen.ru или zen.yandex.ru (https).")
        return

    kind = input("Тип материала (article/video): ").strip().lower()
    if kind not in {"article", "video"}:
        kind = "article"

    actions = input_actions()
    state.submitted_tasks.append(Task(url=url, kind=kind, desired_actions=actions, owner=state.nickname))
    save_state(state)
    print("✅ Материал добавлен в очередь обмена активностью.")


def remove_task(state: UserState) -> None:
    if not state.submitted_tasks:
        print("Удалять нечего: список материалов пуст.")
        return

    show_my_tasks(state)
    raw_idx = input("Введите номер материала для удаления: ").strip()
    if not raw_idx.isdigit():
        print("❌ Номер должен быть целым числом.")
        return

    idx = int(raw_idx) - 1
    if idx < 0 or idx >= len(state.submitted_tasks):
        print("❌ Материал с таким номером не найден.")
        return

    removed = state.submitted_tasks.pop(idx)
    save_state(state)
    print(f"✅ Удалено: {removed.url}")


def generate_exchange_tasks(amount: int = EXCHANGE_TASK_COUNT) -> list[Task]:
    demo_urls = [
        "https://dzen.ru/a/demo_article_1",
        "https://dzen.ru/video/watch/demo_2",
        "https://zen.yandex.ru/media/demo_3",
        "https://dzen.ru/a/demo_article_4",
    ]
    users = ["alice", "bob", "charlie", "mike"]
    pool: list[Task] = []
    for _ in range(max(1, amount)):
        url = random.choice(demo_urls)
        pool.append(
            Task(
                url=url,
                kind="video" if "video" in url else "article",
                desired_actions=[DEFAULT_ACTION, random.choice(["лайк", "подписка", "сохранение в закладки"])],
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
    time.sleep(0.25)


def process_tasks(state: UserState, amount: int = EXCHANGE_TASK_COUNT, verbose: bool = True) -> ProcessReport:
    tasks = generate_exchange_tasks(amount=amount)
    if verbose:
        print(f"Найдено {len(tasks)} заданий для выполнения.\n")

    for task in tasks:
        if verbose:
            emulate_view(task)
        state.points += POINTS_PER_TASK
        state.completed_tasks += 1
        if verbose:
            print(f"  +{POINTS_PER_TASK} балла начислено. Текущий баланс: {state.points}")

    save_state(state)
    if verbose:
        print(f"\n✅ Выполнено заданий: {len(tasks)}. Баланс обновлен.")

    return ProcessReport(processed=len(tasks), points_added=len(tasks) * POINTS_PER_TASK)


def show_my_tasks(state: UserState) -> None:
    if not state.submitted_tasks:
        print("У вас пока нет добавленных материалов.")
        return

    print("\nВаши материалы в очереди:")
    for i, task in enumerate(state.submitted_tasks, start=1):
        print(f"{i}. [{task.kind}] {task.url}")
        print(f"   Действия: {', '.join(task.desired_actions)}")
        print(f"   Добавлено: {task.created_at}")


def export_tasks(state: UserState) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_file = DATA_DIR / "tasks_export.json"
    payload = [asdict(task) for task in state.submitted_tasks]
    export_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return export_file


def reset_progress(state: UserState) -> None:
    confirm = input("Сбросить баллы и статистику? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Сброс отменён.")
        return

    state.points = 0
    state.completed_tasks = 0
    save_state(state)
    print("✅ Баллы и статистика сброшены.")


def show_about() -> None:
    text = f"""
    Dzener Linux Edition v{APP_VERSION} — независимая Linux-реализация логики обмена действиями.

    Возможности:
    - добавление/удаление ссылок на статьи и видео;
    - автоматическая обработка очереди задач;
    - начисление баллов (+{POINTS_PER_TASK} за задание);
    - экспорт задач в JSON;
    - сохранение локальной статистики в {DATA_FILE}.
    """
    print(textwrap.dedent(text).strip())


class DzenerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Dzener Linux Edition v{APP_VERSION}")
        self.root.geometry("860x620")

        self.state = load_state()
        self.actions_vars: dict[str, tk.BooleanVar] = {}
        self.status_var = tk.StringVar()

        self._build_ui()
        self.refresh_header()
        self.refresh_my_tasks()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)

        header = ttk.Label(frame, text=f"Dzener Linux Edition v{APP_VERSION}", font=("Arial", 13, "bold"))
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

        ttk.Label(add_box, text="Действия:").grid(row=2, column=0, sticky="nw", pady=(8, 0))
        actions_frame = ttk.Frame(add_box)
        actions_frame.grid(row=2, column=1, columnspan=3, sticky="w", pady=(8, 0))
        for idx, action in enumerate(ACTION_CATALOG.values()):
            var = tk.BooleanVar(value=(idx == 0))
            self.actions_vars[action] = var
            ttk.Checkbutton(actions_frame, text=action, variable=var).grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 14))

        ttk.Button(add_box, text="Добавить материал", command=self.gui_add_task).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        add_box.columnconfigure(1, weight=1)

        actions_box = ttk.LabelFrame(frame, text="Операции", padding=10)
        actions_box.pack(fill="x", pady=(12, 0))
        ttk.Button(actions_box, text="Запустить автообработку", command=self.gui_process_tasks).pack(side="left")
        ttk.Button(actions_box, text="Экспорт задач", command=self.gui_export_tasks).pack(side="left", padx=8)
        ttk.Button(actions_box, text="О программе", command=self.gui_show_about).pack(side="left", padx=8)

        tasks_box = ttk.LabelFrame(frame, text="Мои материалы", padding=10)
        tasks_box.pack(fill="both", expand=True, pady=(12, 0))

        self.tasks_text = tk.Text(tasks_box, wrap="word", height=14)
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
                self.tasks_text.insert("end", f"   Действия: {', '.join(task.desired_actions)}\n")
                self.tasks_text.insert("end", f"   Добавлено: {task.created_at}\n\n")
        self.tasks_text.configure(state="disabled")

    def selected_actions(self) -> list[str]:
        selected = [action for action, var in self.actions_vars.items() if var.get()]
        return selected or [DEFAULT_ACTION]

    def gui_add_task(self) -> None:
        url = self.url_entry.get().strip()
        if not validate_url(url):
            messagebox.showerror("Ошибка", "Некорректный URL. Используйте https://dzen.ru/... или https://zen.yandex.ru/...")
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
        self.refresh_header()
        self.refresh_my_tasks()
        self.status_var.set("✅ Материал добавлен в очередь.")

    def gui_process_tasks(self) -> None:
        report = process_tasks(self.state, verbose=False)
        self.refresh_header()
        self.status_var.set(f"✅ Выполнено заданий: {report.processed}, начислено {report.points_added} баллов.")
        messagebox.showinfo("Автообработка завершена", f"Выполнено заданий: {report.processed}\nТекущий баланс: {self.state.points}")

    def gui_export_tasks(self) -> None:
        export_file = export_tasks(self.state)
        self.status_var.set(f"✅ Экспортировано в {export_file}")
        messagebox.showinfo("Экспорт завершён", f"Файл сохранён:\n{export_file}")

    def gui_show_about(self) -> None:
        messagebox.showinfo(
            "О программе",
            textwrap.dedent(
                f"""
                Dzener Linux Edition v{APP_VERSION} — локальная Linux-реализация логики обмена действиями.

                Возможности:
                • добавление и удаление ссылок на статьи/видео;
                • автоматическая обработка очереди задач;
                • начисление баллов (+{POINTS_PER_TASK} за задание);
                • экспорт задач в JSON;
                • сохранение статистики в {DATA_FILE}.
                """
            ).strip(),
        )


def run_gui() -> None:
    root = tk.Tk()
    DzenerGUI(root)
    root.mainloop()


def run_cli() -> None:
    state = load_state()
    while True:
        print_header(state)
        print("1. Добавить публикацию/видео")
        print("2. Запустить автообработку заданий")
        print("3. Показать мои материалы")
        print("4. Удалить мой материал")
        print("5. Экспортировать мои материалы в JSON")
        print("6. Сбросить баллы и статистику")
        print("7. О программе")
        print("8. Выход")

        choice = input("\nВыберите действие: ").strip()
        if choice == "1":
            add_task(state)
        elif choice == "2":
            process_tasks(state)
        elif choice == "3":
            show_my_tasks(state)
        elif choice == "4":
            remove_task(state)
        elif choice == "5":
            output = export_tasks(state)
            print(f"✅ Экспорт завершён: {output}")
        elif choice == "6":
            reset_progress(state)
        elif choice == "7":
            show_about()
        elif choice == "8":
            save_state(state)
            print("До свидания!")
            break
        else:
            print("Неизвестная команда.")

        input("\nНажмите Enter, чтобы продолжить...")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Dzener Linux Edition v{APP_VERSION}")
    parser.add_argument("--gui", action="store_true", help="Запустить графический интерфейс (Tkinter)")
    parser.add_argument("--process", type=int, metavar="N", help="Сразу выполнить N заданий и выйти")
    parser.add_argument("--version", action="store_true", help="Показать версию и выйти")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.version:
        print(APP_VERSION)
        return

    if args.process is not None:
        state = load_state()
        report = process_tasks(state, amount=args.process, verbose=False)
        print(f"Выполнено: {report.processed}, начислено: {report.points_added}, баланс: {state.points}")
        return

    if args.gui:
        run_gui()
        return

    run_cli()


if __name__ == "__main__":
    main()
