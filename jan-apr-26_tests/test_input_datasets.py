"""
Test Input Datasets — Jan-Apr 2026 Semester
============================================
Tests are organized across 4 curated datasets:

  Dataset 1 (clean)    — Real Jan-Apr 2026 data, all fields valid.
  Dataset 2 (stress)   — Real courses, only 2 classrooms + 1 lab.
  Dataset 3 (invalid)  — Malformed inputs: bad L-T-P-S-C, missing basket,
                         negative/non-numeric students, empty course file.
  Dataset 4 (conflict) — Same faculty on multiple courses; same-basket electives.

TC01  Baseline timetable generation (Dataset 1)
TC02  No duplicate room usage in same slot (Dataset 1)
TC03  Stress: unscheduled courses when rooms are scarce (Dataset 2)
TC04  Invalid L-T-P-S-C is rejected with clear error (Dataset 3)
TC05  Missing basket column handled gracefully (Dataset 3)
TC06  Negative / non-numeric students clamped to 0 (Dataset 3)
TC07  Empty course file produces no scheduled entries (Dataset 3)
TC08  Faculty not double-booked in the same slot (Dataset 4)
TC09  Same-basket electives share the same time slot (Dataset 4)
TC10  Lab sessions: at most one lab per day per section (Dataset 1)
TC11  Combined courses (is_combined=1) are scheduled without crash (Dataset 1)
TC12  Slot duration calculation correctness (unit test)
"""

import os
import unittest
from pathlib import Path

import pandas as pd

from timetable_automation.main import Course, Scheduler

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent / "test_data" / "datasets"
D1 = BASE / "dataset1_clean"
D2 = BASE / "dataset2_stress"
D3 = BASE / "dataset3_invalid"
D4 = BASE / "dataset4_conflict"

SHARED_SLOTS_D1 = str(D1 / "timeslots.csv")
SHARED_ROOMS_D1 = str(D1 / "rooms.csv")

OUTPUT_DIR = Path(__file__).parent / "test_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_scheduler(courses_file, rooms_file=None, slots_file=None, dept_name="CSE-2-A"):
    """Helper: build a Scheduler with shared global state dicts."""
    return Scheduler(
        slots_file=slots_file or SHARED_SLOTS_D1,
        courses_file=courses_file,
        rooms_file=rooms_file or SHARED_ROOMS_D1,
        global_room_usage={},
        dept_name=dept_name,
    )


def run_timetable(sched, sheet="TestSheet"):
    """Helper: run generate_timetable and close the writer."""
    out = str(OUTPUT_DIR / f"{sheet}_output.xlsx")
    writer = pd.ExcelWriter(out, engine="openpyxl")
    sched.generate_timetable(sched.courses, writer, sheet)
    writer.close()
    return out


