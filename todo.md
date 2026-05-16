# The Time Machine - Project Todo List

This document breaks down the implementation tasks for The Time Machine project - a 3D visualization that renders git repositories as living cities with animated history playback and AI-generated narration.

## Project Overview
Transform any git repository into a 3D city where files are buildings, directories are neighborhoods, and history plays back as an animated, narrated flythrough.

---

## Phase 1: Foundation & Setup

### ✅ Task 1: Set up project structure and development environment
**Status:** Pending  
**Description:** Initialize the project with necessary tooling, dependencies, and folder structure.  
**Acceptance Criteria:**
- Project repository created with appropriate .gitignore
- Development dependencies installed (3D rendering library, git parsing tools, etc.)
- Build system configured
- Basic README with setup instructions

---

## Phase 2: Repository Ingestion

### ✅ Task 2: Implement repository ingestion - accept repository input (FR-01)
**Status:** Pending  
**Requirements:** FR-01  
**Acceptance Criteria:**
- AC-01.1: System accepts repository identifier from user
- AC-01.2: Clear error reporting if repository cannot be read
- AC-01.3: Progress reporting during ingestion

### ✅ Task 3: Implement repository ingestion - parse full commit history (FR-02)
**Status:** Pending  
**Requirements:** FR-02  
**Acceptance Criteria:**
- AC-02.1: Record all N commits with metadata (author, timestamp, message)
- AC-02.2: Track changed files and change types (added, modified, deleted, renamed)
- AC-02.3: Skip unparseable commits with logged warnings (no crashes)

### ✅ Task 4: Implement repository ingestion - group files into modules/neighborhoods (FR-03)
**Status:** Pending  
**Requirements:** FR-03  
**Acceptance Criteria:**
- AC-03.1: Every file belongs to exactly one neighborhood at any moment
- AC-03.2: Files moving between directories update neighborhood assignment over time

---

## Phase 3: 3D City Generation

### ✅ Task 5: Design and implement 3D city generation system
**Status:** Pending  
**Description:** Core architecture for rendering the city, including scene management, rendering pipeline, and data structures.  
**Deliverables:**
- Scene graph architecture
- Rendering pipeline
- Data model for city state at any point in time

### ✅ Task 6: Implement building rendering - one building per file (FR-04)
**Status:** Pending  
**Requirements:** FR-04  
**Acceptance Criteria:**
- AC-04.1: Each existing file at time T appears as exactly one building
- AC-04.2: Non-existent files at time T do not appear
- AC-04.3: Buildings are visually distinguishable from one another

### ✅ Task 7: Implement visual encoding - map file properties to building attributes (FR-05)
**Status:** Pending  
**Requirements:** FR-05  
**Acceptance Criteria:**
- AC-05.1: Building height correlates with file complexity/size
- AC-05.2: Visual age (weathering, color) correlates with time since last modification
- AC-05.3: Consistent encoding across the city
- AC-05.4: Legend/hint available explaining the encoding

### ✅ Task 8: Implement neighborhood clustering - spatial grouping of related files (FR-06)
**Status:** Pending  
**Requirements:** FR-06  
**Acceptance Criteria:**
- AC-06.1: Files in same directory/module placed near each other in 3D space
- AC-06.2: Distinct neighborhoods are visually separable

---

## Phase 4: Time Playback & Animation

### ✅ Task 9: Implement time playback - forward history animation (FR-07)
**Status:** Pending  
**Requirements:** FR-07  
**Acceptance Criteria:**
- AC-07.1: Full playthrough completes in ~90 seconds (tunable)
- AC-07.2: Visually smooth time progression (no hard jumps)
- AC-07.3: Visible timeline/clock indicating current moment

### ✅ Task 10: Implement file lifecycle animations - create, grow, shrink, delete (FR-08)
**Status:** Pending  
**Requirements:** FR-08  
**Acceptance Criteria:**
- AC-08.1: New files appear as buildings rising from ground
- AC-08.2: Deleted files disappear via crumbling/fade-out animation
- AC-08.3: Large changes visually distinguishable from incremental changes

### ✅ Task 11: Implement playback controls - play, pause, scrub, speed adjust (FR-09)
**Status:** Pending  
**Requirements:** FR-09  
**Acceptance Criteria:**
- AC-09.1: User can pause playback (city freezes)
- AC-09.2: User can resume from paused state
- AC-09.3: User can scrub to arbitrary moment
- AC-09.4: User can adjust playback speed within defined range

---

## Phase 5: Camera & Navigation

### ✅ Task 12: Implement free camera movement - pan, zoom, rotate (FR-10)
**Status:** Pending  
**Requirements:** FR-10  
**Acceptance Criteria:**
- AC-10.1: User can pan, zoom, and rotate the view
- AC-10.2: Camera input feels responsive (sub-second response)

### ✅ Task 13: Implement cinematic auto-camera for flythrough (FR-11)
**Status:** Pending  
**Requirements:** FR-11  
**Acceptance Criteria:**
- AC-11.1: Auto-camera highlights regions with significant activity
- AC-11.2: User can take manual control, overriding auto-camera

---

## Phase 6: Bob Narration Integration

### ✅ Task 14: Integrate Bob/IBM agent for narration generation
**Status:** Pending  
**Description:** Set up connection to IBM's Bob agent for AI-generated narration.  
**Deliverables:**
- API integration with Bob/IBM agent
- Authentication and error handling
- Narration request/response data structures

### ✅ Task 15: Implement narration generation for major epochs (FR-12)
**Status:** Pending  
**Requirements:** FR-12  
**Acceptance Criteria:**
- AC-12.1: Narration generated from commit messages, PR descriptions, and diffs
- AC-12.2: Identifies notable events (refactors, high activity, dead periods, large changes)
- AC-12.3: Reads as coherent story, not list of commit summaries

