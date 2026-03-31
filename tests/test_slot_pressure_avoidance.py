import unittest
from pathlib import Path

import pandas as pd

from timetable_automation.main import Scheduler


class TestSlotPressureAvoidance(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = Path("tests/test_data")
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        self.slots_file = self.test_data_dir / "pressure_slots.csv"
        self.rooms_file = self.test_data_dir / "pressure_rooms.csv"
        self.courses_file = self.test_data_dir / "pressure_courses_dsai3.csv"

        pd.DataFrame(
            [
                {"Start_Time": "09:00", "End_Time": "10:00"},
                {"Start_Time": "10:00", "End_Time": "11:00"},
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
                    "Course_Title": "Core DSAI",
                    "Faculty": "Prof Core",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Semester_Half": "1",
                    "Elective": "0",
                    "Students": 60,
                }
            ]
        ).to_csv(self.courses_file, index=False)

    def tearDown(self):
        for f in (self.slots_file, self.rooms_file, self.courses_file):
            try:
                Path(f).unlink()
            except FileNotFoundError:
                pass

    def test_non_elective_prefers_slot_not_blocked_by_cross_sem_elective(self):
        scheduler = Scheduler(
            str(self.slots_file),
            str(self.courses_file),
            str(self.rooms_file),
            global_room_usage={},
            dept_name="DSAI-3",
            global_elective_slot_usage={"1": {("Monday", "09:00-10:00")}},
        )

        timetable = pd.DataFrame("", index=scheduler.days, columns=scheduler.slots)
        result = scheduler._allocate_session(
            timetable=timetable,
            lecturer_busy={d: {s: [] for s in scheduler.slots} for d in scheduler.days},
            labs_scheduled={d: False for d in scheduler.days},
            day="Monday",
            faculty="Prof Core",
            code="CR3",
            duration_hours=1.0,
            session_type="L",
            is_elective=False,
            sheet_name="First_Half",
        )

        self.assertEqual(result, ["10:00-11:00"])


if __name__ == "__main__":
    unittest.main()