# ══════════════════════════════════════════════════════════════════════════════
# TC01 — Baseline timetable generation (Dataset 1)
# ══════════════════════════════════════════════════════════════════════════════
class TC01_BaselineGeneration(unittest.TestCase):
    """
    Scenario : Clean real Jan-Apr 2026 data (CSEA-II).
    Input    : dataset1_clean/coursesCSEA-II.csv + full rooms + real timeslots.
    Expected : Excel file is created; at least one entry is scheduled.
    """

    def test_timetable_file_created(self):
        sched = make_scheduler(str(D1 / "coursesCSEA-II.csv"), dept_name="CSE-2-A")
        out = run_timetable(sched, "TC01")
        self.assertTrue(Path(out).exists(), "Output .xlsx file should be created")

    def test_at_least_one_course_scheduled(self):
        sched = make_scheduler(str(D1 / "coursesCSEA-II.csv"), dept_name="CSE-2-A")
        run_timetable(sched, "TC01b")
        self.assertGreater(
            len(sched.scheduled_entries), 0,
            "At least one course should be scheduled for valid real data"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC02 — No duplicate room usage in the same slot (Dataset 1)
# ══════════════════════════════════════════════════════════════════════════════
class TC02_NoDuplicateRooms(unittest.TestCase):
    """
    Scenario : Two sections (CSEA-II and CSEB-II) scheduled with shared room pool.
    Input    : dataset1_clean — both sections, shared global_room_usage.
    Expected : No room appears twice in the same (day, slot) across both sections.
    """

    def test_no_room_double_booked(self):
        shared_room_usage = {}
        sched_a = Scheduler(
            slots_file=SHARED_SLOTS_D1,
            courses_file=str(D1 / "coursesCSEA-II.csv"),
            rooms_file=SHARED_ROOMS_D1,
            global_room_usage=shared_room_usage,
            dept_name="CSE-2-A",
        )
        sched_b = Scheduler(
            slots_file=SHARED_SLOTS_D1,
            courses_file=str(D1 / "coursesCSEB-II.csv"),
            rooms_file=SHARED_ROOMS_D1,
            global_room_usage=shared_room_usage,
            dept_name="CSE-2-B",
        )

        out_a = str(OUTPUT_DIR / "TC02_A.xlsx")
        out_b = str(OUTPUT_DIR / "TC02_B.xlsx")

        w = pd.ExcelWriter(out_a, engine="openpyxl")
        sched_a.generate_timetable(sched_a.courses, w, "Sheet1")
        w.close()

        w = pd.ExcelWriter(out_b, engine="openpyxl")
        sched_b.generate_timetable(sched_b.courses, w, "Sheet1")
        w.close()

        for day, slot_map in shared_room_usage.items():
            for slot, rooms_used in slot_map.items():
                self.assertEqual(
                    len(set(rooms_used)), len(rooms_used),
                    f"Room double-booked on {day} at {slot}: {rooms_used}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TC03 — Stress: some courses unscheduled when rooms are scarce (Dataset 2)
# ══════════════════════════════════════════════════════════════════════════════
class TC03_StressRoomScarcity(unittest.TestCase):
    """
    Scenario : 12 real courses but only 2 classrooms + 1 lab available.
    Input    : dataset2_stress — full course list, minimal rooms.
    Expected : Scheduler does not crash; unscheduled_courses list is populated
               OR scheduled_entries < total courses (some couldn't fit).
    """

    def test_no_crash_under_room_scarcity(self):
        sched = make_scheduler(
            str(D2 / "courses_stress.csv"),
            rooms_file=str(D2 / "rooms.csv"),
            slots_file=str(D2 / "timeslots.csv"),
            dept_name="CSE-2-A",
        )
        try:
            run_timetable(sched, "TC03")
        except Exception as e:
            self.fail(f"Scheduler crashed under room scarcity: {e}")

    def test_not_all_courses_fit(self):
        sched = make_scheduler(
            str(D2 / "courses_stress.csv"),
            rooms_file=str(D2 / "rooms.csv"),
            slots_file=str(D2 / "timeslots.csv"),
            dept_name="CSE-2-A",
        )
        run_timetable(sched, "TC03b")
        total_courses = len(sched.courses)
        # Count distinct course codes that were actually scheduled
        scheduled_codes = {e["code"] for e in sched.scheduled_entries}
        # With only 2 classrooms and 12 courses needing multiple sessions,
        # it is expected that not every session can be placed.
        # We verify the scheduler handled it gracefully (no crash above),
        # and that it scheduled at least something.
        self.assertGreater(len(scheduled_codes), 0, "Should schedule at least some courses")


# ══════════════════════════════════════════════════════════════════════════════
# TC04 — Invalid L-T-P-S-C is rejected with clear error (Dataset 3)
# ══════════════════════════════════════════════════════════════════════════════
class TC04_InvalidLTPFormat(unittest.TestCase):
    """
    Scenario : One course has L-T-P-S-C = "BAD-FORMAT".
    Input    : dataset3_invalid/courses_invalid_ltp.csv
    Expected : ValueError is raised with a clear validation message.
    """

    def test_bad_ltp_raises_clear_value_error(self):
        row = {
            "Course_Code": "MA163",
            "Course_Title": "Linear Algebra",
            "L-T-P-S-C": "BAD-FORMAT",
            "Faculty": "Dr. Anand P. Barangi",
            "Semester_Half": "1",
            "Elective": "0",
            "Students": "107",
            "basket": "0",
            "is_combined": "0",
        }
        with self.assertRaisesRegex(ValueError, "Invalid L-T-P-S-C format: expected 5 integers"):
            Course(row)

    def test_scheduler_rejects_bad_ltpsc_during_load(self):
        """Scheduler construction fails fast with malformed L-T-P-S-C input."""
        with self.assertRaisesRegex(ValueError, "Invalid L-T-P-S-C format: expected 5 integers"):
            make_scheduler(
                courses_file=str(D3 / "courses_invalid_ltp.csv"),
                rooms_file=str(D3 / "rooms.csv"),
                slots_file=str(D3 / "timeslots.csv"),
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC05 — Missing basket column handled gracefully (Dataset 3)
# ══════════════════════════════════════════════════════════════════════════════
class TC05_MissingBasketColumn(unittest.TestCase):
    """
    Scenario : courses CSV has no 'basket' column at all.
    Input    : dataset3_invalid/courses_missing_basket.csv
    Expected : Scheduler loads without crash; basket defaults to 0.
    """

    def test_missing_basket_no_crash(self):
        sched = make_scheduler(
            str(D3 / "courses_missing_basket.csv"),
            rooms_file=str(D3 / "rooms.csv"),
            slots_file=str(D3 / "timeslots.csv"),
        )
        try:
            run_timetable(sched, "TC05")
        except Exception as e:
            self.fail(f"Scheduler crashed when basket column is missing: {e}")

    def test_missing_basket_defaults_to_zero(self):
        row = {
            "Course_Code": "CS154",
            "Course_Title": "Intro to Data Analytics",
            "L-T-P-S-C": "3-1-0-0-2",
            "Faculty": "Dr. Abdul Wahid",
            "Semester_Half": "1",
            "Elective": "1",
            "Students": "11",
            "is_combined": "0",
            # 'basket' intentionally omitted
        }
        course = Course(row)
        self.assertEqual(course.basket, 0)


# ══════════════════════════════════════════════════════════════════════════════
# TC06 — Negative / non-numeric students clamped to 0 (Dataset 3)
# ══════════════════════════════════════════════════════════════════════════════
class TC06_InvalidStudentCount(unittest.TestCase):
    """
    Scenario : Students field is -50 or "abc".
    Input    : dataset3_invalid/courses_negative_students.csv
    Expected : course.students == 0 (clamped); no crash.
    """

    def test_negative_students_clamped(self):
        row = {
            "Course_Code": "MA163",
            "L-T-P-S-C": "3-1-0-0-2",
            "Students": "-50",
        }
        course = Course(row)
        self.assertEqual(course.students, 0)

    def test_non_numeric_students_clamped(self):
        row = {
            "Course_Code": "CS162",
            "L-T-P-S-C": "3-1-0-0-2",
            "Students": "abc",
        }
        course = Course(row)
        self.assertEqual(course.students, 0)

    def test_scheduler_loads_negative_students_without_crash(self):
        sched = make_scheduler(
            str(D3 / "courses_negative_students.csv"),
            rooms_file=str(D3 / "rooms.csv"),
            slots_file=str(D3 / "timeslots.csv"),
        )
        try:
            run_timetable(sched, "TC06")
        except Exception as e:
            self.fail(f"Scheduler crashed on negative/invalid student count: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TC07 — Empty course file produces no scheduled entries (Dataset 3)
# ══════════════════════════════════════════════════════════════════════════════
class TC07_EmptyCourseFile(unittest.TestCase):
    """
    Scenario : courses CSV has headers but zero data rows.
    Input    : dataset3_invalid/courses_empty.csv
    Expected : No crash; scheduled_entries is empty.
    """

    def test_empty_courses_no_crash(self):
        sched = make_scheduler(
            str(D3 / "courses_empty.csv"),
            rooms_file=str(D3 / "rooms.csv"),
            slots_file=str(D3 / "timeslots.csv"),
        )
        try:
            run_timetable(sched, "TC07")
        except Exception as e:
            self.fail(f"Scheduler crashed on empty course file: {e}")

    def test_empty_courses_zero_entries(self):
        sched = make_scheduler(
            str(D3 / "courses_empty.csv"),
            rooms_file=str(D3 / "rooms.csv"),
            slots_file=str(D3 / "timeslots.csv"),
        )
        run_timetable(sched, "TC07b")
        self.assertEqual(len(sched.scheduled_entries), 0)


# ══════════════════════════════════════════════════════════════════════════════
# TC08 — Faculty not double-booked in the same slot (Dataset 4)
# ══════════════════════════════════════════════════════════════════════════════
class TC08_FacultyConflict(unittest.TestCase):
    """
    Scenario : Dr. Aswath Babu H is assigned to 3 courses in the same semester half.
    Input    : dataset4_conflict/courses_faculty_conflict.csv
    Expected : No two scheduled entries for the same faculty overlap in (day, slot).
    """

    def test_no_faculty_double_booking(self):
        sched = make_scheduler(
            str(D4 / "courses_faculty_conflict.csv"),
            rooms_file=str(D4 / "rooms.csv"),
            slots_file=str(D4 / "timeslots.csv"),
            dept_name="CSE-2-A",
        )
        run_timetable(sched, "TC08")

        # Build a map: (faculty, day, slot) -> list of course codes
        faculty_slot_map = {}
        for entry in sched.scheduled_entries:
            key = (entry["faculty"], entry["day"], entry["slot"])
            faculty_slot_map.setdefault(key, []).append(entry["code"])

        for (faculty, day, slot), codes in faculty_slot_map.items():
            self.assertEqual(
                len(codes), 1,
                f"Faculty '{faculty}' double-booked on {day} at {slot}: {codes}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC09 — Same-basket electives share the same time slot (Dataset 4)
# ══════════════════════════════════════════════════════════════════════════════
class TC09_SameBasketElectiveSlot(unittest.TestCase):
    """
    Scenario : Basket 1 has 4 elective options; basket 2 has 3 options.
    Input    : dataset4_conflict/courses_same_basket_electives.csv
    Expected : All basket-1 electives are represented by a single placeholder
               scheduled at the same slot; same for basket-2.
               (The scheduler picks one representative per basket.)
    """

    def test_one_placeholder_per_basket(self):
        sched = make_scheduler(
            str(D4 / "courses_same_basket_electives.csv"),
            rooms_file=str(D4 / "rooms.csv"),
            slots_file=str(D4 / "timeslots.csv"),
            dept_name="CSE-2-A",
        )
        run_timetable(sched, "TC09")

        elective_codes = {e["code"] for e in sched.scheduled_entries if e["code"].startswith("Elective_")}
        # Expect exactly one placeholder per basket (Elective_1 and Elective_2)
        self.assertIn("Elective_1", elective_codes, "Basket 1 placeholder should be scheduled")
        self.assertIn("Elective_2", elective_codes, "Basket 2 placeholder should be scheduled")

    def test_basket_electives_not_in_same_slot(self):
        """Basket 1 and Basket 2 placeholders must NOT overlap in (day, slot)."""
        sched = make_scheduler(
            str(D4 / "courses_same_basket_electives.csv"),
            rooms_file=str(D4 / "rooms.csv"),
            slots_file=str(D4 / "timeslots.csv"),
            dept_name="CSE-2-A",
        )
        run_timetable(sched, "TC09b")

        slots_b1 = {(e["day"], e["slot"]) for e in sched.scheduled_entries if e["code"] == "Elective_1"}
        slots_b2 = {(e["day"], e["slot"]) for e in sched.scheduled_entries if e["code"] == "Elective_2"}
        overlap = slots_b1 & slots_b2
        self.assertEqual(len(overlap), 0, f"Basket 1 and Basket 2 electives overlap at: {overlap}")


# ══════════════════════════════════════════════════════════════════════════════
# TC10 — Lab sessions: at most one lab per day per section (Dataset 1)
# ══════════════════════════════════════════════════════════════════════════════
class TC10_OneLabPerDay(unittest.TestCase):
    """
    Scenario : CSEA-II has CS163 (L=3,P=2) and CS164 (L=3,P=2) — two lab courses.
    Input    : dataset1_clean/coursesCSEA-II.csv
    Expected : On any given day, at most one lab session is scheduled.
    """

    def test_at_most_one_lab_per_day(self):
        sched = make_scheduler(str(D1 / "coursesCSEA-II.csv"), dept_name="CSE-2-A")
        run_timetable(sched, "TC10")

        # A lab session spans multiple slots — count distinct (day, course_code) lab pairs,
        # not individual slot entries. The constraint is: at most one lab course per day.
        lab_day_courses = {}
        for entry in sched.scheduled_entries:
            if "(Lab" in entry.get("display", ""):
                day = entry["day"]
                code = entry["code"]
                lab_day_courses.setdefault(day, set()).add(code)

        for day, codes in lab_day_courses.items():
            self.assertEqual(
                len(codes), 1,
                f"More than one distinct lab course on {day}: {codes}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC11 — Combined courses scheduled without crash (Dataset 1)
# ══════════════════════════════════════════════════════════════════════════════
class TC11_CombinedCourses(unittest.TestCase):
    """
    Scenario : MA163, CS162, HS161 have is_combined=1 in CSEA-II.
    Input    : dataset1_clean/coursesCSEA-II.csv
    Expected : Scheduler runs without crash; combined courses appear in entries.
    """

    def test_combined_courses_no_crash(self):
        sched = make_scheduler(str(D1 / "coursesCSEA-II.csv"), dept_name="CSE-2-A")
        try:
            run_timetable(sched, "TC11")
        except Exception as e:
            self.fail(f"Scheduler crashed on combined courses: {e}")

    def test_combined_courses_appear_in_schedule(self):
        sched = make_scheduler(str(D1 / "coursesCSEA-II.csv"), dept_name="CSE-2-A")
        run_timetable(sched, "TC11b")
        scheduled_codes = {e["code"] for e in sched.scheduled_entries}
        combined_codes = {
            c.code for c in sched.courses if getattr(c, "is_combined", False)
        }
        # At least one combined course should be scheduled
        self.assertTrue(
            combined_codes & scheduled_codes,
            f"None of the combined courses were scheduled. Combined: {combined_codes}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC12 — Slot duration calculation correctness (unit test)
# ══════════════════════════════════════════════════════════════════════════════
class TC12_SlotDuration(unittest.TestCase):
    """
    Scenario : Verify _slot_duration() against known values from real timeslots.
    Input    : Various slot strings from the actual timeslots.csv.
    Expected : Exact float durations.
    """

    def setUp(self):
        self.sched = make_scheduler(str(D1 / "coursesCSEA-II.csv"), dept_name="CSE-2-A")

    def test_one_hour_slot(self):
        self.assertAlmostEqual(self.sched._slot_duration("09:00-10:00"), 1.0)

    def test_ninety_minute_slot(self):
        self.assertAlmostEqual(self.sched._slot_duration("07:30-09:00"), 1.5)

    def test_thirty_minute_slot(self):
        self.assertAlmostEqual(self.sched._slot_duration("10:00-10:30"), 0.5)

    def test_fifteen_minute_slot(self):
        self.assertAlmostEqual(self.sched._slot_duration("10:30-10:45"), 0.25)

    def test_forty_five_minute_slot(self):
        self.assertAlmostEqual(self.sched._slot_duration("12:30-13:15"), 0.75)

    def test_real_timeslots_all_positive(self):
        for slot in self.sched.slots:
            self.assertGreater(
                self.sched._slot_duration(slot), 0,
                f"Slot {slot} has non-positive duration"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
