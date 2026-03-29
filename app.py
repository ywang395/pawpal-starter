import streamlit as st
from datetime import date, timedelta
from collections import defaultdict
from pawpal_system import Owner, Task, Preferences, TimeSlot, _time_to_minutes, _intervals_overlap

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

if "booked_slots" not in st.session_state:
    st.session_state.booked_slots = {}  # date_str -> set of "HH:MM" strings


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
# Helpers
# ---------------------------------------------------------------------------
def _find_free_slot(candidate: int, duration: int, placed_windows: list, gid) -> int:
    """Advance candidate to the next free 30-min slot, ignoring windows in the same group."""
    while any(
        _intervals_overlap(candidate, candidate + duration, w_start, w_end)
        and not (gid and gid == w_gid)
        for w_start, w_end, w_gid in placed_windows
    ):
        candidate += 30
    return candidate


def _check_conflicts(owner, plan_date):
    """Return a list of warning strings for any overlapping tasks on plan_date."""
    warnings = []
    for plan in owner.scheduler.plans:
        if plan.date != plan_date:
            continue
        for a, b in owner.scheduler.detect_conflicts(plan):
            warnings.append(
                f"⚠️ **{a.name}** and **{b.name}** ({plan.pet.name}) overlap on {plan_date}."
            )
    return warnings


# ---------------------------------------------------------------------------
# Add task
# ---------------------------------------------------------------------------
st.subheader("Tasks")

pet_labels = [f"{p.name} ({p.breed})" for p in owner.pets] or ["(add a pet first)"]
pet_label_to_obj = {f"{p.name} ({p.breed})": p for p in owner.pets}

# Date outside the form so the slot dropdown updates live when date changes.
rc1, rc2, rc3, rc4 = st.columns(4)
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
with rc4:
    task_date = st.date_input("Date", value=date.today(), key="task_date_pick")

# Build start-time dropdown from already-submitted tasks on this date.
# Occupied slots are determined by existing task start_time + duration_minutes.
# When a task is deleted it's removed from session_state.tasks, freeing its slots automatically.
all_slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
occupied_windows = [
    (_time_to_minutes(t["start_time"]), _time_to_minutes(t["start_time"]) + t["duration_minutes"])
    for t in st.session_state.tasks
    if t.get("start_time") and t["date"] == str(task_date) and not t.get("completed")
]
already_booked = st.session_state.booked_slots.get(str(task_date), set())
free_slot_values = [
    s for s in all_slots
    if s not in already_booked
    and not any(_intervals_overlap(_time_to_minutes(s), _time_to_minutes(s) + 30, ws, we)
                for ws, we in occupied_windows)
]

if "task_time_submitted" not in st.session_state:
    st.session_state.task_time_submitted = None
if "task_time_last_submitted" not in st.session_state:
    st.session_state.task_time_last_submitted = None

PLACEHOLDER = "— Pick a time —"

if not free_slot_values:
    st.warning("No free slots available on this date.")
    task_time = None
    st.selectbox("Start time", [PLACEHOLDER], key="task_time_pick")
else:
    last = st.session_state.task_time_last_submitted
    prev = st.session_state.get("task_time_pick")
    options = [PLACEHOLDER] + free_slot_values
    # After submission or on first load, reset to placeholder; otherwise restore selection.
    if prev and prev in free_slot_values and prev != last:
        default_index = options.index(prev)
    else:
        default_index = 0
    selected = st.selectbox("Start time", options, index=default_index, key="task_time_pick")
    task_time = selected if selected != PLACEHOLDER else None
    st.session_state.task_time_submitted = task_time

with st.form("add_task_form", clear_on_submit=True):
    tc1, tc2 = st.columns(2)
    with tc1:
        task_pets = st.multiselect("Pet(s)", ["All pets"] + pet_labels)
    with tc2:
        task_title = st.text_input("Task", value="Morning walk")
    tc4, tc5 = st.columns(2)
    with tc4:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with tc5:
        priority = st.selectbox("Priority", ["high", "medium", "low"])

    add_task = st.form_submit_button("Add task")

