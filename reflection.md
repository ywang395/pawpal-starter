# PawPal+ Project Reflection

## 1. System Design

### a. Initial design

My original design centered on three main classes: `Owner`, `Pet`, and `Task`. I knew I needed a way to represent who the owner was, which pets belonged to that owner, and what care tasks had to be completed. I also expected to need a `DailyPlan` class to hold the tasks for a specific day and a `Scheduler` class to control the logic for building a plan.

At the beginning, the design was simpler than the final result. I thought of tasks mostly as generic pet-care items with a name, duration, priority, and category. I had not yet worked out how tasks would attach to a specific pet in a multi-pet household, how start times would be stored after scheduling, or how recurring tasks would be represented.

### b. Design changes

The final implementation required several important changes to make the system realistic and maintainable:

1. `Task` gained `pet`, `start_time`, `completed`, `recur_days`, `recur_remaining`, and `user_start_time`.
These fields made the model much more expressive. A task now knows which pet it belongs to, when it is scheduled, whether it is done, and whether it should recur.

2. `DailyPlan` gained a `pet` field.
This made each plan clearly belong to one pet on one date, which avoided ambiguity when the owner has multiple pets.

3. `Preferences.preferred_time` became a `TimeSlot` enum instead of a plain string.
Using an enum made the code safer and easier to reason about because the scheduler only has to support valid values like `MORNING`, `AFTERNOON`, and `EVENING`.

4. `Scheduler` became responsible for more than just plan creation.
It now sorts tasks by time, supports priority-then-time views, detects conflicts, recommends the next available slot, and regenerates plans through `adjust_plan()`. That kept scheduling logic centralized instead of scattering it across the system.

5. `Owner` became the main coordination class.
In the final version, `Owner` not only stores pets and preferences but also routes tasks into the correct `DailyPlan`, handles cancellation, supports lazy recurring scheduling, marks tasks complete through `complete_task()`, and now saves/loads the full system state through JSON persistence.

6. The recurring-task design changed to a lazy model.
Instead of creating every future occurrence up front, the system creates the first occurrence immediately and stores recurrence metadata so the next occurrence can be created after completion. This kept the design simpler and matched the behavior I wanted in the app.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities

My scheduler considers three main constraints:

- Time: tasks need valid start times and should not overlap.
- Priority: higher-priority tasks should be scheduled before lower-priority tasks.
- Preferences: the owner's preferred time of day influences where scheduling starts.

I decided these mattered most because they are the core of what makes a pet-care scheduler useful. If the schedule ignores overlap, it becomes unrealistic. If it ignores priority, important care like medication can be delayed. If it ignores preferences, the schedule may work technically but still feel unhelpful to the user.

The final algorithm schedules pending tasks by descending priority, begins at the owner’s preferred time slot, and places each task at the next available `:00` or `:30` boundary. User-requested start times are also respected as inputs to the scheduling process, and completed tasks are excluded from future rescheduling.

I also added a third algorithmic capability beyond the basic requirements: next-available-slot recommendation. This lets the scheduler calculate the next open time for a given pet, date, and duration based on the current occupied windows. It made the system feel more assistant-like instead of only reactive.

### b. Tradeoffs

One tradeoff I made was scheduling around 30-minute boundaries. This simplified placement and made the schedule easier to read in the UI, but it also reduced precision. For example, a task requested at `07:05` is rounded to the next half-hour boundary, which is easier to manage algorithmically but less exact than a real-world calendar.

Another tradeoff was choosing lazy recurrence instead of generating all future tasks immediately. Lazy recurrence kept the data model smaller and made it easier to reason about what is currently active, but it also means future recurring tasks do not appear until the current one is completed.

I also chose to keep scheduling logic in the backend model rather than fully duplicating it in the UI. This made the system architecture cleaner because the `Scheduler` stays the source of truth, even though the UI still has some display-specific logic layered on top.

## 3. AI Collaboration

### a. How I used AI

I used AI mostly for design brainstorming, refactoring support, edge-case analysis, and test planning. VS Code Copilot was especially helpful when I was trying to translate high-level scheduling ideas into concrete class responsibilities and method signatures. It was also useful for suggesting test cases that I might forget, such as sorting correctness, conflict detection, and recurrence behavior.

The Copilot features that were most effective for building my scheduler were:

