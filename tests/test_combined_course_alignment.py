import unittest
from pathlib import Path

import pandas as pd

from timetable_automation.main import Scheduler


class TestCombinedCourseAlignment(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = Path("tests/test_data")
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        self.slots_file = self.test_data_dir / "combined_align_slots.csv"
        self.rooms_file = self.test_data_dir / "combined_align_rooms.csv"
        self.courses_dsai_file = self.test_data_dir / "combined_align_courses_dsai4.csv"
        self.courses_cse_file = self.test_data_dir / "combined_align_courses_cse6.csv"

        pd.DataFrame(
            [
                {"Start_Time": "09:00", "End_Time": "10:00"},
            ]
        ).to_csv(self.slots_file, index=False)

        pd.DataFrame(
            [
                {"Room_ID": "C004", "Capacity": 200, "Type": "Classroom"},
            ]
        ).to_csv(self.rooms_file, index=False)

        pd.DataFrame(
            [
                {
                    "Course_Code": "DS308",
                    "Course_Title": "Data Security and Privacy",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Faculty": "Faculty A",
                    "Semester_Half": "1",
                    "Elective": "0",
                    "Students": 60,
                    "is_combined": 1,
                }
            ]
        ).to_csv(self.courses_dsai_file, index=False)

        pd.DataFrame(
            [
                {
                    "Course_Code": "DS308",
                    "Course_Title": "Data Security and Privacy",
                    "L-T-P-S-C": "1-0-0-0-1",
                    "Faculty": "Faculty B",
                    "Semester_Half": "1",
                    "Elective": "0",
                    "Students": 80,
                    "is_combined": 1,
                }
            ]
        ).to_csv(self.courses_cse_file, index=False)

    def tearDown(self):
        for f in (
            self.slots_file,
            self.rooms_file,
            self.courses_dsai_file,
            self.courses_cse_file,
        ):
            try:
                Path(f).unlink()
            except FileNotFoundError:
                pass

    def test_combined_course_template_shared_across_groups(self):
        shared_room_usage = {}
        shared_elective_slots = {}
        shared_elective_slot_usage = {}
        shared_elective_room_templates = {}
        shared_elective_room_usage = {}
        shared_elective_representatives = {}
        shared_combined_slots = {}
        shared_combined_room_usage = {}
        shared_combined_strength = {"DS308": 140}
        shared_c004_reserved_slots = {}

        dsai = Scheduler(
            str(self.slots_file),
            str(self.courses_dsai_file),
            str(self.rooms_file),
            shared_room_usage,
            shared_elective_slots,
            dept_name="DSAI-4",
            global_elective_slot_usage=shared_elective_slot_usage,
            global_elective_room_templates=shared_elective_room_templates,
            global_elective_room_usage=shared_elective_room_usage,
            global_elective_representatives=shared_elective_representatives,
            global_combined_slots=shared_combined_slots,
            global_combined_room_usage=shared_combined_room_usage,
            global_combined_strength=shared_combined_strength,
            global_c004_reserved_slots=shared_c004_reserved_slots,
        )
        cse = Scheduler(
            str(self.slots_file),
            str(self.courses_cse_file),
            str(self.rooms_file),
            shared_room_usage,
            shared_elective_slots,
            dept_name="CSE-6-A",
            global_elective_slot_usage=shared_elective_slot_usage,
            global_elective_room_templates=shared_elective_room_templates,
            global_elective_room_usage=shared_elective_room_usage,
            global_elective_representatives=shared_elective_representatives,
            global_combined_slots=shared_combined_slots,
            global_combined_room_usage=shared_combined_room_usage,
            global_combined_strength=shared_combined_strength,
            global_c004_reserved_slots=shared_c004_reserved_slots,
        )

        sheet_name = "First_Half"
        template_key = dsai._combined_template_key("DS308", "L", sheet_name)
        dsai._record_combined_slots(template_key, "Monday", [dsai.slots[0]], "C004")

        self.assertIn(template_key, shared_combined_slots)
        self.assertEqual(cse._combined_template_key("DS308", "L", sheet_name), template_key)
        self.assertEqual(cse.global_combined_slots[template_key][0]["slots"], [cse.slots[0]])


if __name__ == "__main__":
    unittest.main()