if add_task:
    task_date = st.session_state.task_date_pick
    task_time = st.session_state.task_time_submitted or task_time
    if not task_time:
        st.error("Please pick a start time.")
    elif not task_pets:
        st.error("Please select at least one pet.")
    else:
        st.session_state.task_time_last_submitted = task_time
        date_key = str(task_date)
        if date_key not in st.session_state.booked_slots:
            st.session_state.booked_slots[date_key] = set()
        st.session_state.booked_slots[date_key].add(task_time)
        is_recurring = st.session_state.recurring_checkbox
        n_occurrences = st.session_state.recur_count
        n_interval = st.session_state.recur_interval
        prio_int = {"high": 3, "medium": 2, "low": 1}[priority]

        # Clamp duration to available space starting from task_time on this date.
        task_start_min = _time_to_minutes(task_time)
        next_conflict_start = min(
            (ws for ws, we in occupied_windows if ws >= task_start_min),
            default=24 * 60,
        )
        available = next_conflict_start - task_start_min
        effective_duration = int(duration)
        if effective_duration > available:
            effective_duration = max(available, 0)
            st.warning(
                f"⚠️ **{task_title}** overlaps an existing task at {task_time}. "
                f"Duration reduced from {int(duration)} min to **{effective_duration} min** "
                f"to fit the available slot."
            )

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
                duration=effective_duration,
                priority=prio_int,
                pet=pet_obj,
                recur_days=int(n_interval) if is_recurring else 0,
                user_start_time=task_time.strip(),
            )
            if is_recurring:
                owner.schedule_recurring(base_task, task_date, int(n_occurrences), int(n_interval))
                st.session_state.tasks.append({
                    "pet": label,
                    "title": task_title,
                    "duration_minutes": effective_duration,
                    "priority": priority,
                    "date": str(task_date),
                    "recurring": True,
                    "recur_days": int(n_interval),
                    "recur_remaining": int(n_occurrences) - 1,
                    "start_time": task_time.strip(),
                    "group_id": group_id,
                })
            else:
                owner.schedule_task(base_task, task_date)
                st.session_state.tasks.append({
                    "pet": label,
                    "title": task_title,
                    "duration_minutes": effective_duration,
                    "priority": priority,
                    "date": str(task_date),
                    "recurring": False,
                    "start_time": task_time.strip(),
                    "group_id": group_id,
                })
            for msg in _check_conflicts(owner, task_date):
                st.warning(msg)
        st.rerun()