- Chat for reasoning through class relationships and method responsibilities.
- Inline code suggestions for repetitive test-writing patterns.
- Codebase-aware prompting for checking whether the implementation and tests were still consistent.
- Agent-style delegation for scoping persistence and advanced scheduling changes before integrating them into the main codebase.

The most helpful prompts were specific and architectural, not just “write code.” Prompts like “what edge cases does this scheduler need to handle?” or “how should recurrence be represented without creating future tasks immediately?” produced better results than broad prompts.

### b. Judgment and verification

One AI suggestion I rejected or modified was the idea of treating recurrence as eager by generating all future occurrences as soon as `schedule_recurring()` was called. That approach would have worked, but it did not match the simpler lazy-recurring model I wanted. Instead, I kept the design clean by storing `recur_days` and `recur_remaining` on the task and only spawning the next occurrence after completion.

I verified AI suggestions by comparing them against the actual code design, the project requirements, and the test suite. If a suggestion introduced extra complexity or created behavior that conflicted with my intended model, I changed it rather than accepting it directly.

Using separate chat sessions for different phases helped me stay organized because each conversation had a clear purpose. One session was better for system design and UML thinking, another for implementation details, and another for testing and debugging. That separation reduced context overload and made it easier to evaluate whether AI output was relevant to the phase I was working on.

The biggest thing I learned about being the “lead architect” with powerful AI tools is that AI can generate many possible solutions quickly, but it does not automatically choose the right system boundaries for you. I still had to decide what the source of truth should be, what tradeoffs were acceptable, and when to keep the design simple. In that sense, the architect’s job became even more important: AI accelerated the work, but I still had to define the direction and protect the coherence of the system.

### c. Agent Mode and prompt comparison

For the persistence and advanced scheduling upgrade, I used Agent Mode to delegate the reconnaissance and planning pass for `pawpal_system.py` and `app.py`. The agent was helpful for mapping the insertion points for `save_to_json`, `load_from_json`, and the UI startup flow. Even though I ended up integrating the final patch locally after a patch mismatch, the delegation still helped me keep the work structured and file-scoped.

For prompt comparison, I used a complex scheduling question about how to support weekly rescheduling and persistence-friendly recurrence metadata. In this environment I only had OpenAI-based models available, so I compared the main model’s answer against a smaller agent model rather than an external Claude or Gemini run. The stronger model gave the more modular and Pythonic answer because it separated recurrence metadata, scheduling decisions, and persistence concerns cleanly, while the smaller model was useful for reconnaissance but less strong on final architecture. That comparison reinforced an important lesson: model strength matters, but clear ownership and system boundaries matter even more.

## 4. Testing and Verification

### a. What I tested

I tested the behaviors that mattered most to the scheduler:

- task addition and removal
- chronological sorting
- priority-based scheduling
- priority-then-time display behavior
- overlap prevention
- conflict detection
- next-available-slot recommendation
- multi-pet and multi-date behavior
- completion tracking
- deletion and rescheduling
- lazy recurring-task behavior
- JSON persistence across save/load cycles

These tests were important because scheduling systems can appear to work in simple demos while still failing in edge cases. The tests helped confirm that tasks are ordered correctly, conflicts are handled predictably, and recurrence works the way I intended.

### b. Confidence

I am fairly confident that the scheduler works correctly for the core scenarios I built and tested. The current suite passes and covers the main scheduling flows, which gives me confidence in the backend behavior.

If I had more time, I would test more UI-level and end-to-end cases, especially around duplicate task names, cross-midnight scheduling, and more complex multi-pet recurring scenarios.

## 5. Reflection

### a. What went well

The part I am most satisfied with is that the final system feels more like a real scheduling model than a basic task list. The combination of `Owner`, `Scheduler`, `DailyPlan`, and `Task` ended up being clear and practical, and the lazy recurrence behavior made the design simpler without losing usefulness.

### b. What I would improve

If I had another iteration, I would improve the UI-to-backend consistency even more and give tasks unique IDs so actions like marking done or deleting are matched more robustly than by title and date alone. I would also consider a richer scheduling model that handles arbitrary minute precision instead of rounding to half-hour boundaries.

### c. Key takeaway

One important thing I learned is that good system design is not just about adding features. It is about deciding where logic belongs, which abstractions are worth keeping, and which tempting ideas should be simplified. Working with AI reinforced that lesson because the strongest results came from using AI as a collaborator, not as a replacement for judgment.
