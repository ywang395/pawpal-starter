# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.


## Smarter Scheduling

The scheduling engine in `pawpal_system.py` goes beyond a simple task list:

- **Priority-first ordering** — tasks are sorted by descending priority before slot assignment, so high-priority care (e.g. medication) is always placed first.
- **Overlap-free placement** — each task is placed at the next free `:00` or `:30` boundary using half-open interval checks, guaranteeing no two tasks share the same time window.
- **User-pinned start times** — a task can carry a `user_start_time` that anchors it to an exact slot; auto-scheduled tasks flow around pinned ones without displacing them.
- **Recurring task support** — `schedule_recurring()` stamps the first occurrence onto the calendar and records the repeat interval (`recur_days`) and remaining count (`recur_remaining`) on the task, ready for a background process to spawn future copies.
- **Conflict detection** — `Scheduler.detect_conflicts()` scans a plan and returns every overlapping task pair, making it easy to surface scheduling problems in the UI.
- **Live re-scheduling** — adding or removing a task triggers `adjust_plan()`, which reruns the full schedule so the displayed plan is always consistent.

## Testing PawPal+

Run the automated test suite with:

```bash
python -m pytest
```

The tests cover core scheduling behaviors including chronological task ordering, priority-based scheduling, overlap prevention, conflict detection, task completion, deletion and rescheduling, pet and multi-date plan management, and lazy recurring-task behavior where the next occurrence is created after the current one is completed.

**Confidence Level:** 4/5 stars. The current suite passes (`77 passed`) and gives strong coverage of the main scheduling flows and edge cases, though the app would still benefit from deeper UI-level and end-to-end testing for additional confidence.
