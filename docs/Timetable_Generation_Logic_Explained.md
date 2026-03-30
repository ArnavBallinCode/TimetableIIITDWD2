# Timetable Generation Logic — Step-by-Step (Very Detailed)

This document explains, in plain language, how the timetable generator works internally.
It is intentionally detailed and example-driven.

> Source of truth: `/home/runner/work/TimetableIIITDWD2/TimetableIIITDWD2/timetable_automation/main.py`

---

## 1) What this system takes as input

For each department/branch CSV, the scheduler reads:

- **Course_Code** (example: `CS301`)
- **Course_Title** (example: `Operating Systems`)
- **Faculty** (example: `Prof A` or `Prof A/Prof B`)
- **L-T-P-S-C** (example: `3-1-2-0-4`)
- **Semester_Half** (`1`, `2`, or `0`)
- **Elective** (`1` or `0`)
- Optional fields used by newer logic:
  - `basket` (elective basket id)
  - `is_combined` / `Is_Combined` (combined class across branches)
  - `Students` (strength/capacity checks)

It also reads:

- **Time slots CSV** (`Start_Time`, `End_Time`)
- **Rooms CSV** (`Room_ID`, optional `Capacity`)

---

## 2) Big picture: what happens first

When `main.py` runs:

1. A dictionary called `departments` defines all department files.
2. Global shared structures are created:
   - `global_room_usage` (room occupancy)
   - `global_elective_slots` (cross-branch elective slot templates)
   - `global_combined_slots` (templates for combined courses)
   - and related tracking maps.
3. For each department:
   - a `Scheduler` object is created,
   - first-half and second-half timetables are generated,
   - styled Excel files are produced.
4. A combined faculty timetable workbook is generated.

So the algorithm is **not only local** to one class file; it coordinates across departments using shared dictionaries.

---

## 3) Hardcoded rules (important)

These are explicit constants/rules in code:

1. **Random seed is fixed**  
   - `RANDOM_SEED = 42`  
   This makes runs deterministic for the same input.

2. **Working days are fixed**  
   - `["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]`

3. **Excluded slots are hardcoded**  
   - `["07:30-09:00", "13:15-14:00"]`
   - These are kept empty in final sheets.

4. **Maximum retry attempts**  
   - `MAX_ATTEMPTS = 2000` per scheduling loop for L/T/P.

5. **Room naming convention is hardcoded by prefix**
   - Rooms starting with `L` are treated as labs.
   - Rooms starting with `C` are treated as classrooms.
   - Other prefixes are ignored by class/lab assignment logic.

6. **Special room policy is hardcoded**
   - `C002` and `C003`: compulsory-only classrooms.
   - `C004`: reserved for combined courses only.

7. **Combined cluster mapping is hardcoded**
   - `CSE` is one cluster.
   - `DSAI` and `ECE` are treated as another shared cluster.

---

## 4) Course parsing logic

Each CSV row becomes a `Course` object.

- Elective is considered true if:
  - `Elective > 0`, **or**
  - `basket > 0`
- `L-T-P-S-C` is split into integers `L`, `T`, `P`, `S`, `C`.
- Invalid numeric fields are safely defaulted (mostly to `0`).

### Example

If row is:

`CS510,Advanced Topic,Prof X,3-1-0-0-4,1,1,basket=2`

Then:
- `L=3`, `T=1`, `P=0`
- treated as elective because `Elective=1` and basket is non-zero.

---

## 5) How sessions are ordered for scheduling

Inside `generate_timetable`, courses are grouped in this order:

1. **Elective placeholders** first  
   (synthetic course codes like `Elective_2`)
2. **Combined non-electives**
3. **Regular non-electives**

Within non-electives, sorting prefers heavier courses first:
- sort key: `(P, L+T+S)` descending.

Why: harder-to-place courses are placed earlier.

---

## 6) Core allocation routine (`_allocate_session`)

This is the central function used for lectures/tutorials/labs.

### Inputs include
- day to try
- faculty
- course code
- required duration (hours)
- session type (`L`, `T`, `P`)
- whether elective
- forced slots or search mode

### Main checks

1. Prevent duplicate same-course entry in same day/sheet.
2. For practicals (`P`): max one lab session per day (`labs_scheduled[day]`).
3. Find candidate slots:
   - If `force_slots` is given: validate directly.
   - Else: scan free contiguous blocks and use a sliding-window fit.
4. Check faculty conflict in those slots.
5. Check elective cross-sem slot restrictions (unless relaxed).
6. Pick a room (for non-electives):
   - session-room compatibility (`L`/`T` => classroom, `P` => lab),
   - policy rules (`C004` / compulsory-only rules),
   - capacity (if required),
   - global room availability.
7. Write display text into timetable cells and save entries to `scheduled_entries`.

