import unittest
from pathlib import Path

import pandas as pd

from timetable_automation.main import Scheduler


class TestFacultyConflicts(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = Path("tests/test_data")
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        self.slots_file = self.test_data_dir / "faculty_slots.csv"
        self.rooms_file = self.test_data_dir / "faculty_rooms.csv"
        self.courses_a_file = self.test_data_dir / "faculty_courses_a.csv"
        self.courses_b_file = self.test_data_dir / "faculty_courses_b.csv"
        self.output_a = self.test_data_dir / "faculty_output_a.xlsx"
        self.output_b = self.test_data_dir / "faculty_output_b.xlsx"

        pd.DataFrame(
            [
                {"Start_Time": "09:00", "End_Time": "10:00"},
            ]
        ).to_csv(self.slots_file, index=False)

        pd.DataFrame(
            [
                {"Room_ID": "C101", "Type": "classroom"},
                {"Room_ID": "C102", "Type": "classroom"},
            ]
        ).to_csv(self.rooms_file, index=False)

        pd.DataFrame(
            [
                {
                    "Course_Code": "CS101",
                    "Course_Title": "Dept A Course",
                    "Faculty": "Dr. Shared",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Semester_Half": "1",
                    "Elective": "0",
                }
            ]
        ).to_csv(self.courses_a_file, index=False)

        pd.DataFrame(
            [
                {
                    "Course_Code": "EC101",
                    "Course_Title": "Dept B Course",
                    "Faculty": "Dr. Shared",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Semester_Half": "1",
                    "Elective": "0",
                }
            ]
        ).to_csv(self.courses_b_file, index=False)

    def tearDown(self):
        for f in (
            self.slots_file,
            self.rooms_file,
            self.courses_a_file,
            self.courses_b_file,
            self.output_a,
            self.output_b,
        ):
            try:
                Path(f).unlink()
            except FileNotFoundError:
                pass

    def test_shared_faculty_not_double_booked_across_departments(self):
        shared_room_usage = {}
        shared_lecturer_busy = {}

        scheduler_a = Scheduler(
            str(self.slots_file),
            str(self.courses_a_file),
            str(self.rooms_file),
            shared_room_usage,
            dept_name="CSE-5-A",
            global_lecturer_busy=shared_lecturer_busy,
        )
        scheduler_b = Scheduler(
            str(self.slots_file),
            str(self.courses_b_file),
            str(self.rooms_file),
            shared_room_usage,
            dept_name="ECE-5",
            global_lecturer_busy=shared_lecturer_busy,
        )
        scheduler_a.days = ["Monday"]
        scheduler_b.days = ["Monday"]

        with pd.ExcelWriter(self.output_a, engine="openpyxl") as writer_a:
            scheduler_a.generate_timetable(scheduler_a.courses, writer_a, "First_Half")
        with pd.ExcelWriter(self.output_b, engine="openpyxl") as writer_b:
            scheduler_b.generate_timetable(scheduler_b.courses, writer_b, "First_Half")

        entries_a = [e for e in scheduler_a.scheduled_entries if e["sheet"] == "First_Half"]
        entries_b = [e for e in scheduler_b.scheduled_entries if e["sheet"] == "First_Half"]

        self.assertEqual(len(entries_a), 1)
        self.assertEqual(entries_a[0]["faculty"], "Dr. Shared")
        self.assertEqual(len(entries_b), 0)
        unscheduled_ec101 = [
            unscheduled_course
            for unscheduled_course in scheduler_b.unscheduled_courses
            if unscheduled_course["course_code"] == "EC101" and unscheduled_course["type"] == "Lecture"
        ]
        self.assertEqual(len(unscheduled_ec101), 1)
        self.assertEqual(unscheduled_ec101[0]["faculty"], "Dr. Shared")
        self.assertEqual(
            shared_lecturer_busy.get("First_Half", {}).get("Monday", {}).get("09:00-10:00"),
            ["Dr. Shared"],
        )


if __name__ == "__main__":
    unittest.main()
