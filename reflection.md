# PawPal+ Project Reflection

## 1. System Design

Three core actions :
-Schedule a task / preference.
-cancel a task.
-view schedule and plan.

**a. Initial design**

My first design would be the following:
There would be three classes - Pet, Owner , and Task.
-The Pet class would have basic attributes like name, age, and breed.
-The Owner class would have attributes like name attributes like owner Info, Preferences and a pet or list of pets.
-The Task class would have attributes like name, duration, priority, and Category (Feeding, Walking, Grooming).
-Daily Plan class : This class would be responsible for generating the daily schedule based on the tasks and preferences of the owner. It would have methods to add tasks, remove tasks, and generate the schedule for the day.
-Schedular class : This class would be responsible for managing the overall scheduling process. It would have methods to create and manage daily plans, as well as to handle any conflicts or adjustments that may arise.

**b. Design changes**

Yes, the design changed after reviewing the initial skeleton for missing relationships and logic bottlenecks. The following changes were made:

1. **`Task` gained `pet` and `start_time` fields** — The original `Task` had no link to a `Pet`, making it impossible to know which pet a task belonged to in a multi-pet household. A `start_time` field was also added so `view_plan()` can return a real timed schedule rather than an unordered list.

2. **`DailyPlan` gained a `pet` parameter** — The original `DailyPlan` only held a date and a list of tasks with no ownership context. Adding `pet` makes it clear whose plan is being generated.

3. **`Scheduler` gained a `preferences` parameter** — The original `Scheduler` had no access to `Preferences`, so it could not respect `preferred_time` or `priority_categories` when building a plan. Passing `Preferences` into `__init__` gives the scheduler the context it needs.

4. **`Owner.schedule_task` gained a `plan_date` parameter** — Without a date, the scheduler had no way to route a task to the correct `DailyPlan`.

5. **`Scheduler.handle_conflict` gained a `plan` parameter** — Conflict resolution requires comparing a new task against an existing plan, so the method signature was widened to include the relevant `DailyPlan`.

6. **`Preferences.preferred_time` changed from `str` to a `TimeSlot` enum** — A raw string like `"morning"` is fragile and hard to validate. A `TimeSlot` enum (MORNING, AFTERNOON, EVENING) makes the field safe and self-documenting.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

One tradeoff I made was scheduling tasks in 30-minute blocks. This simplifies the logic and makes it easier to visualize the schedule, but it also means that tasks that take less than 30 minutes may end up blocking a full half-hour slot, potentially reducing overall efficiency. I chose this approach because it strikes a balance between simplicity and flexibility, and it aligns well with common scheduling practices.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
