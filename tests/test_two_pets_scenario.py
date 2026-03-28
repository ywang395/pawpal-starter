"""
Scenario-based tests for PawPal+:
  - Two pets: Mochi (Pon) and Mochi (Shiba Inu)
  - Task for Shiba with MORNING preference
  - Task for Pon with AFTERNOON preference
  - Generate schedule and verify correct start times per pet
  - Repeat task, delete, recreate, mark done, regenerate
"""
import unittest
from datetime import date, timedelta
from pawpal_system import Owner, Task, Preferences, DailyPlan, Scheduler, TimeSlot, _time_to_minutes


TODAY = date.today()


def make_owner():
    prefs = Preferences(preferred_time=TimeSlot.MORNING)
    return Owner(name="Jordan", owner_info="", preferences=prefs)


# ---------------------------------------------------------------------------
# Two-pet setup helpers
# ---------------------------------------------------------------------------

class TestTwoPetSchedule(unittest.TestCase):
    """Mochi (Pon) gets AFTERNOON, Mochi (Shiba Inu) gets MORNING."""

    def setUp(self):
        self.owner = make_owner()
        self.shiba = self.owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")
        self.pon   = self.owner.add_pet(name="Mochi", age=3, breed="Pon")

    def _schedule_shiba(self, name="Walk", duration=30, priority=2):
        """Schedule one task for Shiba with MORNING preference."""
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        task = Task(name=name, duration=duration, priority=priority, pet=self.shiba)
        self.owner.schedule_task(task, TODAY)
        return task

    def _schedule_pon(self, name="Feed", duration=20, priority=2):
        """Schedule one task for Pon with AFTERNOON preference."""
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        task = Task(name=name, duration=duration, priority=priority, pet=self.pon)
        self.owner.schedule_task(task, TODAY)
        return task

    # -----------------------------------------------------------------------
    # Basic separate-plan tests
    # -----------------------------------------------------------------------

    def test_two_same_name_pets_different_breeds_have_separate_plans(self):
        self._schedule_shiba()
        self._schedule_pon()
        self.assertEqual(len(self.owner.scheduler.plans), 2)

    def test_shiba_task_not_in_pon_plan(self):
        shiba_task = self._schedule_shiba()
        self._schedule_pon()
        pon_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Pon")
        self.assertNotIn(shiba_task, pon_plan.tasks)

    def test_pon_task_not_in_shiba_plan(self):
        self._schedule_shiba()
        pon_task = self._schedule_pon()
        shiba_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Shiba Inu")
        self.assertNotIn(pon_task, shiba_plan.tasks)

    # -----------------------------------------------------------------------
    # Preference-based start time tests
    # -----------------------------------------------------------------------

    def test_shiba_task_starts_at_morning_slot(self):
        self._schedule_shiba()
        shiba_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Shiba Inu")
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.scheduler.adjust_plan(shiba_plan)
        task = shiba_plan.view_plan()[0]
        self.assertEqual(task.start_time, "07:00")

    def test_pon_task_starts_at_afternoon_slot(self):
        self._schedule_pon()
        pon_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Pon")
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        self.owner.scheduler.adjust_plan(pon_plan)
        task = pon_plan.view_plan()[0]
        self.assertEqual(task.start_time, "12:00")

    def test_shiba_and_pon_have_different_start_times(self):
        self._schedule_shiba()
        self._schedule_pon()
        shiba_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Shiba Inu")
        pon_plan   = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Pon")
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.scheduler.adjust_plan(shiba_plan)
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        self.owner.scheduler.adjust_plan(pon_plan)
        shiba_time = shiba_plan.view_plan()[0].start_time
        pon_time   = pon_plan.view_plan()[0].start_time
        self.assertNotEqual(shiba_time, pon_time)
        self.assertEqual(shiba_time, "07:00")
        self.assertEqual(pon_time, "12:00")

    # -----------------------------------------------------------------------
    # Multiple tasks — sequential scheduling per pet
    # -----------------------------------------------------------------------

    def test_two_shiba_tasks_scheduled_sequentially(self):
        t1 = self._schedule_shiba("Walk",  duration=30, priority=3)
        t2 = self._schedule_shiba("Brush", duration=20, priority=1)
        shiba_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Shiba Inu")
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.scheduler.adjust_plan(shiba_plan)
        tasks = shiba_plan.view_plan()
        # higher priority first
        self.assertEqual(tasks[0].name, "Walk")
        self.assertEqual(tasks[0].start_time, "07:00")
        # second task starts after first ends, rounded to :00/:30
        first_end = _time_to_minutes("07:00") + 30  # 450 = 07:30
        self.assertEqual(tasks[1].start_time, "07:30")

    def test_no_time_overlap_between_shiba_tasks(self):
        self._schedule_shiba("Walk",  duration=30, priority=3)
        self._schedule_shiba("Brush", duration=20, priority=1)
        shiba_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Shiba Inu")
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.scheduler.adjust_plan(shiba_plan)
        conflicts = self.owner.scheduler.detect_conflicts(shiba_plan)
        self.assertEqual(conflicts, [])

    def test_no_time_overlap_between_pon_tasks(self):
        self._schedule_pon("Feed",  duration=20, priority=2)
        self._schedule_pon("Groom", duration=25, priority=1)
        pon_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Pon")
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        self.owner.scheduler.adjust_plan(pon_plan)
        conflicts = self.owner.scheduler.detect_conflicts(pon_plan)
        self.assertEqual(conflicts, [])


