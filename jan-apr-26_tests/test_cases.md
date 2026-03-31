# TEST CASES — Timetable Automation Project
## Jan–Apr 2026 Semester Data

> Multiple datasets were curated using real Jan–Apr 2026 semester data and modified to simulate
> edge cases, constraint violations, and invalid inputs. Test cases were designed to cover
> functional correctness, robustness, and system limitations. The test cases were designed to
> expose both visible failures (crashes) and latent issues (silent incorrect behavior).

---

## Dataset Summary

| Dataset | Location | Description | Purpose |
|---------|----------|-------------|---------|
| **Dataset 1** — Clean | `tests/test_data/datasets/dataset1_clean/` | Real Jan–Apr 2026 data (CSEA-II, CSEB-II, ECE-II, CSEA-IV). Full rooms, real timeslots. | Baseline functional correctness |
| **Dataset 2** — Stress | `tests/test_data/datasets/dataset2_stress/` | Real courses (12 entries) but only 2 classrooms + 1 lab. | Test scheduling limits / room scarcity |
| **Dataset 3** — Invalid | `tests/test_data/datasets/dataset3_invalid/` | Malformed L-T-P-S-C, missing basket column, negative/non-numeric students, empty course file. | Robustness and error handling |
| **Dataset 4** — Conflict | `tests/test_data/datasets/dataset4_conflict/` | Same faculty on 3 courses; multiple electives in same basket. | Constraint enforcement |

---

## Test Case Table

| Test ID | Scenario | Dataset | Input File(s) | Type | Expected Result |
|---------|----------|---------|---------------|------|-----------------|
| **TC01** | Baseline timetable generation | Dataset 1 | `coursesCSEA-II.csv`, full rooms, real timeslots | Normal / Functional | Excel output created; `scheduled_entries` is non-empty |
| **TC02** | No duplicate room usage in same slot | Dataset 1 | `coursesCSEA-II.csv` + `coursesCSEB-II.csv`, shared `global_room_usage` | Constraint | No room appears twice in the same `(day, slot)` across both sections |
| **TC03** | Room scarcity — some courses unscheduled | Dataset 2 | `courses_stress.csv`, only 2 classrooms + 1 lab | Edge Case / Stress | Scheduler does not crash; at least some courses are scheduled; not all sessions fit |
| **TC04** | Invalid L-T-P-S-C string exposes missing attribute bug | Dataset 3 | `courses_invalid_ltp.csv` (one row has `"BAD-FORMAT"`) | Invalid Input / Bug Exposure | `Course.L = Course.T = Course.P = 0` (correct); but `Course.S` and `Course.C` are **not set** — scheduler crashes with `AttributeError` when accessing `c.S`. Confirms robustness bug in `Course.__init__`. |
| **TC05** | Missing `basket` column | Dataset 3 | `courses_missing_basket.csv` (no basket column) | Invalid Input | Scheduler loads without crash; `course.basket` defaults to `0` |
| **TC06** | Negative / non-numeric student count | Dataset 3 | `courses_negative_students.csv` (`Students = -50` or `"abc"`) | Invalid Input | `course.students` clamped to `0`; no crash |
| **TC07** | Empty course file | Dataset 3 | `courses_empty.csv` (headers only, zero rows) | Edge Case | No crash; `scheduled_entries` is empty |
| **TC08** | Faculty double-booking prevention | Dataset 4 | `courses_faculty_conflict.csv` (Dr. Aswath Babu H on 3 courses, same half) | Constraint | No two entries share `(faculty, day, slot)`; faculty never double-booked |
| **TC09** | Same-basket electives get one placeholder each | Dataset 4 | `courses_same_basket_electives.csv` (basket 1: 4 electives, basket 2: 3 electives) | Elective / Constraint | Exactly one `Elective_1` and one `Elective_2` placeholder scheduled; baskets do not overlap in time |
| **TC10** | At most one lab session per day | Dataset 1 | `coursesCSEA-II.csv` (CS163 and CS164 both have P=2) | Constraint | On any given day, at most one `(Lab-...)` entry appears in `scheduled_entries` |
| **TC11** | Combined courses scheduled correctly | Dataset 1 | `coursesCSEA-II.csv` (MA163, CS162, HS161 have `is_combined=1`) | Functional | No crash; at least one combined course appears in `scheduled_entries` |
| **TC12** | Slot duration calculation | Dataset 1 | Slot strings from real `timeslots.csv` | Unit | `_slot_duration("09:00-10:00") == 1.0`, `"07:30-09:00" == 1.5`, `"10:30-10:45" == 0.25`, all slots > 0 |

---

## Dataset–Test Mapping

| Dataset | Test IDs |
|---------|----------|
| Dataset 1 — Clean | TC01, TC02, TC10, TC11, TC12 |
| Dataset 2 — Stress | TC03 |
| Dataset 3 — Invalid | TC04, TC05, TC06, TC07 |
| Dataset 4 — Conflict | TC08, TC09 |

---

## Coverage Summary

| Coverage Area | Test IDs |
|---------------|----------|
| Functional correctness (happy path) | TC01, TC11, TC12 |
| Constraint enforcement | TC02, TC08, TC09, TC10 |
| Edge cases | TC03, TC07 |
| Invalid / malformed input | TC04, TC05, TC06 |

---

## Dataset 3 — Invalid Input Files Detail

| File | What is broken | TC |
|------|----------------|----|
| `courses_invalid_ltp.csv` | First row has `L-T-P-S-C = "BAD-FORMAT"` | TC04 |
| `courses_missing_basket.csv` | No `basket` column at all | TC05 |
| `courses_negative_students.csv` | `Students = -50` and `Students = "abc"` | TC06 |
| `courses_empty.csv` | Header row only, zero data rows | TC07 |

---

## Pre-existing Unit Tests (original test suite)

| Test File | Function Tested | Description |
|-----------|-----------------|-------------|
| `test_course.py` | `Course(row)` | Valid parsing, invalid L-T-P-S-C defaults |
| `test_scheduler_basic.py` | `_slot_duration()`, `_get_free_blocks()` | Duration math, free block detection |
| `test_session_allocation.py` | `_allocate_session()` | Basic session placement |
| `test_elective_allotment.py` | `generate_timetable()` | Elective placeholder scheduling |
| `test_elective_room_alignment.py` | `_compute_elective_room_assignments_legally()` | Same elective code → same room across branches |
| `test_end_to_end.py` | `generate_timetable()` | Full pipeline, no duplicate rooms |
