import streamlit as st
from datetime import date, timedelta
from collections import defaultdict
from pawpal_system import Owner, Task, Preferences, TimeSlot, _time_to_minutes

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owner_obj" not in st.session_state:
    prefs = Preferences(preferred_time=TimeSlot.MORNING)
    st.session_state["owner_obj"] = Owner(name="Jordan", owner_info="", preferences=prefs)

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "schedule_visible" not in st.session_state:
    st.session_state.schedule_visible = False

if "recurring_checkbox" not in st.session_state:
    st.session_state.recurring_checkbox = False


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
        already_exists = any(
            p.name == clean_name and p.breed == new_pet_breed.strip() and p.age == int(new_pet_age)
            for p in owner.pets
        )
        if clean_name and not already_exists:
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
                owner.remove_pet(p)
                st.rerun()
else:
    st.info("No pets added yet.")

st.divider()

# ---------------------------------------------------------------------------
# Add task
# ---------------------------------------------------------------------------
st.subheader("Tasks")

pet_labels = [f"{p.name} ({p.breed})" for p in owner.pets] or ["(add a pet first)"]
pet_label_to_obj = {f"{p.name} ({p.breed})": p for p in owner.pets}

# Recurring controls live outside the form so the checkbox triggers an immediate
# rerun and enables the number inputs before the form is submitted.
rc1, rc2, rc3 = st.columns(3)
with rc1:
    recurring = st.checkbox("Repeat task", key="recurring_checkbox")
with rc2:
    recur_count = st.number_input("Occurrences", min_value=2, max_value=30, value=7,
                                   disabled=not st.session_state.recurring_checkbox,
                                   key="recur_count")
with rc3:
    recur_interval = st.number_input("Every N days", min_value=1, max_value=30, value=1,
                                      disabled=not st.session_state.recurring_checkbox,
                                      key="recur_interval")

with st.form("add_task_form", clear_on_submit=True):
    tc1, tc2 = st.columns(2)
    with tc1:
        task_pets = st.multiselect("Pet(s)", ["All pets"] + pet_labels)
    with tc2:
        task_title = st.text_input("Task", value="Morning walk")
    tc4, tc5, tc6 = st.columns(3)
    with tc4:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with tc5:
        priority = st.selectbox("Priority", ["high", "medium", "low"])
    with tc6:
        task_date = st.date_input("Date", value=date.today())
    task_time = st.text_input("Start time (HH:MM)", value="07:00", placeholder="e.g. 08:30")

    add_task = st.form_submit_button("Add task")