# ---------------------------------------------------------------------------
# Recurring task tests
# ---------------------------------------------------------------------------

class TestRecurringTasks(unittest.TestCase):

    def setUp(self):
        self.owner = make_owner()
        self.shiba = self.owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")

    def test_recurring_creates_correct_number_of_plans(self):
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_recurring(task, TODAY, occurrences=5, interval_days=1)
        self.assertEqual(len(self.owner.scheduler.plans), 5)

    def test_recurring_plans_on_consecutive_dates(self):
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_recurring(task, TODAY, occurrences=3, interval_days=1)
        plan_dates = sorted(p.date for p in self.owner.scheduler.plans)
        expected = [TODAY, TODAY + timedelta(days=1), TODAY + timedelta(days=2)]
        self.assertEqual(plan_dates, expected)

    def test_recurring_every_2_days(self):
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_recurring(task, TODAY, occurrences=3, interval_days=2)
        plan_dates = sorted(p.date for p in self.owner.scheduler.plans)
        expected = [TODAY, TODAY + timedelta(days=2), TODAY + timedelta(days=4)]
        self.assertEqual(plan_dates, expected)

    def test_recurring_tasks_have_start_times_assigned(self):
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_recurring(task, TODAY, occurrences=3, interval_days=1)
        for plan in self.owner.scheduler.plans:
            for t in plan.tasks:
                self.assertIsNotNone(t.start_time)

    def test_recurring_tasks_all_start_at_morning(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_recurring(task, TODAY, occurrences=3, interval_days=1)
        for plan in self.owner.scheduler.plans:
            self.owner.scheduler.adjust_plan(plan)
            self.assertEqual(plan.view_plan()[0].start_time, "07:00")


# ---------------------------------------------------------------------------
# Delete task tests
# ---------------------------------------------------------------------------

class TestDeleteTask(unittest.TestCase):

    def setUp(self):
        self.owner = make_owner()
        self.shiba = self.owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")

    def test_delete_removes_task_from_plan(self):
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(task, TODAY)
        self.owner.cancel_task(task)
        # Plan is removed when it becomes empty
        self.assertIsNone(self.owner.view_schedule())

    def test_delete_one_task_leaves_others(self):
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=1, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.schedule_task(t2, TODAY)
        self.owner.cancel_task(t1)
        plan = self.owner.view_schedule()
        self.assertNotIn(t1, plan.tasks)
        self.assertIn(t2, plan.tasks)

    def test_delete_reschedules_remaining_tasks(self):
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=1, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.schedule_task(t2, TODAY)
        self.owner.cancel_task(t1)
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        # t2 is now the only task, should start at slot start
        self.assertEqual(plan.view_plan()[0].start_time, "07:00")

    def test_delete_nonexistent_task_does_not_raise(self):
        task = Task(name="Ghost", duration=10, priority=1, pet=self.shiba)
        self.owner.cancel_task(task)  # never scheduled — should not raise


# ---------------------------------------------------------------------------
# Recreate task tests
# ---------------------------------------------------------------------------

class TestRecreateTask(unittest.TestCase):

    def setUp(self):
        self.owner = make_owner()
        self.shiba = self.owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")

    def test_recreate_task_after_delete_adds_back(self):
        t1 = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.cancel_task(t1)
        t2 = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(t2, TODAY)
        plan = self.owner.view_schedule()
        self.assertIn(t2, plan.tasks)

    def test_recreated_task_gets_start_time(self):
        t1 = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.cancel_task(t1)
        t2 = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(t2, TODAY)
        plan = self.owner.view_schedule()
        self.assertIsNotNone(plan.view_plan()[0].start_time)

    def test_recreate_with_different_priority_changes_order(self):
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=1, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.schedule_task(t2, TODAY)
        # delete high priority, recreate with low priority
        self.owner.cancel_task(t1)
        t3 = Task(name="Walk", duration=30, priority=1, pet=self.shiba)
        self.owner.schedule_task(t3, TODAY)
        plan = self.owner.view_schedule()
        # both are now priority 1 — no guarantee of order, but no overlap
        conflicts = self.owner.scheduler.detect_conflicts(plan)
        self.assertEqual(conflicts, [])


# ---------------------------------------------------------------------------
# Mark done tests
# ---------------------------------------------------------------------------

class TestMarkDone(unittest.TestCase):

    def setUp(self):
        self.owner = make_owner()
        self.shiba = self.owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")

    def test_done_task_excluded_from_rescheduling(self):
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=1, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.schedule_task(t2, TODAY)
        t1.mark_complete()
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        # t1 is done — start_time cleared, t2 reschedules to slot start
        self.assertIsNone(t1.start_time)
        self.assertEqual(t2.start_time, "07:00")

    def test_done_task_start_time_cleared(self):
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(task, TODAY)
        task.mark_complete()
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        self.assertIsNone(task.start_time)

    def test_done_task_does_not_cause_conflict(self):
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=1, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.schedule_task(t2, TODAY)
        t1.mark_complete()
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        conflicts = self.owner.scheduler.detect_conflicts(plan)
        self.assertEqual(conflicts, [])

    def test_marking_done_does_not_affect_other_pet_plan(self):
        pon = self.owner.add_pet(name="Mochi", age=3, breed="Pon")
        shiba_task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        pon_task   = Task(name="Feed", duration=20, priority=2, pet=pon)
        self.owner.schedule_task(shiba_task, TODAY)
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        self.owner.schedule_task(pon_task, TODAY)
        shiba_task.mark_complete()
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        pon_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Pon")
        self.owner.scheduler.adjust_plan(pon_plan)
        self.assertFalse(pon_task.completed)
        self.assertIsNotNone(pon_task.start_time)


# ---------------------------------------------------------------------------
# Generate schedule tests
# ---------------------------------------------------------------------------

class TestGenerateSchedule(unittest.TestCase):

    def setUp(self):
        self.owner = make_owner()
        self.shiba = self.owner.add_pet(name="Mochi", age=3, breed="Shiba Inu")
        self.pon   = self.owner.add_pet(name="Mochi", age=3, breed="Pon")

    def test_generate_assigns_all_start_times(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.schedule_task(Task(name="Walk",  duration=30, priority=3, pet=self.shiba), TODAY)
        self.owner.schedule_task(Task(name="Brush", duration=20, priority=1, pet=self.shiba), TODAY)
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        for t in plan.view_plan():
            self.assertIsNotNone(t.start_time)

    def test_generate_shiba_morning_pon_afternoon_no_cross_contamination(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.schedule_task(Task(name="Walk", duration=30, priority=2, pet=self.shiba), TODAY)
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        self.owner.schedule_task(Task(name="Feed", duration=20, priority=2, pet=self.pon), TODAY)

        shiba_plan = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Shiba Inu")
        pon_plan   = next(p for p in self.owner.scheduler.plans if p.pet.breed == "Pon")

        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        self.owner.scheduler.adjust_plan(shiba_plan)
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.AFTERNOON)
        self.owner.scheduler.adjust_plan(pon_plan)

        self.assertEqual(shiba_plan.view_plan()[0].start_time, "07:00")
        self.assertEqual(pon_plan.view_plan()[0].start_time, "12:00")

    def test_generate_after_delete_no_overlap(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=2, pet=self.shiba)
        t3 = Task(name="Feed",  duration=15, priority=1, pet=self.shiba)
        for t in [t1, t2, t3]:
            self.owner.schedule_task(t, TODAY)
        self.owner.cancel_task(t2)
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        conflicts = self.owner.scheduler.detect_conflicts(plan)
        self.assertEqual(conflicts, [])

    def test_generate_after_done_task_remaining_tasks_sequential(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        t1 = Task(name="Walk",  duration=30, priority=3, pet=self.shiba)
        t2 = Task(name="Brush", duration=20, priority=1, pet=self.shiba)
        self.owner.schedule_task(t1, TODAY)
        self.owner.schedule_task(t2, TODAY)
        t1.mark_complete()
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        # t2 should now start at 07:00 since t1 is done and cleared
        self.assertEqual(t2.start_time, "07:00")

    def test_generate_priority_order_high_before_low(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        low  = Task(name="Low",  duration=20, priority=1, pet=self.shiba)
        high = Task(name="High", duration=20, priority=3, pet=self.shiba)
        self.owner.schedule_task(low,  TODAY)
        self.owner.schedule_task(high, TODAY)
        plan = self.owner.view_schedule()
        names = [t.name for t in plan.view_plan()]
        self.assertLess(names.index("High"), names.index("Low"))

    def test_generate_multiple_times_is_idempotent(self):
        self.owner.scheduler.preferences = Preferences(preferred_time=TimeSlot.MORNING)
        task = Task(name="Walk", duration=30, priority=2, pet=self.shiba)
        self.owner.schedule_task(task, TODAY)
        plan = self.owner.view_schedule()
        self.owner.scheduler.adjust_plan(plan)
        time_first = task.start_time
        self.owner.scheduler.adjust_plan(plan)
        time_second = task.start_time
        self.assertEqual(time_first, time_second)


if __name__ == "__main__":
    unittest.main()
