# System Architecture Documentation

## Table of Contents
1. [High-Level Overview](#high-level-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Design Patterns](#design-patterns)
6. [Module Responsibilities](#module-responsibilities)
7. [Integration Points](#integration-points)

---

## High-Level Overview

The Time Machine is a 3D visualization system that transforms git repositories into living cities and plays their history back as animated, narrated flythroughs. The system follows a pipeline architecture with clear separation of concerns across ingestion, processing, rendering, and narration layers.

### System Goals
- **Visualize repository evolution**: Transform abstract git history into intuitive 3D representations
- **AI-powered storytelling**: Generate coherent narratives using IBM Watson/Bob
- **Interactive exploration**: Enable users to pause, inspect, and navigate through history
- **Demo-ready**: Support offline mode with pre-generated content for reliable presentations

### Architecture Diagram (High-Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                    (React + Three.js Frontend)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Flask API Server                         │
│                    (Request Routing & State)                    │
└─────┬──────────────┬──────────────┬──────────────┬─────────────┘
      │              │              │              │
      ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│Ingestion │  │   City   │  │Rendering │  │  Narration   │
│  Layer   │  │Generator │  │  Engine  │  │   Service    │
└──────────┘  └──────────┘  └──────────┘  └──────────────┘
      │              │              │              │
      ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│   Git    │  │  3D City │  │ ModernGL │  │ IBM Watson/  │
│Repository│  │   Data   │  │ Graphics │  │     Bob      │
└──────────┘  └──────────┘  └──────────┘  └──────────────┘
```

---

## Component Architecture

### 1. Ingestion Layer (`src/time_machine/ingestion/`)

**Purpose**: Parse git repositories and extract structured data about commits, files, and changes.

**Components**:
- **RepositoryIngester**: Main entry point for repository ingestion
  - Accepts local paths or remote URLs
  - Clones/copies repositories to data directory
  - Validates git repositories
  - Reports progress and errors
  
- **CommitParser**: Parses git commit history
  - Extracts commit metadata (SHA, author, timestamp, message)
  - Analyzes file changes (added, modified, deleted, renamed)
  - Calculates line changes (additions/deletions)
  - Builds chronological commit timeline
  
- **FileGrouper**: Organizes files into logical neighborhoods
  - Groups files by directory structure
  - Creates hierarchical neighborhood tree
  - Calculates neighborhood statistics
  - Supports nested directory structures

**Data Structures**:
```python
CommitInfo:
  - sha: str
  - author: str
  - timestamp: datetime
  - message: str
  - files_changed: List[FileChange]

FileChange:
  - path: str
  - change_type: ChangeType (ADDED/MODIFIED/DELETED/RENAMED)
  - lines_added: int
  - lines_deleted: int
  - old_path: Optional[str]

Neighborhood:
  - path: str
  - name: str
  - parent: Optional[str]
  - files: Set[str]
  - subdirectories: Set[str]
```

### 2. City Generation Layer (`src/time_machine/city/`)

**Purpose**: Transform repository data into 3D city representation.

**Components**:
- **CityGenerator**: Core city generation engine
  - Processes commit history to build file metrics
  - Calculates spatial layout for neighborhoods
  - Generates buildings for all files
  - Supports time-travel (city at any commit)
  - Implements multiple layout algorithms

**Visual Encoding**:
- **Height**: Logarithmic scale based on lines of code
- **Color**: Temperature scale based on modification count
  - Blue (cold) = low activity
  - Red (hot) = high activity
- **Brightness**: Age-based weathering
  - Bright = recently modified
  - Dark = old/stale

**Layout Algorithms**:
- **Grid Layout**: Organizes neighborhoods in grid pattern
  - Root neighborhoods positioned first
  - Nested neighborhoods offset from parents
  - Configurable spacing and grid size

**Data Structures**:
```python
Building:
  - file_path: str
  - position: (x, y, z)
  - height: float
  - base_size: (width, depth)
  - color: (r, g, b)
  - neighborhood: str
  - created_at: commit_sha
  - last_modified: commit_sha
  - modification_count: int
  - lines_of_code: int

CityState:
  - commit_sha: str
  - timestamp: datetime
  - buildings: Dict[str, Building]
  - neighborhoods: Dict[str, metadata]
  - layout_config: LayoutConfig
  - statistics: Dict[str, Any]
```

### 3. Rendering Engine (`src/time_machine/rendering/`)

**Purpose**: Render 3D city visualization with animations and camera controls.

**Components**:
- **CityRenderer**: ModernGL-based 3D renderer
  - GPU-accelerated rendering
  - Phong shading for realistic lighting
  - Building mesh generation
  - Neighborhood boundary visualization
  - Camera management

- **AnimationSystem**: Handles building animations
  - Construction animations (buildings rising)
  - Destruction animations (buildings falling)
  - Modification effects (color pulses)
  - Smooth interpolation

- **CameraController**: Camera movement and controls
  - Orbit controls (rotate around target)
  - Zoom controls (dolly in/out)
  - Pan controls (translate view)
  - Auto-positioning for full city view

- **AutoCamera**: Cinematic camera automation
  - Follows areas of high activity
  - Smooth transitions between points of interest
  - Configurable movement speed and easing
  - Respects user manual control

- **PlaybackController**: Manages playback state
  - Play/pause/stop controls
  - Speed adjustment (0.5x - 2.0x)
  - Loop mode
  - State change callbacks

- **TimelineController**: Time management
  - Maps commits to playback timeline
  - Handles scrubbing to specific times
  - Calculates current commit based on time
  - Provides time-based queries

**Rendering Pipeline**:
```
1. Load CityState
2. Generate building meshes (vertices, normals, colors)
3. Upload to GPU (VBOs, VAOs)
4. Each frame:
   - Update camera matrices
   - Set shader uniforms (view, projection, lighting)
   - Render buildings (triangles)
   - Render neighborhood boundaries (lines)
   - Apply post-processing effects
```

### 4. Narration Service (`src/time_machine/narration/`)

**Purpose**: Generate and synchronize AI-powered narration with visual playback.

**Components**:
- **BobClient**: IBM Watson/Bob API integration
  - Authenticates with Watson API
  - Sends prompts for narration generation
  - Handles rate limiting and retries
  - Supports offline mode with cached responses

- **EpochGenerator**: Identifies significant time periods
  - Analyzes commit history for major events
  - Calculates significance scores
  - Groups related commits into epochs
  - Identifies key contributors and files

- **BuildingExplainer**: Generates file-specific explanations
  - Analyzes individual file history
  - Explains purpose and evolution
  - Highlights major changes
  - Provides context for current state

- **NarrationSync**: Synchronizes narration with playback
  - Maps epoch times to playback timeline
  - Manages narration segments
  - Triggers callbacks for UI updates
  - Handles pause/resume correctly

- **NarrationStorage**: Persists narration data
  - Saves generated narrations to disk
  - Loads pre-generated narrations
  - Supports offline demo mode
  - Caches for performance

**Narration Pipeline**:
```
1. Analyze commit history
2. Identify epochs (significant periods)
3. Generate narration for each epoch
4. Map epochs to playback timeline
5. Synchronize with visual playback
6. Deliver narration at appropriate times
```

### 5. API Server (`src/time_machine/api/`)

**Purpose**: Provide REST API for frontend communication.

**Endpoints**:
- `GET /api/repositories` - List ingested repositories
- `POST /api/repositories/ingest` - Ingest new repository
- `GET /api/city/:repo_name` - Get city data for repository
- `GET /api/narration/:repo_name` - Get narration data
- `POST /api/narration/generate` - Generate narration on-demand
- `GET /api/timeline/:repo_name` - Get timeline data
- `GET /api/building/:repo_name/:file_path` - Get building details

**Architecture**:
- Flask application with CORS support
- RESTful design principles
- JSON request/response format
- Error handling and validation
- Session management for long-running operations

### 6. Utilities (`src/time_machine/utils/`)

**Purpose**: Shared utilities and configuration.

**Components**:
- **Config**: Centralized configuration management
  - Environment variable loading
  - Default values
  - Path management
  - Feature flags

- **Logger**: Structured logging
  - Colorized console output
  - File logging
  - Log level configuration
  - Module-specific loggers

- **ErrorHandler**: Error handling utilities
  - Custom exception types
  - Error reporting
  - Graceful degradation

---

## Data Flow

### 1. Repository Ingestion Flow

```
User Input (path/URL)
    │
    ▼
RepositoryIngester
    │
    ├─► Validate repository
    ├─► Clone/copy to data directory
    ├─► CommitParser: Extract commit history
    │       │
    │       ├─► Parse commits chronologically
    │       ├─► Analyze file changes
    │       └─► Calculate metrics
    │
    ├─► FileGrouper: Organize into neighborhoods
    │       │
    │       ├─► Build directory tree
    │       ├─► Group files by directory
    │       └─► Calculate statistics
    │
    └─► Save metadata to disk
            │
            ▼
        Repository ready for visualization
```

### 2. City Generation Flow

```
Commit History + Neighborhoods
    │
    ▼
CityGenerator
    │
    ├─► Calculate file metrics
    │       │
    │       ├─► Track creation/modification
    │       ├─► Count modifications
    │       └─► Calculate lines of code
    │
    ├─► Calculate neighborhood positions
    │       │
    │       ├─► Apply layout algorithm
    │       ├─► Position root neighborhoods
    │       └─► Position nested neighborhoods
    │
    ├─► Generate buildings
    │       │
    │       ├─► Calculate building properties
    │       │   ├─► Height (from LOC)
    │       │   ├─► Color (from activity)
    │       │   └─► Position (from layout)
    │       │
    │       └─► Create Building objects
    │
    └─► Create CityState
            │
            ▼
        3D city data ready for rendering
```

### 3. Rendering Flow

```
CityState
    │
    ▼
CityRenderer
    │
    ├─► Initialize ModernGL context
    ├─► Compile shaders
    ├─► Generate building meshes
    │       │
    │       ├─► Create vertices
    │       ├─► Create normals
    │       └─► Create colors
    │
    ├─► Upload to GPU
    │       │
    │       ├─► Create VBOs
    │       └─► Create VAOs
    │
    └─► Render loop
            │
            ├─► Update camera
            ├─► Update animations
            ├─► Set shader uniforms
            ├─► Render buildings
            └─► Render UI overlays
                    │
                    ▼
                Visual output
```

### 4. Narration Flow

```
Commit History
    │
    ▼
EpochGenerator
    │
    ├─► Identify significant periods
    ├─► Calculate significance scores
    └─► Create Epoch objects
            │
            ▼
        BobClient
            │
            ├─► Generate prompts
            ├─► Call Watson API
            └─► Parse responses
                    │
                    ▼
                EpochNarration objects
                    │
                    ▼
                NarrationSync
                    │
                    ├─► Map to timeline
                    ├─► Create segments
                    └─► Synchronize with playback
                            │
                            ▼
                        Narration delivery
```

---

## Technology Stack

### Backend (Python 3.9+)
- **GitPython/pygit2**: Git repository parsing
- **ModernGL**: GPU-accelerated 3D rendering
- **pyrr**: 3D math (matrices, vectors)
- **NumPy**: Numerical computations
- **Flask**: Web server and REST API
- **ibm-watson**: IBM Watson/Bob integration
- **pandas**: Data processing
- **pytest**: Testing framework

### Frontend (JavaScript/TypeScript)
- **React**: UI framework
- **Three.js**: WebGL 3D rendering
- **Axios**: HTTP client
- **Vite**: Build tool and dev server

### Infrastructure
- **Python virtual environment**: Dependency isolation
- **npm**: JavaScript package management
- **Git**: Version control
- **JSON**: Data serialization

---

## Design Patterns

### 1. Pipeline Pattern
The system follows a clear pipeline architecture:
```
Ingestion → City Generation → Rendering → Narration
```
Each stage transforms data and passes it to the next stage.

### 2. Repository Pattern
- **RepositoryIngester**: Abstracts git repository access
- **NarrationStorage**: Abstracts narration persistence
- Enables testing with mock repositories

### 3. Observer Pattern
- **PlaybackController**: Notifies observers of state changes
- **NarrationSync**: Listens to playback events
- **AnimationSystem**: Responds to timeline events
- Enables loose coupling between components

### 4. Strategy Pattern
- **Layout algorithms**: Pluggable layout strategies (grid, force-directed)
- **Visual encoding**: Configurable encoding strategies
- Enables experimentation with different approaches

### 5. Factory Pattern
- **BuildingMesh**: Creates mesh data for different building types
- **EpochGenerator**: Creates epoch objects from commit analysis
- Centralizes object creation logic

### 6. Singleton Pattern
- **Config**: Single source of configuration
- **Logger**: Centralized logging
- Ensures consistency across application

### 7. Command Pattern
- **CLI commands**: Each command is a separate handler
- Enables easy addition of new commands
- Supports undo/redo for future features

### 8. Scene Graph Pattern
- **CityRenderer**: Organizes 3D objects hierarchically
- Buildings grouped by neighborhoods
- Enables efficient rendering and culling

---

## Module Responsibilities

### Ingestion Module
**Responsibility**: Extract and parse git repository data
- ✅ Accept repository paths/URLs
- ✅ Validate git repositories
- ✅ Parse commit history
- ✅ Analyze file changes
- ✅ Group files into neighborhoods
- ✅ Report progress and errors

### City Module
**Responsibility**: Transform repository data into 3D city
- ✅ Calculate file metrics from history
- ✅ Apply layout algorithms
- ✅ Generate building properties
- ✅ Create city state snapshots
- ✅ Support time-travel through history
- ✅ Serialize/deserialize city data

### Rendering Module
**Responsibility**: Visualize 3D city with animations
- ✅ Render buildings as 3D meshes
- ✅ Apply visual encoding
- ✅ Animate building changes
- ✅ Control camera movement
- ✅ Manage playback state
- ✅ Handle user interactions

### Narration Module
**Responsibility**: Generate and deliver AI narration
- ✅ Identify significant epochs
- ✅ Generate narration via Watson/Bob
- ✅ Synchronize with visual timeline
- ✅ Explain individual buildings
- ✅ Support offline mode
- ✅ Cache generated content

### API Module
**Responsibility**: Provide REST API for frontend
- ✅ Route HTTP requests
- ✅ Validate input
- ✅ Coordinate between modules
- ✅ Handle errors gracefully
- ✅ Manage sessions
- ✅ Serve static files

### Utils Module
**Responsibility**: Shared utilities and configuration
- ✅ Load configuration
- ✅ Provide logging
- ✅ Handle errors
- ✅ Manage paths
- ✅ Validate data

---

## Integration Points

### 1. Git Integration
- **Library**: GitPython/pygit2
- **Purpose**: Read repository data
- **Interface**: Repository, Commit, Tree, Blob objects
- **Error Handling**: InvalidGitRepositoryError, GitCommandError

### 2. IBM Watson/Bob Integration
- **Library**: ibm-watson SDK
- **Purpose**: Generate AI narration
- **Interface**: REST API with authentication
- **Error Handling**: Rate limiting, network errors, API errors
- **Offline Mode**: Cached responses for demo mode

### 3. ModernGL Integration
- **Library**: ModernGL + moderngl-window
- **Purpose**: GPU-accelerated 3D rendering
- **Interface**: Context, Program, Buffer, VertexArray
- **Shaders**: GLSL vertex and fragment shaders

### 4. Frontend Integration
- **Protocol**: REST API over HTTP
- **Format**: JSON request/response
- **CORS**: Enabled for cross-origin requests
- **WebSocket**: (Future) For real-time updates

### 5. File System Integration
- **Data Directory**: `data/` for repositories and cache
- **Narration Storage**: `data/narration/` for cached narrations
- **Repository Storage**: `data/repositories/` for ingested repos
- **Cache**: `data/cache/` for temporary files

### 6. Configuration Integration
- **Environment Variables**: `.env` file for secrets
- **Config Class**: Centralized configuration access
- **Defaults**: Sensible defaults for all settings
- **Validation**: Type checking and range validation

---

## Performance Considerations

### 1. Repository Size Limits
- **Max commits**: 10,000 (configurable)
- **Max files**: 5,000 (configurable)
- **Rationale**: Balance between detail and performance

### 2. Rendering Optimization
- **GPU acceleration**: ModernGL for fast rendering
- **Instancing**: (Future) Render many buildings efficiently
- **Culling**: (Future) Don't render off-screen buildings
- **LOD**: (Future) Level-of-detail for distant buildings

### 3. Narration Caching
- **Pre-generation**: Generate all narrations upfront for demos
- **Disk storage**: Cache narrations to avoid API calls
- **Offline mode**: Use cached narrations when network unavailable

### 4. Memory Management
- **Streaming**: Process commits in batches for large repos
- **Cleanup**: Release GPU resources when done
- **Garbage collection**: Python GC handles most cleanup

---

## Security Considerations

### 1. API Security
- **Authentication**: (Future) API key or OAuth
- **Rate limiting**: Prevent abuse
- **Input validation**: Sanitize all user input
- **CORS**: Restrict allowed origins

### 2. Repository Access
- **Path validation**: Prevent directory traversal
- **Git validation**: Ensure valid git repositories
- **Sandboxing**: Isolate repository operations

### 3. Watson API
- **Credentials**: Store in environment variables
- **HTTPS**: Encrypted communication
- **Error handling**: Don't expose API keys in errors

---

## Extensibility

### Future Enhancements
1. **Additional layout algorithms**: Force-directed, treemap
2. **More visual encodings**: File type colors, author attribution
3. **Interactive features**: Click buildings for details, search
4. **Export capabilities**: Video export, screenshots
5. **Collaboration features**: Multi-user viewing, annotations
6. **Advanced analytics**: Code quality metrics, hotspot detection
7. **Plugin system**: Custom visualizations and narrations

### Extension Points
- **Layout algorithms**: Implement `LayoutAlgorithm` interface
- **Visual encodings**: Subclass `VisualEncoding`
- **Narration generators**: Implement `NarrationGenerator` interface
- **Renderers**: Alternative to ModernGL (WebGL, Vulkan)

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-16  
**Maintained By**: IBM Bob Hackathon Team