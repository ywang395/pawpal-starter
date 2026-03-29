from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt


def draw_class(ax, x, y, w, h, title, attrs, methods, color="#f8fbff"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="#264653", linewidth=2))
    ax.plot([x, x + w], [y + h - 0.55, y + h - 0.55], color="#264653", linewidth=1.5)
    ax.plot([x, x + w], [y + 0.95, y + 0.95], color="#264653", linewidth=1.5)
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="center", fontsize=12, fontweight="bold")

    attr_y = y + h - 0.75
    for attr in attrs:
        ax.text(x + 0.12, attr_y, attr, ha="left", va="top", fontsize=9, family="monospace")
        attr_y -= 0.22

    meth_y = y + 0.82
    for method in methods:
        ax.text(x + 0.12, meth_y, method, ha="left", va="top", fontsize=9, family="monospace")
        meth_y -= 0.22


def arrow(ax, x1, y1, x2, y2, label="", color="#555"):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="->", linewidth=1.8, color=color, shrinkA=5, shrinkB=5),
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, fontsize=9, color=color, ha="center")


fig, ax = plt.subplots(figsize=(16, 10))
fig.patch.set_facecolor("#eef6f6")
ax.set_facecolor("#eef6f6")

owner = (0.5, 5.1, 4.3, 3.5)
pet = (0.6, 1.6, 3.0, 2.3)
task = (6.0, 5.0, 4.5, 3.8)
daily_plan = (11.3, 5.0, 4.2, 3.2)
scheduler = (11.1, 1.4, 4.6, 3.0)
preferences = (6.4, 1.45, 3.3, 1.7)
timeslot = (6.9, 0.15, 2.3, 0.9)

draw_class(
    ax, *owner,
    "Owner",
    ["+name: str", "+owner_info: str", "+preferences: Preferences", "+pets: List[Pet]", "+scheduler: Scheduler"],
    ["+add_pet(...): Pet", "+remove_pet(pet)", "+schedule_task(task, plan_date)", "+schedule_recurring(...)", "+cancel_task(task)", "+complete_task(task)", "+view_schedule(): DailyPlan|None"],
)

draw_class(
    ax, *pet,
    "Pet",
    ["+name: str", "+age: int", "+breed: str", "+owner_name: str"],
    ["+__eq__(other): bool", "+__hash__(): int"],
)

draw_class(
    ax, *task,
    "Task",
    ["+name: str", "+duration: int", "+priority: int", "+pet: Optional[Pet]", "+start_time: Optional[str]", "+completed: bool", "+recur_days: int", "+recur_remaining: int", "+user_start_time: Optional[str]"],
    ["+mark_complete()"],
)

draw_class(
    ax, *daily_plan,
    "DailyPlan",
    ["+date: date", "+pet: Pet", "+tasks: List[Task]"],
    ["+add_task(task)", "+remove_task(task)", "+generate_schedule(preferences)", "+view_plan(sort_by_time=True): List[Task]"],
)

draw_class(
    ax, *scheduler,
    "Scheduler",
    ["+preferences: Preferences", "+_plan_index: dict", "+plans: List[DailyPlan]"],
    ["+create_daily_plan(date, pet): DailyPlan", "+sort_by_time(tasks): List[Task]", "+handle_conflict(task, plan)", "+detect_conflicts(plan): List[tuple]", "+adjust_plan(plan)"],
)

draw_class(
    ax, *preferences,
    "Preferences",
    ["+preferred_time: TimeSlot"],
    [],
)

draw_class(
    ax, *timeslot,
    "TimeSlot <<enum>>",
    ["MORNING", "AFTERNOON", "EVENING"],
    [],
    color="#fffaf0",
)

arrow(ax, owner[0] + owner[2] / 2, owner[1], pet[0] + pet[2] / 2, pet[1] + pet[3], "owns")
arrow(ax, owner[0] + owner[2], owner[1] + 1.8, task[0], task[1] + 2.0, "schedules")
arrow(ax, owner[0] + owner[2], owner[1] + 0.9, scheduler[0], scheduler[1] + 2.2, "uses")
arrow(ax, scheduler[0] + 2.0, scheduler[1] + scheduler[3], daily_plan[0] + 2.0, daily_plan[1], "manages")
arrow(ax, daily_plan[0], daily_plan[1] + 2.2, task[0] + task[2], task[1] + 2.0, "contains")
arrow(ax, daily_plan[0] + 0.6, daily_plan[1], scheduler[0] + 0.8, scheduler[1] + scheduler[3], "adjusts via")
arrow(ax, task[0] + 0.8, task[1], preferences[0] + 1.0, preferences[1] + preferences[3], "scheduled with")
arrow(ax, preferences[0] + preferences[2] / 2, preferences[1], timeslot[0] + timeslot[2] / 2, timeslot[1] + timeslot[3], "stores")
arrow(ax, task[0] + 0.2, task[1], pet[0] + pet[2], pet[1] + pet[3] - 0.2, "assigned to")

ax.text(0.5, 9.35, "PawPal+ Final UML Diagram", fontsize=18, fontweight="bold", color="#1d3557")
ax.text(0.5, 9.0, "Updated to reflect the final implementation in pawpal_system.py", fontsize=10, color="#457b9d")

ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis("off")
plt.tight_layout()
plt.savefig("uml_final.png", dpi=220, bbox_inches="tight")
