import streamlit as st
from datetime import date, timedelta
from collections import defaultdict
from pawpal_system import Owner, Task, Preferences, Category, TimeSlot, _time_to_minutes

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Priority → time slot mapping
# high = morning (07:00), medium = afternoon (12:00), low = evening (17:00)
PRIORITY_TIME = {
    "high":   ("07:00", TimeSlot.MORNING),
    "medium": ("12:00", TimeSlot.AFTERNOON),
    "low":    ("17:00", TimeSlot.EVENING),
}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owner_obj" not in st.session_state:
    prefs = Preferences(
        preferred_time=TimeSlot.MORNING,
        priority_categories=[Category.FEEDING, Category.WALKING],
    )
    st.session_state["owner_obj"] = Owner(name="Jordan", owner_info="", preferences=prefs)

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "schedule_visible" not in st.session_state:
    st.session_state.schedule_visible = False

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# Owner info
# ---------------------------------------------------------------------------
st.subheader("Owner Info")
owner_name = st.text_input("Owner name", value="Jordan")
owner = st.session_state["owner_obj"]
owner.name = owner_name

# ---------------------------------------------------------------------------
# Pets  (add multiple)
# ---------------------------------------------------------------------------
st.subheader("Pets")

if "pets" not in st.session_state:
    st.session_state.pets = []

with st.form("add_pet_form", clear_on_submit=True):
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        new_pet_name = st.text_input("Pet name", value="Mochi")
    with pc2:
        new_pet_breed = st.text_input("Breed", value="Shiba Inu")
    with pc3:
        new_pet_age = st.number_input("Age", min_value=0, max_value=30, value=3)
    add_pet = st.form_submit_button("Add pet")
    if add_pet:
        clean_name = new_pet_name.strip().strip("*").strip()
        already_exists = any(p.name == clean_name for p in owner.pets)
        if clean_name and not already_exists:
            # Phase 2 method: Owner.add_pet() creates the Pet and links owner_name
            owner.add_pet(name=clean_name, age=int(new_pet_age), breed=new_pet_breed)
            age = int(new_pet_age)
            if age <= 1:
                st.info(f"Tip: {clean_name} is a puppy/kitten — consider scheduling more frequent feeding and shorter, more frequent walks.")
            elif age >= 8:
                st.info(f"Tip: {clean_name} is a senior pet — consider gentler, shorter activities and more frequent vet check-ups.")

if owner.pets:
    for i, p in enumerate(owner.pets):
        c1, c2 = st.columns([6, 1])
        with c1:
            st.write(f"🐾 **{p.name}** — {p.breed}, {p.age} yrs")
        with c2:
            if st.button("Remove", key=f"rmpet_{i}"):
                # Phase 2 method: Owner.remove_pet() removes pet and clears its plans
                owner.remove_pet(p)
                st.rerun()
else:
    st.info("No pets added yet.")

st.divider()

# ---------------------------------------------------------------------------
# Add task
# ---------------------------------------------------------------------------
st.subheader("Tasks")

pet_names = [p.name for p in owner.pets] or ["(add a pet first)"]

CATEGORY_MAP = {
    "Feeding": Category.FEEDING,
    "Walking": Category.WALKING,
    "Grooming": Category.GROOMING,
}

