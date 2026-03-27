import unittest
from datetime import date
from pawpal_system import (
    Owner, Pet, Task, Preferences, DailyPlan,
    Category, TimeSlot,
)


def make_owner():
    prefs = Preferences(
        preferred_time=TimeSlot.MORNING,
        priority_categories=[Category.FEEDING, Category.WALKING],
    )
    return Owner(name="Jordan", owner_info="", preferences=prefs)


def make_pet(owner, name="Mochi"):
    return owner.add_pet(name=name, age=3, breed="Shiba Inu")


def make_task(name="Morning walk", pet=None):
    return Task(name=name, duration=20, priority=2, category=Category.WALKING, pet=pet)


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

    def test_duplicate_task_is_not_added_twice(self):
        owner = make_owner()
        pet = make_pet(owner)
        task = make_task(pet=pet)
        owner.schedule_task(task, date.today())
        owner.schedule_task(task, date.today())   # same task again
        plan = owner.view_schedule()
        self.assertEqual(len(plan.tasks), 1)

    def test_tasks_for_different_pets_go_into_separate_plans(self):
        owner = make_owner()
        mochi = make_pet(owner, "Mochi")
        boba = make_pet(owner, "Boba")
        owner.schedule_task(make_task("Walk", pet=mochi), date.today())
        owner.schedule_task(make_task("Feed", pet=boba), date.today())
        self.assertEqual(len(owner.scheduler.plans), 2)


if __name__ == "__main__":
    unittest.main()
