# The Time Machine — Requirements

**Project:** A 3D visualization that renders any git repository as a living city and plays its history back as an animated, narrated flythrough. Bob (the IBM agent) provides the narration layer — turning commit history into a story a viewer can follow.

**Document purpose:** Capture *what* the system must do, with testable acceptance criteria. No implementation or technology choices appear here; those belong to a later design phase.

---

## 1. User Flows

### UF1 — First-Time Setup
1. User opens the Time Machine.
2. User points it at a repository (local path or remote URL).
3. The system ingests the repository's full history and prepares it for visualization.
4. The system signals when the city is ready to view.

### UF2 — The Flythrough (the headline experience)
1. User opens a prepared repository.
2. The 3D city materializes in its present-day state.
3. User presses play.
4. The city rewinds to the project's beginning, then plays forward through history.
5. As history unfolds, buildings rise, neighborhoods sprawl, and dead districts crumble.
6. Narration plays in sync with the visuals, explaining major events ("This is when the retry logic was bolted on…").
7. The flythrough ends at the present day.

### UF3 — Pause and Inspect
1. During or after playback, the user pauses.
2. The user clicks a building.
3. The system surfaces information about the file that building represents: who has touched it, when it grew or shrank, and a plain-English explanation of its history up to the current playback moment.
4. The user can resume playback from the paused moment.

### UF4 — Jump to a Moment
1. The user scrubs the timeline to a specific point (a date, a release, a commit).
2. The city instantly reflects its state at that moment.
3. Narration for that era is available on demand.

### UF5 — Demo Mode (Reliability Path)
1. Presenter loads a pre-indexed repository before the demo.
2. All narration is already generated and stored.
3. The flythrough runs without depending on live network or live model calls.
4. If anything fails mid-demo, the system degrades gracefully (visuals continue even if narration is unavailable).

---

## 2. Functional Requirements

### Repository Ingestion

**FR-01 — Accept a repository as input.**
The system shall allow a user to specify a git repository to visualize.
- *AC-01.1:* The system accepts a repository identifier from the user.
- *AC-01.2:* The system reports a clear error if the repository cannot be read.
- *AC-01.3:* The system reports progress during ingestion so the user knows it is working.

**FR-02 — Parse the full commit history.**
The system shall extract every commit, including author, timestamp, message, and the files changed.
- *AC-02.1:* For a repository with N commits, the system records N commits' worth of metadata.
- *AC-02.2:* For each commit, the set of changed files and the nature of each change (added, modified, deleted, renamed) is recorded.
- *AC-02.3:* Commits that cannot be parsed are skipped with a logged warning, not a crash.

**FR-03 — Group files into modules.**
The system shall organize files into logical groupings ("neighborhoods") based on the repository's directory structure.
- *AC-03.1:* Every file in the repository belongs to exactly one neighborhood at any given moment.
- *AC-03.2:* Files that move between directories update their neighborhood assignment over time.

### City Generation

**FR-04 — Render each file as a building.**
The system shall represent every file present at the currently-displayed moment as a distinct 3D building.
- *AC-04.1:* Each existing file at time T appears as exactly one building.
- *AC-04.2:* Files that do not exist at time T do not appear.
- *AC-04.3:* Buildings are visually distinguishable from one another (no two files collapse into the same visual element).

**FR-05 — Encode file properties visually.**
The system shall map quantitative file properties to visual attributes of buildings.
- *AC-05.1:* Building height correlates with a measure of file complexity or size.
- *AC-05.2:* Building visual age (e.g. weathering, color) correlates with time since last modification.
- *AC-05.3:* The encoding is consistent across the city — the same property maps to the same visual attribute everywhere.
- *AC-05.4:* A legend or hint is available to the user explaining the encoding.

**FR-06 — Group buildings into neighborhoods.**
The system shall spatially cluster buildings that belong to the same module.
- *AC-06.1:* Files in the same directory/module are placed near each other in 3D space.
- *AC-06.2:* Distinct neighborhoods are visually separable to the eye.

### Time Playback

**FR-07 — Play history forward.**
The system shall animate the city through its full history from earliest to latest commit.
- *AC-07.1:* A full playthrough of the entire history completes in approximately 90 seconds for a typical project (a tunable parameter).
- *AC-07.2:* Time progression is visually smooth, not a series of hard jumps.
- *AC-07.3:* A visible timeline or clock indicates the current moment in history.

**FR-08 — Animate file lifecycle events.**
The system shall visually represent when files are created, grow, shrink, or are deleted.
- *AC-08.1:* New files appear as buildings rising from the ground.
- *AC-08.2:* Deleted files disappear via a visible crumbling or fade-out animation.
- *AC-08.3:* Files that undergo large changes are visually distinguishable from files that change incrementally.