with st.form("add_task_form", clear_on_submit=True):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        task_pet = st.selectbox("Pet", pet_names)
    with tc2:
        task_title = st.text_input("Task", value="Morning walk")
    with tc3:
        task_category = st.selectbox("Category", list(CATEGORY_MAP.keys()))
    tc4, tc5, tc6 = st.columns(3)
    with tc4:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with tc5:
        priority = st.selectbox("Priority", ["high", "medium", "low"])
    with tc6:
        task_date = st.date_input("Date", value=date.today())
    rc1, rc2 = st.columns(2)
    with rc1:
        recurring = st.checkbox("Repeat task")
    with rc2:
        recur_count = st.number_input("Occurrences", min_value=2, max_value=30, value=7, disabled=not recurring)
    recur_interval = 1
    if recurring:
        recur_interval = st.number_input("Every N days", min_value=1, max_value=30, value=1)

    add_task = st.form_submit_button("Add task")
    if add_task and task_pet != "(add a pet first)":
        pet_obj = next(p for p in owner.pets if p.name == task_pet)
        prio_int = {"high": 3, "medium": 2, "low": 1}[priority]
        base_task = Task(
            name=task_title,
            duration=int(duration),
            priority=prio_int,
            category=CATEGORY_MAP[task_category],
            pet=pet_obj,
            recur_days=int(recur_interval) if recurring else 0,
        )
        if recurring:
            owner.schedule_recurring(base_task, task_date, int(recur_count), int(recur_interval))
            for i in range(int(recur_count)):
                d = task_date + timedelta(days=i * int(recur_interval))
                st.session_state.tasks.append({
                    "pet": task_pet,
                    "title": task_title,
                    "category": task_category,
                    "duration_minutes": int(duration),
                    "priority": priority,
                    "date": str(d),
                    "recurring": True,
                })
        else:
            owner.schedule_task(base_task, task_date)
            st.session_state.tasks.append({
                "pet": task_pet,
                "title": task_title,
                "category": task_category,
                "duration_minutes": int(duration),
                "priority": priority,
                "date": str(task_date),
                "recurring": False,
            })

# Current tasks table with filter + complete + delete
if st.session_state.tasks:
    st.markdown("**Current tasks:**")
    all_pet_names = sorted({t["pet"] for t in st.session_state.tasks})
    fc1, fc2 = st.columns(2)
    with fc1:
        filter_pet = st.selectbox("Filter by pet", ["All"] + all_pet_names, key="filter_pet")
    with fc2:
        filter_status = st.selectbox("Filter by status", ["All", "Pending", "Done"], key="filter_status")

    visible_tasks = [
        (i, t) for i, t in enumerate(st.session_state.tasks)
        if (filter_pet == "All" or t["pet"] == filter_pet)
        and (filter_status == "All"
             or (filter_status == "Done" and t.get("completed"))
             or (filter_status == "Pending" and not t.get("completed")))
    ]

    if not visible_tasks:
        st.info("No tasks match the current filters.")

    for i, t in visible_tasks:
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            label = f"~~{t['title']}~~" if t.get("completed") else t['title']
            recur_badge = " 🔁" if t.get("recurring") else ""
            st.write(f"**{t['pet']}** | {label}{recur_badge} | {t['date']} | {t['duration_minutes']} min | {t['priority']}")
        with c2:
            if not t.get("completed"):
                if st.button("Done", key=f"done_{i}"):
                    # Find the matching Task object and mark it complete
                    for plan in owner.scheduler.plans:
                        for task in plan.tasks:
                            if task.name == t["title"] and plan.pet.name == t["pet"] and str(plan.date) == t["date"]:
                                task.mark_complete()
                    st.session_state.tasks[i]["completed"] = True
                    st.rerun()
            else:
                st.write("✓ Done")
        with c3:
            if st.button("Delete", key=f"del_{i}"):
                st.session_state.tasks.pop(i)
                st.rerun()
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Generate schedule
# ---------------------------------------------------------------------------
st.subheader("Build Schedule")

sc1, sc2, sc3 = st.columns(3)
with sc1:
    sched_filter_pet = st.selectbox("Filter schedule by pet", ["All"] + [p.name for p in owner.pets], key="sched_pet")
with sc2:
    sched_filter_status = st.selectbox("Filter schedule by status", ["All", "Pending", "Done"], key="sched_status")
with sc3:
    sched_sort = st.selectbox("Sort tasks by", ["Time", "Priority"], key="sched_sort")

if st.button("Generate schedule"):
    if not owner.scheduler.plans:
        st.warning("Add at least one task before generating a schedule.")
    elif not owner.pets:
        st.warning("Add at least one pet before generating a schedule.")
    else:
        st.session_state.schedule_visible = True

