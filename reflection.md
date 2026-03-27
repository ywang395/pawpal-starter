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

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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
