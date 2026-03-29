from dataclasses import dataclass
from enum import Enum
from datetime import date, timedelta
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pet):
            return NotImplemented
        return self.name == other.name and self.age == other.age and self.breed == other.breed

    def __hash__(self) -> int:
        return hash((self.name, self.age, self.breed))


@dataclass
class Task:
    name: str
    duration: int                        # minutes
    priority: int                        # higher number = higher priority
    pet: Optional["Pet"] = None          # which pet this task is for
    start_time: Optional[str] = None     # e.g. "08:00" (computed or user-set)
    completed: bool = False
    recur_days: int = 0       # interval between occurrences (0 = one-time)
    recur_remaining: int = 0  # how many future occurrences remain after this one
    user_start_time: Optional[str] = None  # user-specified start time; overrides auto-scheduling

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True


@dataclass
class Preferences:
    preferred_time: TimeSlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIME_SLOT_START = {
    TimeSlot.MORNING: "07:00",
    TimeSlot.AFTERNOON: "12:00",
    TimeSlot.EVENING: "17:00",
}


def _time_to_minutes(time_str: str) -> int:
    """Convert a "HH:MM" string to an integer number of minutes since midnight."""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def _round_up_to_half_hour(total_minutes: int) -> int:
    """Round up to the next :00 or :30 boundary."""
    remainder = total_minutes % 30
    if remainder == 0:
        return total_minutes
    return total_minutes + (30 - remainder)


def _add_minutes(time_str: str, minutes: int) -> str:
    """Add *minutes* to a "HH:MM" string and return the result as "HH:MM".

    Wraps around midnight (modulo 24 hours).
    """
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _intervals_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    """Return True if half-open intervals [start_a, end_a) and [start_b, end_b) overlap."""
    return start_a < end_b and start_b < end_a


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
        """Schedule tasks avoiding time overlaps.
        User-pinned tasks (user_start_time set) keep their exact time.
        Auto tasks are placed at the next free :00/:30 slot that doesn't
        overlap any pinned or already-placed task.
        Completed tasks are excluded from rescheduling."""
        for t in self.tasks:
            if t.completed:
                t.start_time = None
        pending = [t for t in self.tasks if not t.completed]
        pending.sort(key=lambda t: -t.priority)

        def _overlaps_any(start: int, end: int) -> bool:
            return any(_intervals_overlap(start, end, w_start, w_end) for w_start, w_end in placed_windows)

        placed_windows: list = []
        default_start = _time_to_minutes(TIME_SLOT_START[preferences.preferred_time])

        for task in pending:
            # Start from user-requested time if set, otherwise use the running cursor
            candidate = _round_up_to_half_hour(
                _time_to_minutes(task.user_start_time) if task.user_start_time is not None else default_start
            )
            # Push forward until the slot is free
            while _overlaps_any(candidate, candidate + task.duration):
                candidate += 30
            task.start_time = f"{(candidate // 60) % 24:02d}:{candidate % 60:02d}"
            placed_windows.append((candidate, candidate + task.duration))
            if task.user_start_time is None:
                default_start = candidate + task.duration

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
        self._plan_index: dict = {}  # (date, pet.name, pet.breed, pet.age) -> DailyPlan

    @property
    def plans(self) -> List[DailyPlan]:
        return list(self._plan_index.values())

    @plans.setter
    def plans(self, value: List[DailyPlan]) -> None:
        self._plan_index = {(p.date, p.pet.name, p.pet.breed, p.pet.age): p for p in value}

    def create_daily_plan(self, plan_date: date, pet: Pet) -> DailyPlan:
        """Return the existing plan for this date and pet, or create a new one."""
        key = (plan_date, pet.name, pet.breed, pet.age)
        if key not in self._plan_index:
            self._plan_index[key] = DailyPlan(plan_date, pet)
        return self._plan_index[key]

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted by start_time in HH:MM format.
        Tasks without a start_time are placed at the end."""
        assigned = [t for t in tasks if t.start_time is not None]
        unassigned = [t for t in tasks if t.start_time is None]
        return sorted(assigned, key=lambda t: _time_to_minutes(t.start_time)) + unassigned

    def handle_conflict(self, task: Task, plan: DailyPlan) -> None:
        """Add the task to the plan."""
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
                if _intervals_overlap(a_start, a_end, b_start, b_end):
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
        """Schedule a recurring task starting on *start_date*.

        Only the first occurrence is placed on the calendar immediately.
        The ``recur_days`` and ``recur_remaining`` fields on the created task
        record how often it repeats and how many future occurrences are still
        pending, so a background process (or the next call) can spawn the
        remaining copies.

        Args:
            task: Template task whose name, duration, priority, pet, and
                optional user_start_time are copied into the first occurrence.
            start_date: The date on which the first occurrence is scheduled.
            occurrences: Total number of times the task should occur
                (including the first one).
            interval_days: Number of days between consecutive occurrences.
                Defaults to 1 (daily).
        """
        first = Task(
            name=task.name,
            duration=task.duration,
            priority=task.priority,
            pet=task.pet,
            recur_days=interval_days,
            recur_remaining=occurrences - 1,
            user_start_time=task.user_start_time,
        )
        self.schedule_task(first, start_date)

    def cancel_task(self, task: Task) -> None:
        """Remove a task from whichever plan contains it and regenerate that plan.
        If the plan becomes empty, remove it from the scheduler."""
        for plan in self.scheduler.plans:
            if task in plan.tasks:
                plan.remove_task(task)
                if plan.tasks:
                    self.scheduler.adjust_plan(plan)
                else:
                    self.scheduler.plans = [p for p in self.scheduler.plans if p is not plan]
                break

    def complete_task(self, task: Task) -> None:
        """Mark a task complete and spawn its next recurring occurrence if needed."""
        for plan in self.scheduler.plans:
            if task not in plan.tasks:
                continue

            task.mark_complete()
            self.scheduler.adjust_plan(plan)

            if task.recur_days > 0 and task.recur_remaining > 0:
                next_task = Task(
                    name=task.name,
                    duration=task.duration,
                    priority=task.priority,
                    pet=task.pet,
                    recur_days=task.recur_days,
                    recur_remaining=task.recur_remaining - 1,
                    user_start_time=task.user_start_time,
                )
                next_date = plan.date + timedelta(days=task.recur_days)
                self.schedule_task(next_task, next_date)
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
    prefs = Preferences(preferred_time=TimeSlot.MORNING)
    owner = Owner(name="Jordan", owner_info="Busy professional", preferences=prefs)
    pet = owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")

    tasks = [
        Task(name="Morning walk", duration=30, priority=3, pet=pet),
        Task(name="Breakfast",    duration=15, priority=2, pet=pet),
        Task(name="Brush coat",   duration=20, priority=1, pet=pet),
    ]

    today = date.today()
    for t in tasks:
        owner.schedule_task(t, today)

    plan = owner.view_schedule()
    print(f"Schedule for {pet.name} on {plan.date}:")
    print("-" * 40)
    for t in plan.view_plan():
        print(f"  {t.start_time}  {t.name} ({t.duration} min, priority {t.priority})")

    print(f"\nCancelling '{tasks[2].name}'...")
    owner.cancel_task(tasks[2])
    print(f"\nUpdated schedule:")
    print("-" * 40)
    for t in plan.view_plan():
        print(f"  {t.start_time}  {t.name} ({t.duration} min, priority {t.priority})")
