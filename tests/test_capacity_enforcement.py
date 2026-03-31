import unittest
from pathlib import Path

import pandas as pd

from timetable_automation.main import Scheduler


class TestCapacityEnforcement(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = Path("tests/test_data")
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        self.slots_file = self.test_data_dir / "capacity_slots.csv"
        self.courses_file = self.test_data_dir / "capacity_courses.csv"
        self.rooms_file = self.test_data_dir / "capacity_rooms.csv"

        pd.DataFrame([{"Start_Time": "09:00", "End_Time": "10:00"}]).to_csv(
            self.slots_file, index=False
        )
        pd.DataFrame(
            [
                {
                    "Course_Code": "CS161",
                    "Course_Title": "Problem Solving",
                    "Faculty": "Dr. X",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Semester_Half": "1",
                    "Elective": "0",
                    "Students": 300,
                    "is_combined": 0,
                }
            ]
        ).to_csv(self.courses_file, index=False)

    def tearDown(self):
        for f in (self.slots_file, self.courses_file, self.rooms_file):
            try:
                Path(f).unlink()
            except FileNotFoundError:
                pass

    def test_non_combined_course_uses_its_own_strength_for_capacity(self):
        pd.DataFrame(
            [
                {"Room_ID": "C101", "Capacity": 96, "Type": "Classroom"},
                {"Room_ID": "C102", "Capacity": 360, "Type": "Classroom"},
            ]
        ).to_csv(self.rooms_file, index=False)

        sched = Scheduler(
            str(self.slots_file), str(self.courses_file), str(self.rooms_file), {}
        )
        course = sched.courses[0]

        required_capacity = sched._required_capacity_for_course(
            course, is_elective=False, is_combined=False
        )
        self.assertEqual(required_capacity, 300)

    def test_non_combined_course_not_assigned_to_small_room(self):
        pd.DataFrame(
            [{"Room_ID": "C101", "Capacity": 96, "Type": "Classroom"}]
        ).to_csv(self.rooms_file, index=False)

        sched = Scheduler(
            str(self.slots_file), str(self.courses_file), str(self.rooms_file), {}
        )
        course = sched.courses[0]
        required_capacity = sched._required_capacity_for_course(
            course, is_elective=False, is_combined=False
        )

        room = sched._pick_room_for_slots(
            day="Monday",
            slots=[sched.slots[0]],
            code=course.code,
            session_type="L",
            min_capacity_needed=required_capacity,
            is_compulsory=True,
        )
        self.assertEqual(room, "")


if __name__ == "__main__":
    unittest.main()
