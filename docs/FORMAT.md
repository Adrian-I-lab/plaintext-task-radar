# Note format

This is the contract that `taskradar` implements. The code and the tests are checked against it.

## Files

- One Markdown file per project. Any `.md` file under the folder you point the tool at is read.
- Hidden folders (names starting with `.`) are skipped.
- The notes are the source of truth. Every report is derived from them and regenerated on each run.

## Frontmatter

Each note starts with a YAML block between two `---` lines.

| Key | Required | Values |
| --- | --- | --- |
| `title` | yes | Free text. |
| `status` | yes | `active`, `paused`, `done`, or `dropped`. |
| `priority` | yes | `high`, `medium`, or `low`. |
| `deadline` | no | `YYYY-MM-DD`. |
| `updated` | no | `YYYY-MM-DD`, the last time the note was reviewed. |
| `owner` | no | Free text. |

## Tasks

Tasks live under a level-2 heading, `## Tasks`. The section ends at the next heading of level 1 or 2. Task
lines elsewhere in the note are still read, and the linter warns about them. A note without the heading may
still hold tasks.

A task line is a list item: optional indentation, `-` or `*`, at least one space, a one-character marker in
square brackets, then a space and the task text. Indented sub-tasks are tasks in their own right.

There are exactly six markers.

| Marker | Meaning | Live |
| --- | --- | --- |
| `[ ]` | Open | yes |
| `[~]` | In progress | yes |
| `[x]` | Done | no |
| `[-]` | Cancelled | no |
| `[>]` | Migrated elsewhere | no |
| `[d]` | Delegated | no |

Live tasks are the ones on the radar. Live is a fixed list, so a new symbol is never treated as open by
accident. Any other marker is an error, because no reader would ever see that task.

## Signifiers on a task

- Due date: `📅 YYYY-MM-DD`, the same signifier the Obsidian Tasks plugin uses. The ASCII alias
  `due:YYYY-MM-DD` means the same thing.
- Done date: `✅ YYYY-MM-DD`.
- Priority, optional: `⏫` high, `🔼` medium, `🔽` low.
- Delegate: a `[d]` task names who has it as `@name`.

A task with a malformed date keeps its place in the note, but it has no due date until the date is fixed.

## Fenced code

Fenced code blocks (opened with three backticks or three tildes) are ignored entirely. Documentation can
show bad examples without tripping the linter.

## Lint rules

L005 is a warning. Every other rule is an error. `taskradar lint` exits 1 when it finds any error.

**L001. Unknown marker.** The task is invisible to every reader. Common slips get a fix: `[/]` becomes
`[~]`, and `[X]` becomes `[x]`.

```text
bad:  - [/] Paint the fence
good: - [~] Paint the fence
```

**L002. Malformed date after a due or done signifier.** The deadline silently drops off the radar.

```text
bad:  - [ ] Book the hall 📅 29 Sep
good: - [ ] Book the hall 📅 2026-09-29
```

**L003. No space after the bullet.** Markdown does not treat the line as a list item, so it is not a task.
Only the six markers and the two common slips count, so a footnote such as `*[1] Reference` is left alone.

```text
bad:  -[ ] Call the plumber
good: - [ ] Call the plumber
```

**L004. Delegated task with no owner.** Nobody owns the work.

```text
bad:  - [d] Collect the keys
good: - [d] Collect the keys @sam
```

**L005. Task outside `## Tasks`.** The task is read anyway. The warning is about tidiness.

```text
bad:  a task line above the "## Tasks" heading
good: the same line moved under "## Tasks"
```

**L006. Frontmatter missing or invalid.** Status and deadline checks cannot run. This covers a missing
block, YAML that does not parse, a missing required key, an unknown status or priority, and a `deadline`
or `updated` value that is not a real `YYYY-MM-DD` date.

```text
bad:  status: on-hold
good: status: paused
```

## Radar definitions

`today` comes from `--today` when it is given, so the output is reproducible. Day counts are whole
calendar days.

- **Overdue.** A live task whose due date is before today.
- **Due soon.** A live task due from today to today plus the horizon, inclusive. The horizon defaults to
  7 days.
- **Stale.** A live task with no due date, in an active project whose age is more than the stale limit
  (default 21 days). Age is measured from `updated`, else the file's last git commit date, else the
  file's modification time. Modification times change on a fresh clone, so they are the last resort.
- **Project deadline.** An active project's `deadline` is listed as an overdue or due soon item, unless
  a live task in the same note already carries that date.

Overdue and due soon cover live tasks in every note, whatever the project status.

Project checks:

- `no-live-tasks`: an active project with no live task.
- `live-tasks-in-closed-project`: a done or dropped project that still has live tasks.
- `deadline-passed`: an active project whose deadline is before today.
