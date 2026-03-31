import unittest
import tempfile
import pandas as pd
from timetable_automation.main import Scheduler

class TestSchedulerBasics(unittest.TestCase):
    def setUp(self):
        pd.DataFrame([
            {"Start_Time": "09:00", "End_Time": "10:00"},
            {"Start_Time": "10:00", "End_Time": "11:00"}
        ]).to_csv("tests/test_data/temp_slots.csv", index=False)

        pd.DataFrame([
            {"Course_Code": "CS101", "Course_Title": "Intro", "Faculty": "Prof X", "L-T-P-S-C": "1-0-0-0-1", "Semester_Half": "1", "Elective": "0"},
        ]).to_csv("tests/test_data/temp_courses.csv", index=False)

        pd.DataFrame([
            {"Room_ID": "R1", "Type": "classroom"},
            {"Room_ID": "R2", "Type": "lab"}
        ]).to_csv("tests/test_data/temp_rooms.csv", index=False)

        self.sched = Scheduler("tests/test_data/temp_slots.csv", "tests/test_data/temp_courses.csv", "tests/test_data/temp_rooms.csv", {})

    def test_slot_duration(self):
        self.assertAlmostEqual(self.sched._slot_duration("09:00-10:00"), 1.0)
        self.assertAlmostEqual(self.sched._slot_duration("10:00-11:30"), 1.5)

    def test_free_blocks(self):
        df = pd.DataFrame("", index=self.sched.days, columns=self.sched.slots)
        df.at["Monday", "09:00-10:00"] = "Used"
        free = self.sched._get_free_blocks(df, "Monday")
        self.assertIsInstance(free, list)

    def test_slots_are_sorted_by_start_time(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            slots_path = f"{tmp_dir}/slots_unsorted.csv"
            pd.DataFrame([
                {"Start_Time": "10:00", "End_Time": "11:00"},
                {"Start_Time": "09:00", "End_Time": "10:00"}
            ]).to_csv(slots_path, index=False)
            sched = Scheduler(slots_path, "tests/test_data/temp_courses.csv", "tests/test_data/temp_rooms.csv", {})
            self.assertEqual(sched.slots, ["09:00-10:00", "10:00-11:00"])

    def test_invalid_slot_duration_raises_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            slots_path = f"{tmp_dir}/slots_invalid_duration.csv"
            pd.DataFrame([
                {"Start_Time": "10:00", "End_Time": "09:00"}
            ]).to_csv(slots_path, index=False)
            with self.assertRaisesRegex(ValueError, "Invalid timeslot duration"):
                Scheduler(slots_path, "tests/test_data/temp_courses.csv", "tests/test_data/temp_rooms.csv", {})
