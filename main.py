from datetime import date
from pawpal_system import Owner, Task, Preferences, Category, TimeSlot

# --- Setup ---
prefs = Preferences(
    preferred_time=TimeSlot.MORNING,
    priority_categories=[Category.FEEDING, Category.WALKING],
)

owner = Owner(name="Jordan", owner_info="Busy professional", preferences=prefs)

# Two pets registered by their owners at the front desk
mochi = owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")
boba  = owner.add_pet(name="Boba",  age=5, breed="Golden Retriever")

# At least three tasks assigned to different pets
today = date.today()

owner.schedule_task(Task(name="Breakfast",      duration=15, priority=3, category=Category.FEEDING,  pet=mochi), today)
owner.schedule_task(Task(name="Morning walk",   duration=30, priority=2, category=Category.WALKING,  pet=mochi), today)
owner.schedule_task(Task(name="Brush coat",     duration=20, priority=1, category=Category.GROOMING, pet=mochi), today)
owner.schedule_task(Task(name="Boba's feeding", duration=10, priority=3, category=Category.FEEDING,  pet=boba),  today)
owner.schedule_task(Task(name="Boba's walk",    duration=45, priority=2, category=Category.WALKING,  pet=boba),  today)

# --- Print Today's Schedule ---
print("=" * 45)
print("         Today's Schedule")
print("=" * 45)

for plan in owner.scheduler.plans:
    if plan.date == today:
        print(f"\n  {plan.pet.name} ({plan.pet.breed})")
        print("  " + "-" * 35)
        for task in plan.view_plan():
            print(f"  {task.start_time}  {task.name:<20} {task.duration} min")

print()
