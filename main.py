from datetime import date
from pawpal_system import Owner, Task, Preferences, TimeSlot


def priority_badge(priority: int) -> str:
    return {3: "🔴 High", 2: "🟡 Medium", 1: "🟢 Low"}.get(priority, str(priority))


def status_badge(completed: bool) -> str:
    return "✅ Done" if completed else "🕒 Pending"


def print_task_table(title: str, pet_name: str, breed: str, tasks):
    print(f"\n  {pet_name} ({breed})")
    print("  " + "-" * 74)
    print(f"  {title}")
    print("  " + "-" * 74)
    print(f"  {'Time':<8} {'Task':<22} {'Duration':<12} {'Priority':<12} {'Status':<12}")
    for task in tasks:
        print(
            f"  {(task.start_time or '--:--'):<8} "
            f"{task.name:<22} "
            f"{(str(task.duration) + ' min'):<12} "
            f"{priority_badge(task.priority):<12} "
            f"{status_badge(task.completed):<12}"
        )


# --- Setup ---
prefs = Preferences(preferred_time=TimeSlot.MORNING)
owner = Owner(name="Jordan", owner_info="Busy professional", preferences=prefs)

mochi = owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")
boba  = owner.add_pet(name="Boba",  age=5, breed="Golden Retriever")

today = date.today()

# Add tasks OUT OF ORDER (later times first, mixed priorities)
owner.schedule_task(Task(name="Evening walk",   duration=30, priority=1, pet=mochi, user_start_time="17:00"), today)
owner.schedule_task(Task(name="Lunch snack",    duration=10, priority=2, pet=mochi, user_start_time="12:30"), today)
owner.schedule_task(Task(name="Breakfast",      duration=15, priority=3, pet=mochi, user_start_time="07:00"), today)
# Intentional conflict: "Morning meds" starts at 07:05, overlapping "Breakfast" (07:00–07:15)
owner.schedule_task(Task(name="Morning meds",   duration=10, priority=2, pet=mochi, user_start_time="07:05"), today)
owner.schedule_task(Task(name="Boba's walk",    duration=45, priority=2, pet=boba,  user_start_time="08:00"), today)
owner.schedule_task(Task(name="Boba's feeding", duration=10, priority=3, pet=boba,  user_start_time="07:00"), today)
owner.schedule_task(Task(name="Boba's grooming",duration=20, priority=1, pet=boba,  user_start_time="15:00"), today)

# --- Conflict detection (based on user-requested times, before auto-resolution) ---
print("=" * 50)
print("  Conflict Detection")
print("=" * 50)
from pawpal_system import _time_to_minutes
any_conflicts = False
for plan in owner.scheduler.plans:
    if plan.date != today:
        continue
    pinned = [t for t in plan.tasks if t.user_start_time]
    for i, a in enumerate(pinned):
        a_start = _time_to_minutes(a.user_start_time)
        for b in pinned[i + 1:]:
            b_start = _time_to_minutes(b.user_start_time)
            if a_start < b_start + b.duration and b_start < a_start + a.duration:
                any_conflicts = True
                print(f"  WARNING: '{a.name}' requested {a.user_start_time} ({a.duration} min) "
                      f"overlaps '{b.name}' requested {b.user_start_time} ({b.duration} min) "
                      f"for {plan.pet.name} — scheduler will resolve automatically.")
if not any_conflicts:
    print("  No conflicts detected.")
print()

# Mark one task complete to test filtering
mochi_plan = next(p for p in owner.scheduler.plans if p.pet == mochi and p.date == today)
for t in mochi_plan.tasks:
    if t.name == "Evening walk":
        t.mark_complete()

# --- Print sorted by time (all tasks) ---
print("=" * 50)
print("  Sorted by Time (all tasks, all pets)")
print("=" * 50)
for plan in owner.scheduler.plans:
    if plan.date == today:
        sorted_tasks = owner.scheduler.sort_by_time(plan.tasks)
        print_task_table("All tasks", plan.pet.name, plan.pet.breed, sorted_tasks)

# --- Print filtered: pending only ---
print()
print("=" * 50)
print("  Filtered: Pending tasks only")
print("=" * 50)
for plan in owner.scheduler.plans:
    if plan.date == today:
        pending = [t for t in owner.scheduler.sort_by_time(plan.tasks) if not t.completed]
        if pending:
            print_task_table("Pending tasks", plan.pet.name, plan.pet.breed, pending)

# --- Print filtered: completed only ---
print()
print("=" * 50)
print("  Filtered: Completed tasks only")
print("=" * 50)
found = False
for plan in owner.scheduler.plans:
    if plan.date == today:
        done = [t for t in owner.scheduler.sort_by_time(plan.tasks) if t.completed]
        if done:
            found = True
            print_task_table("Completed tasks", plan.pet.name, plan.pet.breed, done)
if not found:
    print("\n  No completed tasks.")

print()