**FR-09 — Playback controls.**
The system shall provide play, pause, scrub-to-moment, and speed-adjust controls.
- *AC-09.1:* The user can pause playback and the city freezes in its current state.
- *AC-09.2:* The user can resume from a paused state without restarting.
- *AC-09.3:* The user can scrub to an arbitrary moment and see the city in that state.
- *AC-09.4:* The user can adjust playback speed within a defined range.

### Camera and Navigation

**FR-10 — Free camera movement.**
The system shall allow the user to navigate the city in 3D.
- *AC-10.1:* The user can pan, zoom, and rotate the view.
- *AC-10.2:* Camera input feels responsive — input causes visible movement within a fraction of a second.

**FR-11 — Cinematic auto-camera (optional flythrough).**
The system shall provide an automatic camera path that produces a cinematic flythrough during playback.
- *AC-11.1:* The auto-camera highlights regions of the city where significant activity is happening at that moment.
- *AC-11.2:* The user can take manual control at any time, overriding the auto-camera.

### Bob Narration

**FR-12 — Generate narration for major epochs.**
The system shall produce a plain-English narration covering the major moments in the repository's history.
- *AC-12.1:* The narration is generated from the commit messages, PR descriptions (where available), and the substance of the diffs themselves.
- *AC-12.2:* The narration identifies notable events (major refactors, periods of high activity, sustained dead periods, large additions or deletions) rather than narrating every commit.
- *AC-12.3:* The narration reads as a coherent story, not a list of commit summaries.

**FR-13 — Sync narration with the visuals.**
The system shall play narration in sync with the corresponding moment in the flythrough.
- *AC-13.1:* When the city is at moment T, the narration playing describes events at or around moment T.
- *AC-13.2:* Pausing the flythrough pauses the narration; resuming resumes it.

**FR-14 — Per-building explanation on demand.**
When the user clicks a building, the system shall provide a plain-English explanation of that file's history up to the current playback moment.
- *AC-14.1:* The explanation references concrete events ("a major rewrite in March 2023," not "this file has changed").
- *AC-14.2:* The explanation is constrained to events that have occurred at or before the current playback moment — it does not spoil the future.
- *AC-14.3:* The explanation appears within a few seconds of the click.

**FR-15 — Pre-rendered narration for reliability.**
The system shall be able to operate using narration that was generated and stored ahead of time.
- *AC-15.1:* Once a repository has been indexed, the flythrough plays end-to-end without any live model calls being required.
- *AC-15.2:* If a live narration call fails mid-session, the pre-rendered version (if available) is used as a fallback.
- *AC-15.3:* Per-building narration that was pre-generated during indexing is available without a live call.

---

## 3. Non-Functional Requirements

**NFR-01 — Demo reliability.**
The system must run a complete demo without requiring live network access to external services.
- *AC-01.1:* A full flythrough of a pre-indexed repository succeeds with the network disabled.

**NFR-02 — Visual clarity.**
A viewer who has never seen the tool before must be able to identify what the city represents within a short, defined onboarding window (e.g. a 15-second intro caption or legend).
- *AC-02.1:* A first-time viewer can correctly answer "what does a building represent?" after seeing the intro.

**NFR-03 — Performance.**
The flythrough must run smoothly on a presenter's laptop without visible stutter.
- *AC-03.1:* For a repository within the supported size range, the animation maintains a smooth frame rate throughout playback.
- *AC-03.2:* Defined size limits are documented (e.g., "supports repositories up to X commits / Y files").

**NFR-04 — Narration quality.**
Narration must read as coherent prose, not as machine-generated boilerplate.
- *AC-04.1:* For a sampled set of narration snippets, a human reader judges each as "tells me something I didn't already know from the commit message alone."
- *AC-04.2:* Narration does not invent events that did not occur in the history.

**NFR-05 — Graceful degradation.**
If any subsystem fails, the rest must continue to function.
- *AC-05.1:* If narration is unavailable, the visuals still play.
- *AC-05.2:* If a single file cannot be rendered, the rest of the city still renders.

---

## 4. Out of Scope (for this version)

To keep the project focused, the following are explicitly excluded:
- Editing the underlying repository from within the tool.
- Visualizing multiple repositories simultaneously.
- Real-time updates as new commits arrive.
- Multi-user / collaborative viewing.
- Anything beyond git as a version-control source.

---

## 5. Open Questions

These need answers before design begins, but are flagged here rather than guessed at:
- What is the upper bound on repository size we commit to supporting for the demo?
- Should narration be text-only, audio (spoken), or both?
- Which specific file property is "complexity" — line count, cyclomatic complexity, churn, something else? (One must be chosen; the choice is a design decision, not a requirements one.)
- For the demo, which repository will we showcase, and have we secured permission to use it on stage?
