# Expected results for the demo vault

Everything in this folder is invented. The reference date is Wednesday 2026-10-14, always passed as
`--today 2026-10-14`. With the default horizon of 7 days, "due soon" runs from 2026-10-14 to 2026-10-21
inclusive. The default stale limit is 21 days. This file is not a note. Its name is all capitals, so the
tool skips it (see docs/FORMAT.md).

## Planted cases

| # | Case | File:line | Expected |
| --- | --- | --- | --- |
| 1 | Overdue open task | community-garden.md:15 | Overdue, 5 days |
| 2 | Overdue in-progress `[~]` task | community-garden.md:16 | Overdue, 2 days |
| 3 | Overdue indented sub-task | community-garden.md:18 | Overdue, 1 day |
| 4 | Task due today | bike-repair.md:13 | Due soon, 0 days |
| 5 | Task due in exactly 7 days | book-club.md:18 | Due soon, 7 days |
| 6 | Task due in 8 days | community-garden.md:20 | Not on the radar |
| 7 | Done task with a past due date | community-garden.md:19 | Not on the radar |
| 8 | Cancelled, migrated, and delegated tasks with past due dates | bike-repair.md:16, bike-repair.md:17, book-club.md:15 | Not on the radar |
| 9 | `[/]` marker | bike-repair.md:15 | L001, fix `[~]` |
| 10 | `[X]` marker | book-club.md:17 | L001, fix `[x]` |
| 11 | `📅 29 Sep` | conference-talk.md:15 | L002 |
| 12 | `-[ ]` with no space | conference-talk.md:16 | L003 |
| 13 | `[d]` with no `@name` | book-club.md:16 | L004 |
| 14 | Task above the `## Tasks` heading | book-club.md:11 | L005, and due soon (6 days) |
| 15 | Status `on-hold` | tidy-csv-library.md:3 | L006 |
| 16 | Fenced block holding `- [/] example` | tidy-csv-library.md:21 | No finding |
| 17 | Open undated task in an active project last updated 2026-09-01 | house-painting.md:12 | Stale, 43 days |
| 18 | Active project with no live task | half-marathon.md | `no-live-tasks` |
| 19 | Done project with one live task | recipe-zine.md:13 | `live-tasks-in-closed-project` |
| 20 | Active project whose deadline (2026-10-07) has passed | conference-talk.md:5 | `deadline-passed`, and overdue (7 days) |
| 21 | ASCII alias `due:2026-10-16` | bike-repair.md:14 | Due soon, 2 days |
| 22 | Task text that mentions README and CLAUDE | tidy-csv-library.md:14 | Due soon, 5 days |

Two further details are deliberate. The bike repair deadline (2026-10-16) is not listed on its own,
because the live task on bike-repair.md:14 carries the same date. The live tasks on
community-garden.md:17 and conference-talk.md:15 have no due date, but their notes were updated less
than 21 days ago, so they are not stale.

## Totals

Overdue: cases 1, 2, 3, and the conference talk deadline (case 20). 3 + 1 = 4.

Due soon: cases 4, 21, 22, 14, and 5 (0, 2, 5, 6, and 7 days). 5.

Stale: case 17 only. 1.

Project issues: cases 18, 19, and 20. 1 + 1 + 1 = 3.

Lint: L001 twice (cases 9 and 10), and L002 to L006 once each (cases 11 to 15). 2 + 5 = 7 findings,
of which 6 are errors and 1 (L005) is a warning.

| Measure | Expected |
| --- | --- |
| Overdue | 4 |
| Due soon | 5 |
| Stale | 1 |
| Project issue `no-live-tasks` | 1 |
| Project issue `live-tasks-in-closed-project` | 1 |
| Project issue `deadline-passed` | 1 |
| L001 | 2 |
| L002 | 1 |
| L003 | 1 |
| L004 | 1 |
| L005 | 1 |
| L006 | 1 |
| Lint errors | 6 |
| Lint warnings | 1 |
