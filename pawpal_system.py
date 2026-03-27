from dataclasses import dataclass, field
from enum import Enum
from datetime import date
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class Category(Enum):
    FEEDING = "Feeding"
    WALKING = "Walking"
    GROOMING = "Grooming"


# ---------------------------------------------------------------------------
# Dataclasses  (pure data holders)
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    age: int
    breed: str


@dataclass
class Task:
    name: str
    duration: int          # minutes
    priority: int          # higher number = higher priority
    category: Category


@dataclass
class Preferences:
    preferred_time: str                        # e.g. "morning", "afternoon"
    priority_categories: List[Category] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Regular classes  (contain behaviour)
# ---------------------------------------------------------------------------

class DailyPlan:
    def __init__(self, plan_date: date):
        self.date: date = plan_date
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def generate_schedule(self) -> None:
        pass

    def view_plan(self) -> List[Task]:
        pass


class Scheduler:
    def __init__(self):
        self.plans: List[DailyPlan] = []

    def create_daily_plan(self, plan_date: date) -> DailyPlan:
        pass

    def handle_conflict(self, task: Task) -> None:
        pass

    def adjust_plan(self, plan: DailyPlan) -> None:
        pass


class Owner:
    def __init__(self, name: str, owner_info: str, preferences: Preferences):
        self.name: str = name
        self.owner_info: str = owner_info
        self.preferences: Preferences = preferences
        self.pets: List[Pet] = []
        self.scheduler: Scheduler = Scheduler()

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet: Pet) -> None:
        pass

    def schedule_task(self, task: Task) -> None:
        pass

    def cancel_task(self, task: Task) -> None:
        pass

    def view_schedule(self) -> Optional[DailyPlan]:
        pass


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    prefs = Preferences(preferred_time="morning", priority_categories=[Category.FEEDING, Category.WALKING])
    pet = Pet(name="Mochi", age=3, breed="Shiba Inu")
    task = Task(name="Morning walk", duration=20, priority=2, category=Category.WALKING)
    owner = Owner(name="Jordan", owner_info="Busy professional", preferences=prefs)

    print(f"Owner : {owner.name}")
    print(f"Pet   : {pet.name} ({pet.breed}, {pet.age} yrs)")
    print(f"Task  : {task.name} — {task.duration} min, category={task.category.value}")
    print(f"Prefs : {prefs.preferred_time}, priorities={[c.value for c in prefs.priority_categories]}")
    print("Skeleton loaded successfully.")
