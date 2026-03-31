import unittest
from pathlib import Path

import pandas as pd

from timetable_automation.main import Scheduler


class TestRoomCollisionGuards(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = Path("tests/test_data")
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        self.slots_file = self.test_data_dir / "collision_slots.csv"
        self.rooms_file = self.test_data_dir / "collision_rooms.csv"
        self.core_courses_file = self.test_data_dir / "collision_core_courses.csv"
        self.elective_courses_file = self.test_data_dir / "collision_elective_courses.csv"

        pd.DataFrame(
            [
                {"Start_Time": "09:00", "End_Time": "10:00"},
            ]
        ).to_csv(self.slots_file, index=False)

        pd.DataFrame(
            [
                {"Room_ID": "C101", "Capacity": 120, "Type": "Classroom"},
                {"Room_ID": "C102", "Capacity": 120, "Type": "Classroom"},
            ]
        ).to_csv(self.rooms_file, index=False)

        pd.DataFrame(
            [
                {
                    "Course_Code": "CR3",
                    "Course_Title": "Core Room Guard",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Faculty": "Prof Core",
                    "Semester_Half": "1",
                    "Elective": "0",
                    "Students": 70,
                    "basket": 0,
                }
            ]
        ).to_csv(self.core_courses_file, index=False)

        pd.DataFrame(
            [
                {
                    "Course_Code": "EL1",
                    "Course_Title": "Shared Elective EL1",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Faculty": "Prof Elective",
                    "Semester_Half": "1",
                    "Elective": "1",
                    "Students": 70,
                    "basket": 1,
                }
            ]
        ).to_csv(self.elective_courses_file, index=False)

    def tearDown(self):
        for file_path in (
            self.slots_file,
            self.rooms_file,
            self.core_courses_file,
            self.elective_courses_file,
        ):
            try:
                Path(file_path).unlink()
            except FileNotFoundError:
                pass

    def test_core_room_availability_checks_elective_usage(self):
        shared_room_usage = {}
        shared_elective_room_usage = {
            "First_Half": {
                "Monday": {
                    "09:00-10:00": {"C101": ("1", "First_Half", "__CODE__", "EL1")}
                }
            }
        }

        scheduler = Scheduler(
            str(self.slots_file),
            str(self.core_courses_file),
            str(self.rooms_file),
            shared_room_usage,
            global_elective_room_usage=shared_elective_room_usage,
        )

        is_free = scheduler._is_room_available(
            "Monday",
            ["09:00-10:00"],
            "C101",
            sheet_name="First_Half",
        )
        self.assertFalse(is_free)

    def test_preferred_elective_room_does_not_override_core_booking(self):
        shared_room_usage = {
            "First_Half": {
                "Monday": {
                    "09:00-10:00": ["C101"],
                }
            }
        }
        shared_elective_room_usage = {}
        shared_elective_room_templates = {
            ("1", "First_Half", "__CODE__", "EL1"): "C101",
        }

        scheduler = Scheduler(
            str(self.slots_file),
            str(self.elective_courses_file),
            str(self.rooms_file),
            shared_room_usage,
            dept_name="CSE-1-A",
            global_elective_room_usage=shared_elective_room_usage,
            global_elective_room_templates=shared_elective_room_templates,
        )

        scheduler.electives_by_sheet["First_Half"] = [(1, scheduler.courses[0])]
        scheduler.scheduled_entries = [
            {
                "sheet": "First_Half",
                "day": "Monday",
                "slot": "09:00-10:00",
                "code": "Elective_1",
                "display": "Elective_1",
                "faculty": scheduler.courses[0].faculty,
                "room": "",
            }
        ]

        scheduler._compute_elective_room_assignments_legally("First_Half")
        assigned_room = scheduler.elective_room_assignment["First_Half"][
            "Elective_1||Shared Elective EL1"
        ]

        self.assertEqual(assigned_room, "C102")


if __name__ == "__main__":
    unittest.main()
