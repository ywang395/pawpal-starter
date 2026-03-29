import unittest
from datetime import date, timedelta
from pathlib import Path
import tempfile
from pawpal_system import (
    Owner, Pet, Task, Preferences, DailyPlan, Scheduler,
    TimeSlot, _add_minutes,
)


def make_owner(name="Jordan", preferred_time=TimeSlot.MORNING):
    prefs = Preferences(preferred_time=preferred_time)
    return Owner(name=name, owner_info="", preferences=prefs)


def make_pet(owner, name="Mochi"):
    return owner.add_pet(name=name, age=3, breed="Shiba Inu")


def make_task(name="Morning walk", pet=None, duration=20, priority=2):
    return Task(name=name, duration=duration, priority=priority, pet=pet)


# ---------------------------------------------------------------------------
# Task Completion
# ---------------------------------------------------------------------------

class TestTaskCompletion(unittest.TestCase):

    def test_task_starts_incomplete(self):
        task = make_task()
        self.assertFalse(task.completed)

    def test_mark_complete_sets_completed_true(self):
        task = make_task()
        task.mark_complete()
        self.assertTrue(task.completed)

    def test_mark_complete_is_idempotent(self):
        task = make_task()
        task.mark_complete()
        task.mark_complete()
        self.assertTrue(task.completed)

    def test_completing_one_task_does_not_affect_another(self):
        task_a = make_task("Walk")
        task_b = make_task("Feed")
        task_a.mark_complete()
        self.assertFalse(task_b.completed)


# ---------------------------------------------------------------------------
# Task Addition
# ---------------------------------------------------------------------------

