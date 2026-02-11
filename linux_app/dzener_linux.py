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
import textwrap
import time
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


def main() -> None:
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