import re
if add_task:
    if not task_pets:
        st.error("Please select at least one pet.")
    elif not re.match(r"^\d{2}:\d{2}$", task_time.strip()):
        st.error("Invalid time format. Please use HH:MM (e.g. 08:30).")
    else:
        is_recurring = st.session_state.recurring_checkbox
        n_occurrences = st.session_state.recur_count
        n_interval = st.session_state.recur_interval
        prio_int = {"high": 3, "medium": 2, "low": 1}[priority]

        # Expand "All pets" to every pet label
        selected_labels = pet_labels if "All pets" in task_pets else task_pets

        # Tasks added in the same submission share a group_id — allowed to overlap each other
        import uuid
        group_id = str(uuid.uuid4()) if len(selected_labels) > 1 else None

        for label in selected_labels:
            if label not in pet_label_to_obj:
                continue
            pet_obj = pet_label_to_obj[label]
            base_task = Task(
                name=task_title,
                duration=int(duration),
                priority=prio_int,
                pet=pet_obj,
                recur_days=int(n_interval) if is_recurring else 0,
                user_start_time=task_time.strip(),
            )
            if is_recurring:
                owner.schedule_recurring(base_task, task_date, int(n_occurrences), int(n_interval))
                for i in range(int(n_occurrences)):
                    recur_day = task_date + timedelta(days=i * int(n_interval))
                    st.session_state.tasks.append({
                        "pet": label,
                        "title": task_title,
                        "duration_minutes": int(duration),
                        "priority": priority,
                        "date": str(recur_day),
                        "recurring": True,
                        "start_time": task_time.strip(),
                        "group_id": group_id,
                    })
            else:
                owner.schedule_task(base_task, task_date)
                st.session_state.tasks.append({
                    "pet": label,
                    "title": task_title,
                    "duration_minutes": int(duration),
                    "priority": priority,
                    "date": str(task_date),
                    "recurring": False,
                    "start_time": task_time.strip(),
                    "group_id": group_id,
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
        and (filter_status == "Done" and t.get("completed")
             or filter_status == "Pending" and not t.get("completed")
             or filter_status == "All" and not t.get("completed"))
    ]

    if not visible_tasks:
        st.info("No tasks match the current filters.")

    for i, t in visible_tasks:
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            label = f"~~{t['title']}~~" if t.get("completed") else t['title']
            recur_badge = " 🔁" if t.get("recurring") else ""
            pet_obj = next((p for p in owner.pets if p.name == t["pet"]), None)
            pet_label = f"{t['pet']} ({pet_obj.breed})" if pet_obj else t["pet"]
            st.write(f"**{pet_label}** | {label}{recur_badge} | {t['date']} | {t['duration_minutes']} min | {t['priority']}")
        with c2:
            if not t.get("completed"):
                if st.button("Done", key=f"done_{i}"):
                    for plan in owner.scheduler.plans:
                        for task in plan.tasks:
                            if task.name == t["title"] and f"{plan.pet.name} ({plan.pet.breed})" == t["pet"] and str(plan.date) == t["date"]:
                                task.mark_complete()
                    st.session_state.tasks[i]["completed"] = True
                    st.rerun()
            else:
                st.write("✓ Done")
        with c3:
            if st.button("Delete", key=f"del_{i}"):
                for plan in owner.scheduler.plans:
                    for task in list(plan.tasks):
                        pet_label = f"{plan.pet.name} ({plan.pet.breed})"
                        if task.name == t["title"] and pet_label == t["pet"] and str(plan.date) == t["date"]:
                            owner.cancel_task(task)
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
    sched_filter_pet = st.selectbox("Filter schedule by pet", ["All"] + [f"{p.name} ({p.breed})" for p in owner.pets], key="sched_pet")
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

        # Collect all pending tasks across all pets for this date, sorted by priority
        all_tasks_for_day = []
        for plan in by_date[d]:
            if sched_filter_pet != "All" and f"{plan.pet.name} ({plan.pet.breed})" != sched_filter_pet:
                continue
            for task in plan.tasks:
                if not task.completed:
                    all_tasks_for_day.append((task, plan.pet))

        # Build group_id lookup: (pet_label, title, date) -> group_id
        group_lookup = {
            (t["pet"], t["title"], t["date"]): t.get("group_id")
            for t in st.session_state.tasks
        }

        # Attach group_id to each (task, pet) tuple
        tagged = []
        for task, pet in all_tasks_for_day:
            pet_label = f"{pet.name} ({pet.breed})"
            gid = group_lookup.get((pet_label, task.name, d))
            tagged.append((task, pet, gid))

        # Sort by user start time
        tagged.sort(key=lambda x: _time_to_minutes(x[0].user_start_time) if x[0].user_start_time else 0)

        placed_windows = []  # (start, end, group_id)
        assigned_group_time = {}  # group_id -> already-resolved candidate

        for task, pet, gid in tagged:
            if gid and gid in assigned_group_time:
                # Same group — reuse the already-assigned time
                candidate = assigned_group_time[gid]
            else:
                candidate = _time_to_minutes(task.user_start_time) if task.user_start_time else 0
                # Push forward only past windows from a different group
                original = candidate
                while any(
                    candidate < w_end and w_start < candidate + task.duration
                    and not (gid and gid == w_gid)
                    for w_start, w_end, w_gid in placed_windows
                ):
                    candidate += 30
                if candidate != original:
                    original_str = f"{(original // 60) % 24:02d}:{original % 60:02d}"
                    moved_str = f"{(candidate // 60) % 24:02d}:{candidate % 60:02d}"
                    st.warning(f"⚠️ **{task.name}** ({pet.name}) overlapped at {original_str} — moved to **{moved_str}**.")
                if gid:
                    assigned_group_time[gid] = candidate
                placed_windows.append((candidate, candidate + task.duration, gid))

            task.start_time = f"{(candidate // 60) % 24:02d}:{candidate % 60:02d}"

            end_total = candidate + task.duration
            if end_total >= 24 * 60:
                st.warning(f"⚠️ '{task.name}' for {pet.name} runs past midnight.")
            all_rows.append({
                "Time": task.start_time,
                "Pet": f"{pet.name} ({pet.breed})",
                "Task": task.name,
                "Duration (min)": task.duration,
                "Priority": task.priority,
                "_completed": task.completed,
            })

        if all_rows:
            # Apply status filter — by default hide completed tasks
            if sched_filter_status == "Done":
                all_rows = [r for r in all_rows if r["_completed"]]
            else:
                all_rows = [r for r in all_rows if not r["_completed"]]

            # Apply sort
            if sched_sort == "Time":
                display_rows = all_rows  # already sorted by sort_by_time()
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
                                        and f"{plan.pet.name} ({plan.pet.breed})" == row["Pet"]
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
                        time_reason = "scheduled first (high priority)"
                    elif p == 2:
                        time_reason = "scheduled second (medium priority)"
                    else:
                        time_reason = "scheduled last (low priority)"
                    st.markdown(
                        f"- **{row['Task']}** ({row['Pet']}) — {time_reason}, "
                        f"runs for {row['Duration (min)']} min, placed at **{row['Time']}**."
                    )