class TestTaskAddition(unittest.TestCase):

    def test_adding_task_increases_plan_task_count(self):
        owner = make_owner()
        pet = make_pet(owner)
        plan = DailyPlan(date.today(), pet)
        task = make_task(pet=pet)
        self.assertEqual(len(plan.tasks), 0)
        plan.add_task(task)
        self.assertEqual(len(plan.tasks), 1)

    def test_adding_multiple_tasks_increases_count_correctly(self):
        owner = make_owner()
        pet = make_pet(owner)
        plan = DailyPlan(date.today(), pet)
        for i in range(3):
            plan.add_task(make_task(name=f"Task {i}", pet=pet))
        self.assertEqual(len(plan.tasks), 3)

    def test_schedule_task_via_owner_adds_to_plan(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_task(task, date.today())
        plan = owner.view_schedule()
        self.assertIn(task, plan.tasks)

    def test_duplicate_task_is_added_twice(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_task(task, date.today())
        owner.schedule_task(task, date.today())
        plan = owner.view_schedule()
        self.assertEqual(len(plan.tasks), 2)

    def test_tasks_for_different_pets_go_into_separate_plans(self):
        owner = make_owner()
        mochi = make_pet(owner, "Mochi")
        boba = make_pet(owner, "Boba")
        owner.schedule_task(make_task("Walk", pet=mochi), date.today())
        owner.schedule_task(make_task("Feed", pet=boba), date.today())
        self.assertEqual(len(owner.scheduler.plans), 2)


# ---------------------------------------------------------------------------
# Task Removal
# ---------------------------------------------------------------------------

class TestTaskRemoval(unittest.TestCase):

    def test_remove_task_from_plan(self):
        owner = make_owner()
        pet = make_pet(owner)
        plan = DailyPlan(date.today(), pet)
        task = make_task(pet=pet)
        plan.add_task(task)
        plan.remove_task(task)
        self.assertNotIn(task, plan.tasks)

    def test_remove_nonexistent_task_does_not_raise(self):
        owner = make_owner()
        pet = make_pet(owner)
        plan = DailyPlan(date.today(), pet)
        task = make_task(pet=pet)
        plan.remove_task(task)

    def test_cancel_task_removes_it_from_owner_plan(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_task(task, date.today())
        owner.cancel_task(task)
        # Plan is removed when it becomes empty
        self.assertIsNone(owner.view_schedule())

    def test_cancel_task_not_in_any_plan_does_nothing(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.cancel_task(task)


# ---------------------------------------------------------------------------
# Pet Management
# ---------------------------------------------------------------------------

class TestPetManagement(unittest.TestCase):

    def test_add_pet_links_owner_name(self):
        owner = make_owner()
        pet = make_pet(owner)
        self.assertEqual(pet.owner_name, "Jordan")

    def test_add_multiple_pets(self):
        owner = make_owner()
        make_pet(owner, "Mochi")
        make_pet(owner, "Boba")
        self.assertEqual(len(owner.pets), 2)

    def test_remove_pet_removes_from_owner(self):
        owner = make_owner()
        pet = make_pet(owner)
        owner.remove_pet(pet)
        self.assertNotIn(pet, owner.pets)

    def test_remove_pet_clears_its_plans(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_task(task, date.today())
        owner.remove_pet(pet)
        pet_plans = [p for p in owner.scheduler.plans if p.pet == pet]
        self.assertEqual(len(pet_plans), 0)

    def test_remove_pet_does_not_affect_other_pets_plans(self):
        owner = make_owner()
        mochi = make_pet(owner, "Mochi")
        boba = make_pet(owner, "Boba")
        owner.schedule_task(make_task("Walk", pet=mochi), date.today())
        owner.schedule_task(make_task("Feed", pet=boba), date.today())
        owner.remove_pet(mochi)
        boba_plans = [p for p in owner.scheduler.plans if p.pet == boba]
        self.assertEqual(len(boba_plans), 1)

    def test_remove_pet_not_in_list_does_nothing(self):
        owner = make_owner()
        pet = Pet(name="Ghost", age=1, breed="Unknown")
        owner.remove_pet(pet)


# ---------------------------------------------------------------------------
# Scheduling Logic
# ---------------------------------------------------------------------------

class TestSchedulingLogic(unittest.TestCase):

    def test_higher_priority_scheduled_before_lower(self):
        owner = make_owner()
        pet = make_pet(owner)
        low  = make_task("Low task",  pet=pet, priority=1)
        high = make_task("High task", pet=pet, priority=3)
        owner.schedule_task(low, date.today())
        owner.schedule_task(high, date.today())
        plan = owner.view_schedule()
        names = [t.name for t in plan.view_plan()]
        self.assertLess(names.index("High task"), names.index("Low task"))

    def test_start_times_are_assigned(self):
        owner = make_owner()
        pet = make_pet(owner)
        owner.schedule_task(make_task(pet=pet), date.today())
        plan = owner.view_schedule()
        for task in plan.view_plan():
            self.assertIsNotNone(task.start_time)

    def test_start_times_do_not_overlap(self):
        owner = make_owner()
        pet = make_pet(owner)
        for i in range(3):
            owner.schedule_task(make_task(name=f"Task {i}", pet=pet, duration=30), date.today())
        plan = owner.view_schedule()
        times = [t.start_time for t in plan.view_plan()]
        self.assertEqual(len(times), len(set(times)))

    def test_view_plan_returns_tasks_in_chronological_order(self):
        owner = make_owner()
        pet = make_pet(owner)
        early = make_task("Breakfast", pet=pet, duration=15, priority=1)
        late = make_task("Evening walk", pet=pet, duration=30, priority=1)
        middle = make_task("Lunch", pet=pet, duration=20, priority=1)
        early.start_time = "07:00"
        late.start_time = "17:00"
        middle.start_time = "12:30"
        plan = DailyPlan(date.today(), pet)
        plan.add_task(late)
        plan.add_task(early)
        plan.add_task(middle)
        self.assertEqual(
            [t.name for t in plan.view_plan()],
            ["Breakfast", "Lunch", "Evening walk"],
        )

    def test_morning_preference_starts_at_0700(self):
        owner = make_owner(preferred_time=TimeSlot.MORNING)
        pet = make_pet(owner)
        owner.schedule_task(make_task(pet=pet), date.today())
        plan = owner.view_schedule()
        self.assertEqual(plan.view_plan()[0].start_time, "07:00")

    def test_afternoon_preference_starts_at_1200(self):
        owner = make_owner(preferred_time=TimeSlot.AFTERNOON)
        pet = make_pet(owner)
        owner.schedule_task(make_task(pet=pet), date.today())
        plan = owner.view_schedule()
        self.assertEqual(plan.view_plan()[0].start_time, "12:00")

    def test_evening_preference_starts_at_1700(self):
        owner = make_owner(preferred_time=TimeSlot.EVENING)
        pet = make_pet(owner)
        owner.schedule_task(make_task(pet=pet), date.today())
        plan = owner.view_schedule()
        self.assertEqual(plan.view_plan()[0].start_time, "17:00")

    def test_schedule_task_with_no_pet_and_no_owner_pets_does_nothing(self):
        owner = make_owner()
        task = make_task()
        owner.schedule_task(task, date.today())
        self.assertEqual(len(owner.scheduler.plans), 0)

    def test_schedule_task_without_pet_falls_back_to_first_owner_pet(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task()
        owner.schedule_task(task, date.today())
        plan = owner.view_schedule()
        self.assertIn(task, plan.tasks)


# ---------------------------------------------------------------------------
# Multi-date Scheduling
# ---------------------------------------------------------------------------

class TestMultiDateScheduling(unittest.TestCase):

    def test_tasks_on_different_dates_go_into_separate_plans(self):
        owner = make_owner()
        pet = make_pet(owner)
        today = date.today()
        tomorrow = today + timedelta(days=1)
        owner.schedule_task(make_task("Walk today", pet=pet), today)
        owner.schedule_task(make_task("Walk tomorrow", pet=pet), tomorrow)
        self.assertEqual(len(owner.scheduler.plans), 2)

    def test_view_schedule_returns_todays_plan(self):
        owner = make_owner()
        pet = make_pet(owner)
        today = date.today()
        yesterday = today - timedelta(days=1)
        owner.schedule_task(make_task("Yesterday task", pet=pet), yesterday)
        owner.schedule_task(make_task("Today task", pet=pet), today)
        plan = owner.view_schedule()
        self.assertEqual(plan.date, today)

    def test_view_schedule_returns_none_when_no_plans(self):
        owner = make_owner()
        self.assertIsNone(owner.view_schedule())

    def test_schedule_recurring_creates_only_one_task(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_recurring(task, date.today(), occurrences=3, interval_days=1)
        self.assertEqual(len(owner.scheduler.plans), 1)
        plan = owner.scheduler.plans[0]
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].recur_remaining, 2)

    def test_schedule_recurring_first_task_carries_recur_days(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_recurring(task, date.today(), occurrences=5, interval_days=3)
        plan = owner.scheduler.plans[0]
        self.assertEqual(plan.tasks[0].recur_days, 3)
        self.assertEqual(plan.tasks[0].recur_remaining, 4)

    def test_completing_daily_recurring_task_creates_next_day_task(self):
        owner = make_owner()
        pet = make_pet(owner)
        today = date.today()
        tomorrow = today + timedelta(days=1)
        task = make_task("Daily walk", pet=pet, duration=30, priority=2)
        owner.schedule_recurring(task, today, occurrences=3, interval_days=1)

        today_plan = owner.scheduler.plans[0]
        first_task = today_plan.tasks[0]
        owner.complete_task(first_task)

        plan_dates = sorted(p.date for p in owner.scheduler.plans)
        self.assertEqual(plan_dates, [today, tomorrow])
        tomorrow_plan = next(p for p in owner.scheduler.plans if p.date == tomorrow)
        self.assertEqual(len(tomorrow_plan.tasks), 1)
        self.assertEqual(tomorrow_plan.tasks[0].name, "Daily walk")
        self.assertEqual(tomorrow_plan.tasks[0].recur_remaining, 1)

    def test_next_available_slot_skips_existing_window(self):
        owner = make_owner()
        pet = make_pet(owner)
        owner.schedule_task(make_task("Breakfast", pet=pet, duration=30, priority=3), date.today())
        suggested = owner.next_available_slot(date.today(), duration=20, pet=pet)
        self.assertEqual(suggested, "07:30")

    def test_save_and_load_json_preserves_owner_pet_and_task_data(self):
        owner = make_owner(name="Jordan")
        pet = make_pet(owner)
        owner.schedule_task(
            Task(
                name="Morning walk",
                duration=30,
                priority=3,
                pet=pet,
                user_start_time="07:00",
            ),
            date.today(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data.json"
            owner.save_to_json(str(data_path))
            restored = Owner.load_from_json(str(data_path))

        self.assertIsNotNone(restored)
        self.assertEqual(restored.name, owner.name)
        self.assertEqual(len(restored.pets), 1)
        self.assertEqual(restored.pets[0].name, "Mochi")
        self.assertEqual(len(restored.scheduler.plans), 1)
        restored_task = restored.scheduler.plans[0].tasks[0]
        self.assertEqual(restored_task.name, "Morning walk")
        self.assertEqual(restored_task.priority, 3)
        self.assertEqual(restored_task.user_start_time, "07:00")


# ---------------------------------------------------------------------------
# Scheduler: create_daily_plan and handle_conflict
# ---------------------------------------------------------------------------

class TestScheduler(unittest.TestCase):

    def test_create_daily_plan_reuses_existing_plan(self):
        owner = make_owner()
        pet = make_pet(owner)
        today = date.today()
        plan1 = owner.scheduler.create_daily_plan(today, pet)
        plan2 = owner.scheduler.create_daily_plan(today, pet)
        self.assertIs(plan1, plan2)

    def test_handle_conflict_allows_same_name_and_pet(self):
        owner = make_owner()
        pet = make_pet(owner)
        plan = DailyPlan(date.today(), pet)
        task1 = make_task("Walk", pet=pet)
        task2 = make_task("Walk", pet=pet)
        owner.scheduler.handle_conflict(task1, plan)
        owner.scheduler.handle_conflict(task2, plan)
        self.assertEqual(len(plan.tasks), 2)

    def test_handle_conflict_allows_same_name_different_pet(self):
        owner = make_owner()
        mochi = make_pet(owner, "Mochi")
        boba  = make_pet(owner, "Boba")
        plan = DailyPlan(date.today(), mochi)
        task1 = make_task("Walk", pet=mochi)
        task2 = make_task("Walk", pet=boba)
        owner.scheduler.handle_conflict(task1, plan)
        owner.scheduler.handle_conflict(task2, plan)
        self.assertEqual(len(plan.tasks), 2)

    def test_adjust_plan_reassigns_start_times(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_task(task, date.today())
        new_task = make_task("Extra task", pet=pet, duration=60)
        owner.schedule_task(new_task, date.today())
        self.assertIsNotNone(task.start_time)

    def test_detect_conflicts_flags_duplicate_start_times(self):
        owner = make_owner()
        pet = make_pet(owner)
        plan = DailyPlan(date.today(), pet)
        walk = make_task("Walk", pet=pet, duration=30, priority=2)
        feed = make_task("Feed", pet=pet, duration=15, priority=1)
        walk.start_time = "07:00"
        feed.start_time = "07:00"
        plan.add_task(walk)
        plan.add_task(feed)
        conflicts = owner.scheduler.detect_conflicts(plan)
        self.assertEqual(conflicts, [(walk, feed)])


# ---------------------------------------------------------------------------
# _add_minutes helper
# ---------------------------------------------------------------------------

class TestAddMinutes(unittest.TestCase):

    def test_add_minutes_basic(self):
        self.assertEqual(_add_minutes("07:00", 30), "07:30")

    def test_add_minutes_crosses_hour(self):
        self.assertEqual(_add_minutes("07:45", 30), "08:15")

    def test_add_minutes_crosses_midnight(self):
        self.assertEqual(_add_minutes("23:45", 30), "00:15")

    def test_add_minutes_zero(self):
        self.assertEqual(_add_minutes("12:00", 0), "12:00")


if __name__ == "__main__":
    unittest.main()