# ---------------------------------------------------------------------------
# Helper: spawn the next recurring occurrence when one is marked complete
# ---------------------------------------------------------------------------
def _spawn_next_occurrence(owner, st_task):
    """Spawn the next occurrence of a recurring task.

    If the completed task belonged to a group (multi-pet submission), all
    siblings in that group share a new group_id so the schedule resolver
    keeps them at the same time slot.  We only spawn once per group — if a
    sibling was already spawned in this rerun (detected by the presence of a
    matching entry for the next date) we skip it.
    """
    if not st_task.get("recurring") or st_task.get("recur_remaining", 0) <= 0:
        return

    next_date = date.fromisoformat(st_task["date"]) + timedelta(days=st_task["recur_days"])
    next_date_str = str(next_date)

    def _is_already_spawned(title, pet_label, date_str):
        return any(
            t["title"] == title and t["pet"] == pet_label and t["date"] == date_str and not t.get("completed")
            for t in st.session_state.tasks
        )

    # Avoid double-spawning when this function is called for each sibling in a group
    if _is_already_spawned(st_task["title"], st_task["pet"], next_date_str):
        return

    orig_group_id = st_task.get("group_id")

    # Find all completed siblings in the same group (same group_id, same date, same title)
    if orig_group_id:
        siblings = [
            t for t in st.session_state.tasks
            if t.get("group_id") == orig_group_id
            and t["title"] == st_task["title"]
            and t["date"] == st_task["date"]
            and t.get("completed")
            and t.get("recur_remaining", 0) > 0
        ]
    else:
        siblings = [st_task]

    import uuid
    new_group_id = str(uuid.uuid4()) if len(siblings) > 1 else None

    for sibling in siblings:
        pet_obj = next((p for p in owner.pets if f"{p.name} ({p.breed})" == sibling["pet"]), None)
        if pet_obj is None:
            continue
        new_backend = Task(
            name=sibling["title"],
            duration=sibling["duration_minutes"],
            priority={"high": 3, "medium": 2, "low": 1}[sibling["priority"]],
            pet=pet_obj,
            recur_days=sibling["recur_days"],
            recur_remaining=sibling["recur_remaining"] - 1,
            user_start_time=sibling["start_time"],
        )
        owner.schedule_task(new_backend, next_date)
        st.session_state.tasks.append({
            "pet": sibling["pet"],
            "title": sibling["title"],
            "duration_minutes": sibling["duration_minutes"],
            "priority": sibling["priority"],
            "date": next_date_str,
            "recurring": True,
            "recur_days": sibling["recur_days"],
            "recur_remaining": sibling["recur_remaining"] - 1,
            "start_time": sibling["start_time"],
            "group_id": new_group_id,
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

    # Collapse tasks that share a group_id into a single display row.
    # Solo tasks (group_id=None) each become their own row keyed by their index.
    seen_groups = set()
    display_rows = []  # list of (row_key, [indices], representative_task)
    for i, t in enumerate(st.session_state.tasks):
        gid = t.get("group_id")
        if gid:
            if gid in seen_groups:
                continue
            seen_groups.add(gid)
            indices = [j for j, x in enumerate(st.session_state.tasks) if x.get("group_id") == gid]
            display_rows.append((f"grp_{gid}", indices, t))
        else:
            display_rows.append((f"solo_{i}", [i], t))

    # Apply filters
    def _row_matches(indices, t):
        if filter_pet != "All" and not any(st.session_state.tasks[j]["pet"] == filter_pet for j in indices):
            return False
        completed = all(st.session_state.tasks[j].get("completed") for j in indices)
        if filter_status == "Done" and not completed:
            return False
        if filter_status in ("All", "Pending") and completed:
            return False
        return True

    visible_rows = [(rk, indices, rep) for rk, indices, rep in display_rows if _row_matches(indices, rep)]

    if not visible_rows:
        st.info("No tasks match the current filters.")

    for row_key, indices, rep in visible_rows:
        members = [st.session_state.tasks[j] for j in indices]
        completed = all(m.get("completed") for m in members)
        pets_label = ", ".join(m["pet"] for m in members)
        label = f"~~{rep['title']}~~" if completed else rep["title"]
        recur_badge = " 🔁" if rep.get("recurring") else ""
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            st.write(f"**{pets_label}** | {label}{recur_badge} | {rep['date']} | {rep['duration_minutes']} min | {rep['priority']}")
        with c2:
            if not completed:
                if st.button("Done", key=f"done_{row_key}"):
                    for j in indices:
                        t = st.session_state.tasks[j]
                        for plan in owner.scheduler.plans:
                            for task in plan.tasks:
                                if task.name == t["title"] and f"{plan.pet.name} ({plan.pet.breed})" == t["pet"] and str(plan.date) == t["date"]:
                                    task.mark_complete()
                        st.session_state.tasks[j]["completed"] = True
                    # Spawn next occurrence using the first member (sibling detection handles the rest)
                    _spawn_next_occurrence(owner, st.session_state.tasks[indices[0]])
                    st.rerun()
            else:
                st.write("✓ Done")
        with c3:
            if st.button("Delete", key=f"del_{row_key}"):
                tasks_to_cancel = []
                for j in indices:
                    t = st.session_state.tasks[j]
                    for plan in owner.scheduler.plans:
                        for task in list(plan.tasks):
                            pet_label_str = f"{plan.pet.name} ({plan.pet.breed})"
                            if task.name == t["title"] and pet_label_str == t["pet"] and str(plan.date) == t["date"]:
                                tasks_to_cancel.append(task)
                for task in tasks_to_cancel:
                    owner.cancel_task(task)
                for j in sorted(indices, reverse=True):
                    t = st.session_state.tasks[j]
                    date_key = t.get("date")
                    slot = t.get("start_time")
                    if date_key and slot:
                        st.session_state.booked_slots.get(date_key, set()).discard(slot)
                    st.session_state.tasks.pop(j)
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
                original = candidate
                candidate = _find_free_slot(candidate, task.duration, placed_windows, gid)
                if candidate != original:
                    original_str = f"{(original // 60) % 24:02d}:{original % 60:02d}"
                    moved_str = f"{(candidate // 60) % 24:02d}:{candidate % 60:02d}"
                    st.warning(f"⚠️ **{task.name}** ({pet.name}) — scheduled time changed from {original_str} to **{moved_str}** due to overlap.")
                if gid:
                    assigned_group_time[gid] = candidate

            placed_windows.append((candidate, candidate + task.duration, gid))
            task.start_time = f"{(candidate // 60) % 24:02d}:{candidate % 60:02d}"

            # Notify if final scheduled time differs from what the user originally requested
            if task.user_start_time and task.start_time != task.user_start_time:
                st.info(f"ℹ️ **{task.name}** ({pet.name}) requested at {task.user_start_time}, scheduled at **{task.start_time}**.")

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
                                _spawn_next_occurrence(owner, st_task)
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
