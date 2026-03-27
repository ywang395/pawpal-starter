from dataclasses import dataclass, field
from enum import Enum
from datetime import date, timedelta
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Category(Enum):
    FEEDING = "Feeding"
    WALKING = "Walking"
    GROOMING = "Grooming"


class TimeSlot(Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


# ---------------------------------------------------------------------------
# Dataclasses  (pure data holders)
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    age: int
    breed: str
    owner_name: str = ""   # which customer owns this pet


@dataclass
class Task:
    name: str
    duration: int                        # minutes
    priority: int                        # higher number = higher priority
    category: Category
    pet: Optional["Pet"] = None          # which pet this task is for
    start_time: Optional[str] = None     # e.g. "08:00"
    completed: bool = False
    recur_days: int = 0  # 0 = one-time; >0 = repeat every N days for that many occurrences

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True


@dataclass
class Preferences:
    preferred_time: TimeSlot
    priority_categories: List[Category] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIME_SLOT_START = {
    TimeSlot.MORNING: "07:00",
    TimeSlot.AFTERNOON: "12:00",
    TimeSlot.EVENING: "17:00",
}


def _time_to_minutes(time_str: str) -> int:
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def _add_minutes(time_str: str, minutes: int) -> str:
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# Regular classes
# ---------------------------------------------------------------------------

class DailyPlan:
    def __init__(self, plan_date: date, pet: Pet):
        self.date: date = plan_date
        self.pet: Pet = pet
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        """Append a task to this plan."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this plan if it exists."""
        if task in self.tasks:
            self.tasks.remove(task)

    def generate_schedule(self, preferences: Preferences) -> None:
        """Sort tasks by preferred category and priority, then assign sequential start times.
        Completed tasks are excluded from rescheduling."""
        pending = [t for t in self.tasks if not t.completed]
        pending.sort(
            key=lambda t: (
                0 if t.category in preferences.priority_categories else 1,
                -t.priority,
            )
        )
        current_time = TIME_SLOT_START[preferences.preferred_time]
        for task in pending:
            task.start_time = current_time
            current_time = _add_minutes(current_time, task.duration)

    def view_plan(self, sort_by_time: bool = True) -> List[Task]:
        """Return tasks sorted by start_time (default) or in insertion order."""
        if sort_by_time:
            assigned = [t for t in self.tasks if t.start_time is not None]
            unassigned = [t for t in self.tasks if t.start_time is None]
            assigned.sort(key=lambda t: _time_to_minutes(t.start_time))
            return assigned + unassigned
        return list(self.tasks)


class Scheduler:
    def __init__(self, preferences: Preferences):
        self.preferences: Preferences = preferences
        self._plan_index: dict = {}  # (date, pet.name) -> DailyPlan

    @property
    def plans(self) -> List[DailyPlan]:
        return list(self._plan_index.values())

    @plans.setter
    def plans(self, value: List[DailyPlan]) -> None:
        self._plan_index = {(p.date, p.pet.name): p for p in value}

    def create_daily_plan(self, plan_date: date, pet: Pet) -> DailyPlan:
        """Return the existing plan for this date and pet, or create a new one."""
        key = (plan_date, pet.name)
        if key not in self._plan_index:
            self._plan_index[key] = DailyPlan(plan_date, pet)
        return self._plan_index[key]

    def handle_conflict(self, task: Task, plan: DailyPlan) -> None:
        """Add the task to the plan, rejecting exact duplicates (same name + pet)."""
        for existing in plan.tasks:
            if existing.name == task.name and existing.pet == task.pet:
                return
        plan.add_task(task)

    def detect_conflicts(self, plan: DailyPlan) -> List[tuple]:
        """Return a list of (task_a, task_b) pairs whose scheduled time windows overlap.
        Only considers tasks that have been assigned a start_time."""
        conflicts = []
        assigned = [t for t in plan.tasks if t.start_time is not None]
        for i, a in enumerate(assigned):
            a_start = _time_to_minutes(a.start_time)
            a_end = a_start + a.duration
            for b in assigned[i + 1:]:
                b_start = _time_to_minutes(b.start_time)
                b_end = b_start + b.duration
                if a_start < b_end and b_start < a_end:
                    conflicts.append((a, b))
        return conflicts

    def adjust_plan(self, plan: DailyPlan) -> None:
        """Regenerate the schedule for a plan after a task is added or removed."""
        plan.generate_schedule(self.preferences)


class Owner:
    def __init__(self, name: str, owner_info: str, preferences: Preferences):
        self.name: str = name
        self.owner_info: str = owner_info
        self.preferences: Preferences = preferences
        self.pets: List[Pet] = []
        self.scheduler: Scheduler = Scheduler(preferences)

    def add_pet(self, name: str, age: int, breed: str) -> Pet:
        """Create a pet record linked to this owner and add it to the owner's list."""
        pet = Pet(name=name, age=age, breed=breed, owner_name=self.name)
        self.pets.append(pet)
        return pet

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet and all its associated plans from this owner."""
        if pet in self.pets:
            self.pets.remove(pet)
            self.scheduler.plans = [p for p in self.scheduler.plans if p.pet != pet]

    def schedule_task(self, task: Task, plan_date: date) -> None:
        """Add a task to the plan for the given date, creating the plan if needed."""
        pet = task.pet if task.pet else (self.pets[0] if self.pets else None)
        if pet is None:
            return
        plan = self.scheduler.create_daily_plan(plan_date, pet)
        self.scheduler.handle_conflict(task, plan)
        self.scheduler.adjust_plan(plan)

    def schedule_recurring(self, task: Task, start_date: date, occurrences: int, interval_days: int = 1) -> None:
        """Schedule copies of task across multiple dates separated by interval_days."""
        for i in range(occurrences):
            day = start_date + timedelta(days=i * interval_days)
            copy = Task(
                name=task.name,
                duration=task.duration,
                priority=task.priority,
                category=task.category,
                pet=task.pet,
                recur_days=interval_days,
            )
            self.schedule_task(copy, day)

    def cancel_task(self, task: Task) -> None:
        """Remove a task from whichever plan contains it and regenerate that plan."""
        for plan in self.scheduler.plans:
            if task in plan.tasks:
                plan.remove_task(task)
                self.scheduler.adjust_plan(plan)
                break

    def view_schedule(self) -> Optional[DailyPlan]:
        """Return today's plan, or None if today has no plan (even if past plans exist)."""
        today = date.today()
        for plan in self.scheduler.plans:
            if plan.date == today:
                return plan
        return None


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    prefs = Preferences(
        preferred_time=TimeSlot.MORNING,
        priority_categories=[Category.FEEDING, Category.WALKING],
    )
    owner = Owner(name="Jordan", owner_info="Busy professional", preferences=prefs)
    pet = owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")

    # Create three tasks with different priorities and categories
    tasks = [
        Task(name="Morning walk", duration=30, priority=3, category=Category.WALKING, pet=pet),
        Task(name="Breakfast", duration=15, priority=2, category=Category.FEEDING, pet=pet),
        Task(name="Brush coat", duration=20, priority=1, category=Category.GROOMING, pet=pet),
    ]

    today = date.today()
    for t in tasks:
        owner.schedule_task(t, today)

    # View schedule
    plan = owner.view_schedule()
    print(f"Schedule for {pet.name} on {plan.date}:")
    print("-" * 40)
    for t in plan.view_plan():
        print(f"  {t.start_time}  {t.name} ({t.category.value}, {t.duration} min, priority {t.priority})")

    # Cancel a task and view again
    print(f"\nCancelling '{tasks[2].name}'...")
    owner.cancel_task(tasks[2])
    print(f"\nUpdated schedule:")
    print("-" * 40)
    for t in plan.view_plan():
        print(f"  {t.start_time}  {t.name} ({t.category.value}, {t.duration} min, priority {t.priority})")
