import unittest

from pydantic import ValidationError

from app.schemas import PlanCreate, TaskCreate


class TestSchemas(unittest.TestCase):
    def test_coordinator_requires_action_or_date(self):
        with self.assertRaises(ValidationError):
            TaskCreate(name="c1", type="coordinator", job_id="job-1")

    def test_bundle_requires_coordinator_or_date(self):
        with self.assertRaises(ValidationError):
            TaskCreate(name="b1", type="bundle", job_id="job-1")

    def test_plan_max_concurrency_bounds(self):
        with self.assertRaises(ValidationError):
            PlanCreate(name="p1", max_concurrency=0)


if __name__ == "__main__":
    unittest.main()