### Display examples
- Lecture: `CS101 (C201)`
- Tutorial: `CS101T (C201)`
- Practical: `CS101 (Lab-L101)`

---

## 7) Slot fitting strategy (with example)

In search mode, `_get_free_blocks` finds continuous empty slot ranges for a day.
Then a sliding window grows until required duration is reached.

Candidates are sorted by **least waste**:
- `waste = (sum(slot durations) - required duration)`

### Example

Suppose free slots durations are: `1.0`, `0.5`, `1.0`
and required duration is `1.5`.

Candidate windows:
- slot1+slot2 = 1.5 (waste 0.0) ✅ best
- slot2+slot3 = 1.5 (waste 0.0)
- slot1+slot2+slot3 = 2.5 (waste 1.0) (not preferred)

So the allocator picks tight fits first.

---

## 8) Room selection strategy (with example)

Room choice is handled by `_pick_room_for_slots`.

Priority:
1. `preferred_room` if valid
2. For combined L/T: prefer `C004` first
3. Reuse previously mapped room for same course (`course_room_map`)
4. Randomized candidates from class/lab pool

### Example

If `CS303` already got `C105` earlier and `C105` is free for requested slots:
- scheduler reuses `C105` to keep room consistency.

If combined lecture and `C004` is free:
- `C004` is chosen before other classrooms.

---

## 9) Elective handling: template-based synchronization

Electives are special:

1. Real elective courses in a basket are represented by one placeholder (`Elective_<basket>`).
2. Placeholder is scheduled in timetable grid.
3. Slots are stored in `global_elective_slots` with a key:
   - `(semester_group, sheet_name, basket_id, session_type)`
4. Other branches in same semester can reuse same elective slot template.

This keeps electives aligned across branches.

### Example

Basket 3 in semester 5 first half:
- First branch schedules `Elective_3` lecture on Tue slot X.
- That becomes template.
- Next branch tries to schedule basket 3 lecture in exactly same slot first.

If strict cross-sem overlap rule blocks it, logic can relax using:
- `relax_cross_sem_elective_block = True`

---

## 10) Combined course handling

Combined courses (`is_combined=true`) share timing/room templates using:
- `global_combined_slots`
- `global_combined_room_usage`

Key includes semester + cluster + sheet + course code + session type.

Capacity logic:
- `_build_global_combined_strength` aggregates students for combined courses across departments.
- `_required_capacity_for_course` enforces minimum room capacity for combined non-electives (L/T).

So, combined courses are synchronized and capacity-aware.

---

## 11) Faculty conflict handling

`lecturer_busy` tracks occupancy:
- day -> slot -> list of faculties.

If faculty is busy in candidate slot, allocation for that candidate is rejected.

Supports multiple faculty names in one course (`A/B`), but scheduling still records provided faculty string and checks conflicts by that value in current flow.

---

## 12) What is global vs local state

### Local (per scheduler sheet run)
- Current timetable DataFrame
- `lecturer_busy`
- `labs_scheduled`
- local break markers in sheet cells

### Shared across departments
- room usage
- elective slot templates
- elective room templates/usages
- combined slots/room ownership
- combined strength totals

This is how one department's decisions influence others.

---

## 13) Output generation flow

After scheduling:

1. Timetable sheets are written (`First_Half`, `Second_Half`).
2. Unscheduled items (if any) are exported to `<dept>_unscheduled_courses.xlsx`.
3. Student workbook is formatted:
   - merged cells for continuous entries,
   - color coding by course code,
   - legends for regular + elective details.
4. Faculty workbook is generated:
   - one sheet per faculty,
   - first and second half sections combined in same sheet.

---

## 14) Is it hardcoded or dynamic?

It is a **hybrid**:

- **Hardcoded**: day list, excluded slots, room policy, cluster mapping, random seed.
- **Dynamic from data**: courses, room capacities, number of departments, L/T/P counts, elective baskets, faculty names, slots list.
- **Heuristic/randomized search**: day shuffling + candidate window selection + retry loops.

So it is not a purely hardcoded timetable; it is data-driven with fixed policy rules.

---

## 15) Why some courses may remain unscheduled

Typical reasons:

- insufficient compatible rooms (especially labs/capacity),
- faculty conflicts,
- slot fragmentation (duration cannot fit),
- too many constraints together.

When this happens, it records rows in:
- `self.unscheduled_courses`
- exported to an Excel file for manual review.

---

## 16) Quick “from scratch” mental model

If explaining to a beginner:

1. Read all slots, courses, rooms.
2. Convert each course into required lecture/tutorial/lab hours.
3. Fill a weekly grid course-by-course.
4. For each session, try a day and find contiguous free slots.
5. Reject slot if teacher busy or room unavailable.
6. Reserve room globally so other departments cannot double-book.
7. For electives and combined courses, save templates so parallel branches follow same pattern.
8. Export pretty Excel files with legends.

That is the full pipeline.