### ✅ Task 16: Implement narration sync with visuals (FR-13)
**Status:** Pending  
**Requirements:** FR-13  
**Acceptance Criteria:**
- AC-13.1: Narration at moment T describes events at/around moment T
- AC-13.2: Pausing flythrough pauses narration; resuming resumes it

### ✅ Task 17: Implement per-building explanation on click (FR-14)
**Status:** Pending  
**Requirements:** FR-14  
**Acceptance Criteria:**
- AC-14.1: Explanation references concrete events with dates
- AC-14.2: Explanation constrained to events at/before current playback moment
- AC-14.3: Explanation appears within a few seconds of click

### ✅ Task 18: Implement pre-rendered narration storage and fallback (FR-15)
**Status:** Pending  
**Requirements:** FR-15  
**Acceptance Criteria:**
- AC-15.1: Indexed repository plays end-to-end without live model calls
- AC-15.2: Failed live calls fall back to pre-rendered version
- AC-15.3: Pre-generated per-building narration available without live call

---

## Phase 7: Demo Mode & Reliability

### ✅ Task 19: Implement demo mode with offline capability (UF5, NFR-01)
**Status:** Pending  
**Requirements:** UF5, NFR-01  
**Acceptance Criteria:**
- Pre-indexed repository loads successfully
- All narration pre-generated and stored
- Flythrough runs without live network/model calls
- Graceful degradation if anything fails mid-demo
- Full flythrough succeeds with network disabled

### ✅ Task 20: Create visual legend/onboarding for first-time viewers (NFR-02)
**Status:** Pending  
**Requirements:** NFR-02  
**Acceptance Criteria:**
- AC-02.1: First-time viewer can answer "what does a building represent?" after intro
- 15-second intro caption or legend available
- Clear visual encoding explanation

### ✅ Task 21: Optimize performance for smooth playback (NFR-03)
**Status:** Pending  
**Requirements:** NFR-03  
**Acceptance Criteria:**
- AC-03.1: Animation maintains smooth frame rate throughout playback
- AC-03.2: Defined size limits documented (X commits / Y files supported)
- Runs smoothly on presenter's laptop without stutter

### ✅ Task 22: Implement graceful degradation for subsystem failures (NFR-05)
**Status:** Pending  
**Requirements:** NFR-05  
**Acceptance Criteria:**
- AC-05.1: If narration unavailable, visuals still play
- AC-05.2: If single file cannot render, rest of city still renders
- Error handling throughout system

---

## Phase 8: Testing & Documentation

### ✅ Task 23: Create comprehensive test suite for all acceptance criteria
**Status:** Pending  
**Description:** Implement automated tests covering all functional and non-functional requirements.  
**Deliverables:**
- Unit tests for core components
- Integration tests for user flows (UF1-UF5)
- Performance benchmarks
- Test coverage report

### ✅ Task 24: Document system architecture and design decisions
**Status:** Pending  
**Description:** Create technical documentation explaining system design.  
**Deliverables:**
- Architecture diagrams
- Component interaction documentation
- Technology choices and rationale
- API documentation

### ✅ Task 25: Document supported repository size limits
**Status:** Pending  
**Requirements:** NFR-03  
**Description:** Define and document the boundaries of what the system can handle.  
**Deliverables:**
- Maximum commits supported
- Maximum files supported
- Performance characteristics at various scales

---

## Phase 9: Open Questions & Demo Preparation

### ✅ Task 26: Answer open questions - repository size bounds, narration format, complexity metric
**Status:** Pending  
**Description:** Resolve the open questions from requirements section 5.  
**Questions to Answer:**
- What is the upper bound on repository size for the demo?
- Should narration be text-only, audio (spoken), or both?
- Which file property represents "complexity"? (line count, cyclomatic complexity, churn, etc.)
- Which repository will we showcase in the demo?
- Have we secured permission to use it on stage?

### ✅ Task 27: Select and prepare demo repository
**Status:** Pending  
**Description:** Choose an appropriate repository for the demo and prepare it.  
**Deliverables:**
- Demo repository selected
- Permission secured (if needed)
- Repository fully indexed
- All narration pre-generated
- Demo tested end-to-end

### ✅ Task 28: Create user documentation and demo script
**Status:** Pending  
**Description:** Prepare materials for presenting and using the tool.  
**Deliverables:**
- User guide
- Demo script with talking points
- Troubleshooting guide
- FAQ document

### ✅ Task 29: Perform end-to-end testing with demo repository
**Status:** Pending  
**Description:** Comprehensive testing of the complete system with the chosen demo repository.  
**Test Scenarios:**
- All user flows (UF1-UF5)
- Offline demo mode
- Performance under demo conditions
- Error recovery scenarios

### ✅ Task 30: Final polish and demo rehearsal
**Status:** Pending  
**Description:** Final preparations before the demo.  
**Deliverables:**
- UI polish and visual refinements
- Demo rehearsal completed
- Backup plans for common failure scenarios
- Presenter training materials

---

## Notes

### Out of Scope (Explicitly Excluded)
- Editing the repository from within the tool
- Visualizing multiple repositories simultaneously
- Real-time updates as new commits arrive
- Multi-user/collaborative viewing
- Version control systems other than git

### Key Success Metrics
- Demo runs smoothly without network access
- Narration tells a coherent story
- First-time viewers understand the visualization within 15 seconds
- System handles the demo repository without performance issues

---

## Task Status Legend
- `[ ]` = Pending (not started)
- `[-]` = In Progress (currently being worked on)
- `[x]` = Completed (fully finished)