if st.session_state.schedule_visible and owner.scheduler.plans:
    # Group existing plans by date
    by_date = defaultdict(list)
    for plan in owner.scheduler.plans:
        by_date[str(plan.date)].append(plan)

    st.markdown(f"## {owner.name}'s Schedule")

    for d in sorted(by_date.keys()):
        st.success(f"📅 {d}")
        all_rows = []

        for plan in by_date[d]:
            if sched_filter_pet != "All" and plan.pet.name != sched_filter_pet:
                continue

            # Regenerate start times: highest priority task starts its slot, rest follow sequentially
            sorted_tasks = sorted(plan.tasks, key=lambda t: -t.priority)
            if not sorted_tasks:
                continue
            top_prio = {3: "high", 2: "medium", 1: "low"}.get(sorted_tasks[0].priority, "low")
            start, _ = PRIORITY_TIME[top_prio]
            h, m = map(int, start.split(":"))
            for task in sorted_tasks:
                task.start_time = f"{h:02d}:{m:02d}"
                end_total = _time_to_minutes(task.start_time) + task.duration
                if end_total >= 24 * 60:
                    st.warning(f"⚠️ '{task.name}' for {plan.pet.name} runs past midnight — consider shortening or rescheduling.")
                m += task.duration
                h += m // 60
                m = m % 60
                all_rows.append({
                    "Time": task.start_time,
                    "Pet": plan.pet.name,
                    "Task": task.name,
                    "Duration (min)": task.duration,
                    "Priority": task.priority,
                    "_completed": task.completed,
                })

            # Conflict detection
            conflicts = owner.scheduler.detect_conflicts(plan)
            for a, b in conflicts:
                st.error(f"⚠️ Conflict: **{a.name}** and **{b.name}** for {plan.pet.name} overlap on {d}.")

        if all_rows:
            # Apply status filter
            if sched_filter_status == "Done":
                all_rows = [r for r in all_rows if r["_completed"]]
            elif sched_filter_status == "Pending":
                all_rows = [r for r in all_rows if not r["_completed"]]

            # Apply sort
            if sched_sort == "Time":
                display_rows = sorted(all_rows, key=lambda r: r["Time"])
            else:
                display_rows = sorted(all_rows, key=lambda r: -r["Priority"])

            # Header row
            h1, h2, h3, h4, h5, h6 = st.columns([2, 2, 3, 2, 2, 2])
            h1.markdown("**Time**"); h2.markdown("**Pet**"); h3.markdown("**Task**")
            h4.markdown("**Duration**"); h5.markdown("**Priority**"); h6.markdown("**Status**")

            for row_idx, row in enumerate(display_rows):
                completed = row["_completed"]
                c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 3, 2, 2, 2])
                c1.write(row["Time"])
                c2.write(row["Pet"])
                c3.write(f"~~{row['Task']}~~" if completed else row["Task"])
                c4.write(f"{row['Duration (min)']} min")
                c5.write(row["Priority"])
                if completed:
                    c6.write("✓ Done")
                else:
                    btn_key = f"sched_done_{d}_{row['Pet']}_{row['Task']}_{row_idx}"
                    if c6.button("Done", key=btn_key):
                        for plan in owner.scheduler.plans:
                            for task in plan.tasks:
                                if (task.name == row["Task"]
                                        and plan.pet.name == row["Pet"]
                                        and str(plan.date) == d):
                                    task.mark_complete()
                        for st_task in st.session_state.tasks:
                            if (st_task["title"] == row["Task"]
                                    and st_task["pet"] == row["Pet"]
                                    and st_task["date"] == d):
                                st_task["completed"] = True
                        st.rerun()

            with st.expander("Why was this plan generated?"):
                for row in display_rows:
                    p = row["Priority"]
                    if p == 3:
                        time_reason = "scheduled at 07:00 (high priority → morning slot)"
                    elif p == 2:
                        time_reason = "scheduled at 12:00 (medium priority → afternoon slot)"
                    else:
                        time_reason = "scheduled at 17:00 (low priority → evening slot)"
                    st.markdown(
                        f"- **{row['Task']}** ({row['Pet']}) — {time_reason}, "
                        f"runs for {row['Duration (min)']} min, placed at **{row['Time']}** "
                        f"after any higher-priority tasks on this day."
                    )
