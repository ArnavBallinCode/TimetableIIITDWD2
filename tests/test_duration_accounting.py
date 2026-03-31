import os
import tempfile
import unittest

import pandas as pd

from timetable_automation.main import Scheduler


class TestDurationAccounting(unittest.TestCase):
    def _build_scheduler(self, slots, ltp="1-0-0-0-1"):
        temp_dir = tempfile.mkdtemp()
        slots_path = os.path.join(temp_dir, "slots.csv")
        courses_path = os.path.join(temp_dir, "courses.csv")
        rooms_path = os.path.join(temp_dir, "rooms.csv")

        pd.DataFrame(slots).to_csv(slots_path, index=False)
        pd.DataFrame(
            [
                {
                    "Course_Code": "CS101",
                    "Course_Title": "Intro",
                    "Faculty": "Prof X",
                    "L-T-P-S-C": ltp,
                    "Semester_Half": "1",
                    "Elective": "0",
                }
            ]
        ).to_csv(courses_path, index=False)
        pd.DataFrame(
            [
                {"Room_ID": "C101", "Type": "classroom"},
                {"Room_ID": "L101", "Type": "lab"},
            ]
        ).to_csv(rooms_path, index=False)
        return Scheduler(
            slots_path,
            courses_path,
            rooms_path,
            {},
        )

    def test_allocate_session_uses_exact_duration_match(self):
        sched = self._build_scheduler(
            [
                {"Start_Time": "09:00", "End_Time": "09:15"},
                {"Start_Time": "09:15", "End_Time": "10:00"},
                {"Start_Time": "10:00", "End_Time": "10:30"},
            ]
        )
        timetable = pd.DataFrame("", index=sched.days, columns=sched.slots)
        allocated = sched._allocate_session(
            timetable,
            {d: {} for d in sched.days},
            {d: False for d in sched.days},
            "Monday",
            "Prof X",
            "CS101",
            1.0,
            "L",
            False,
            "TestSheet",
        )
        self.assertIsNotNone(allocated)
        self.assertAlmostEqual(sum(sched.slot_durations[s] for s in allocated), 1.0)

    def test_allocate_session_rejects_oversized_match(self):
        sched = self._build_scheduler(
            [
                {"Start_Time": "09:00", "End_Time": "09:45"},
                {"Start_Time": "09:45", "End_Time": "10:15"},
            ]
        )
        timetable = pd.DataFrame("", index=sched.days, columns=sched.slots)
        allocated = sched._allocate_session(
            timetable,
            {d: {} for d in sched.days},
            {d: False for d in sched.days},
            "Monday",
            "Prof X",
            "CS101",
            1.0,
            "L",
            False,
            "TestSheet",
        )
        self.assertIsNone(allocated)

    def test_generate_timetable_does_not_fake_hour_coverage(self):
        sched = self._build_scheduler(
            [
                {"Start_Time": "09:00", "End_Time": "09:45"},
                {"Start_Time": "09:45", "End_Time": "10:15"},
            ],
            ltp="1-0-0-0-1",
        )
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            output_path = tmp.name
        try:
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                sched.generate_timetable(sched.courses, writer, "TestSheet")
            lecture_unscheduled = [
                item
                for item in sched.unscheduled_courses
                if item["course_code"] == "CS101" and item["type"] == "Lecture"
            ]
            self.assertTrue(lecture_unscheduled)
            self.assertAlmostEqual(lecture_unscheduled[0]["remaining_hours"], 1.0)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
