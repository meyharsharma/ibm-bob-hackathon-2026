# The Time Machine - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Usage Examples](#usage-examples)
5. [Configuration Options](#configuration-options)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [FAQ](#faq)
8. [API Reference](#api-reference)

---

## Introduction

The Time Machine transforms any git repository into an immersive 3D city visualization where files are buildings and history comes alive through animated flythroughs with AI-generated narration.

### What You Can Do
- 📊 **Visualize repository structure** as a 3D city
- ⏰ **Watch history unfold** through animated playback
- 🎙️ **Listen to AI narration** explaining major events
- 🔍 **Inspect individual files** and their evolution
- 🎮 **Control playback** with interactive controls
- 📴 **Run offline demos** with pre-generated content

### System Requirements
- **Operating System**: macOS, Linux, or Windows
- **Python**: 3.9 or higher
- **Node.js**: 18 or higher
- **Git**: Any recent version
- **RAM**: 4GB minimum, 8GB recommended
- **GPU**: OpenGL 3.3+ compatible graphics card

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/time-machine.git
cd time-machine
```

### Step 2: Set Up Python Environment

#### On macOS/Linux:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

#### On Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Step 3: Set Up Frontend

```bash
# Install Node.js dependencies
npm install
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

**Required Configuration** (in `.env`):
```bash
# IBM Watson/Bob API Credentials
IBM_WATSON_API_KEY=your_api_key_here
IBM_WATSON_URL=your_watson_url
IBM_WATSON_ASSISTANT_ID=your_assistant_id

# Optional: Adjust limits
MAX_COMMITS=10000
MAX_FILES=5000
```

### Step 5: Verify Installation

```bash
# Check Python installation
time-machine --help

# Check frontend installation
npm run dev
```

If both commands work without errors, you're ready to go! 🎉

---

## Quick Start

### Running Your First Visualization

#### 1. Start the Backend Server

Open a terminal and run:
```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Start the backend server
python -m time_machine.api.server
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: off
```

#### 2. Start the Frontend Development Server

Open a **new terminal** and run:
```bash
npm run dev
```

You should see:
```
  VITE v4.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

#### 3. Open in Browser

Navigate to `http://localhost:5173` in your web browser.

#### 4. Ingest a Repository

You can ingest a repository in two ways:

**Option A: Using the CLI**
```bash
# Ingest a local repository
time-machine ingest /path/to/your/repository

# Ingest a remote repository
time-machine ingest https://github.com/user/repo.git

# Ingest with custom name
time-machine ingest /path/to/repo --name my-project
```

**Option B: Using the Web UI**
1. Click "Add Repository" in the web interface
2. Enter the repository path or URL
3. Click "Ingest"
4. Wait for ingestion to complete

#### 5. View the Visualization

1. Select your repository from the list
2. Click "Load City"
3. Press the **Play** button to start the flythrough
4. Enjoy the show! 🎬

---

## Usage Examples

### Example 1: Visualizing a Local Repository

```bash
# Navigate to your project directory
cd ~/projects/my-awesome-app

# Ingest the repository
time-machine ingest . --name my-awesome-app

# List ingested repositories
time-machine list

# Start the server (if not already running)
time-machine serve
```

Then open `http://localhost:5173` and select "my-awesome-app".

### Example 2: Visualizing a GitHub Repository

```bash
# Ingest a popular open-source project
time-machine ingest https://github.com/facebook/react.git

# This will clone the repository and process it
# May take a few minutes for large repositories
```

### Example 3: Preparing for an Offline Demo

```bash
# Pre-generate all narration for a repository
time-machine prepare-demo my-awesome-app

# This will:
# 1. Analyze the repository history
# 2. Identify significant epochs
# 3. Generate narration for each epoch
# 4. Cache everything to disk

# Start in offline mode
ENABLE_OFFLINE_MODE=True time-machine serve
```

### Example 4: Interactive Exploration

While viewing a visualization:

1. **Pause playback**: Press `Space` or click the Pause button
2. **Click a building**: View detailed file history
3. **Scrub timeline**: Drag the timeline slider to any point
4. **Zoom**: Use mouse wheel or pinch gesture
5. **Rotate**: Click and drag to orbit camera
6. **Pan**: Right-click and drag to pan view
7. **Resume**: Press `Space` or click Play

### Example 5: Adjusting Playback Speed

```javascript
// In the web UI, use the speed controls:
// - 0.5x: Slow motion (detailed viewing)
// - 1.0x: Normal speed (default)
// - 1.5x: Faster (quick overview)
// - 2.0x: Double speed (rapid review)
```

### Example 6: Exporting City Data

```bash
# Generate city data and save to JSON
python -c "
from time_machine.ingestion import RepositoryIngester
from time_machine.city import CityGenerator

# Ingest repository
ingester = RepositoryIngester()
result = ingester.ingest('/path/to/repo')

# Generate city
generator = CityGenerator()
city_state = generator.generate_city(commits, neighborhoods)

# Save to file
generator.save_city_state(city_state, 'city_data.json')
"
```

---

## Configuration Options

### Environment Variables

All configuration is done through environment variables in the `.env` file:

#### IBM Watson/Bob Configuration
```bash
# Required for narration generation
IBM_WATSON_API_KEY=your_api_key
IBM_WATSON_URL=https://api.us-south.assistant.watson.cloud.ibm.com
IBM_WATSON_ASSISTANT_ID=your_assistant_id
```

#### Repository Limits
```bash
# Maximum number of commits to process
MAX_COMMITS=10000

# Maximum number of files to visualize
MAX_FILES=5000

# Skip binary files
SKIP_BINARY_FILES=True
```

#### Playback Settings
```bash
# Default playback duration in seconds
DEFAULT_PLAYBACK_DURATION=90

# Default playback speed multiplier
DEFAULT_PLAYBACK_SPEED=1.0

# Enable auto-camera (cinematic mode)
ENABLE_AUTO_CAMERA=True
```

#### Rendering Settings
```bash
# Window resolution
WINDOW_WIDTH=1920
WINDOW_HEIGHT=1080

# Enable anti-aliasing
ENABLE_ANTIALIASING=True

# Enable shadows
ENABLE_SHADOWS=False

# Field of view (degrees)
CAMERA_FOV=60
```

#### Logging
```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file path
LOG_FILE=time_machine.log

# Enable console logging
LOG_TO_CONSOLE=True
```

#### Demo Mode
```bash
# Enable offline mode (use cached narrations)
ENABLE_OFFLINE_MODE=False

# Narration cache directory
NARRATION_CACHE_DIR=data/narration

# Enable graceful degradation
GRACEFUL_DEGRADATION=True
```

#### Flask Server
```bash
# Server host
FLASK_HOST=0.0.0.0

# Server port
FLASK_PORT=5000

# Debug mode
FLASK_DEBUG=False

# Enable CORS
ENABLE_CORS=True
```

### Layout Configuration

You can customize the city layout by modifying `LayoutConfig`:

```python
from time_machine.city import CityGenerator, LayoutConfig

# Create custom layout configuration
layout_config = LayoutConfig(
    grid_size=15.0,              # Size of grid cells
    building_spacing=3.0,         # Space between buildings
    neighborhood_spacing=8.0,     # Space between neighborhoods
    max_building_height=100.0,    # Maximum building height
    min_building_height=0.5,      # Minimum building height
    base_building_size=(2.0, 2.0), # Default building base size
    layout_algorithm='grid'       # Layout algorithm to use
)

# Use custom configuration
generator = CityGenerator(layout_config=layout_config)
```

### Visual Encoding Configuration

Customize how file properties are encoded visually:

```python
from time_machine.rendering import VisualEncoding

# Create custom visual encoding
encoding = VisualEncoding(
    min_height=1.0,
    max_height=50.0,
    height_scale=5.0,
    cold_color=(0.2, 0.4, 0.8),  # Blue for low activity
    hot_color=(0.9, 0.2, 0.1),   # Red for high activity
    fresh_brightness=1.0,
    aged_brightness=0.5
)
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: "ModuleNotFoundError: No module named 'time_machine'"

**Solution**:
```bash
# Reinstall in development mode
pip install -e .

# Verify installation
python -c "import time_machine; print(time_machine.__version__)"
```

#### Issue: "Invalid git repository"

**Solution**:
- Ensure the path points to a valid git repository
- Check that the directory contains a `.git` folder
- Try cloning the repository first if using a URL

```bash
# Verify it's a git repository
cd /path/to/repo
git status

# If not, initialize it
git init
```

#### Issue: "Watson API authentication failed"

**Solution**:
1. Verify credentials in `.env` file
2. Check API key is valid and not expired
3. Ensure Watson service is active
4. Test with offline mode:
```bash
ENABLE_OFFLINE_MODE=True time-machine serve
```

#### Issue: "ModernGL context creation failed"

**Solution**:
- Update graphics drivers
- Check OpenGL version: `glxinfo | grep "OpenGL version"` (Linux)
- Try software rendering:
```bash
LIBGL_ALWAYS_SOFTWARE=1 time-machine serve
```

#### Issue: "Port 5000 already in use"

**Solution**:
```bash
# Use a different port
time-machine serve --port 5001

# Or kill the process using port 5000
lsof -ti:5000 | xargs kill -9  # macOS/Linux
```

#### Issue: "Repository too large"

**Solution**:
```bash
# Increase limits in .env
MAX_COMMITS=20000
MAX_FILES=10000

# Or use a smaller repository for testing
```

#### Issue: "Narration generation is slow"

**Solution**:
- Pre-generate narrations for demos:
```bash
time-machine prepare-demo my-repo
```
- Use offline mode to skip API calls
- Reduce number of epochs by adjusting significance threshold

#### Issue: "Frontend not connecting to backend"

**Solution**:
1. Check backend is running: `curl http://localhost:5000/api/health`
2. Check CORS is enabled in `.env`: `ENABLE_CORS=True`
3. Verify ports match in frontend config
4. Check firewall settings

#### Issue: "Buildings not rendering"

**Solution**:
- Check browser console for WebGL errors
- Verify GPU supports WebGL 2.0
- Try a different browser (Chrome/Firefox recommended)
- Check if city data loaded: Open browser DevTools → Network tab

#### Issue: "Memory error during ingestion"

**Solution**:
```bash
# Process in smaller batches
MAX_COMMITS=5000

# Increase Python memory limit
ulimit -v 8000000  # 8GB limit
```

---

## FAQ

### General Questions

**Q: What types of repositories work best?**

A: Repositories with 1,000-5,000 commits and 500-2,000 files provide the best experience. Very small repos may lack interesting patterns, while very large repos may be slow to process.

**Q: Can I visualize private repositories?**

A: Yes! The Time Machine works with any git repository you have access to, including private repos. Just provide the local path or use SSH URLs with proper authentication.

**Q: Does it work with all programming languages?**

A: Yes! The Time Machine is language-agnostic. It visualizes repository structure and history regardless of the programming language used.

**Q: How long does ingestion take?**

A: Depends on repository size:
- Small repos (< 1,000 commits): 10-30 seconds
- Medium repos (1,000-5,000 commits): 1-3 minutes
- Large repos (5,000-10,000 commits): 3-10 minutes

**Q: Can I export the visualization?**

A: Currently, you can take screenshots. Video export is planned for a future release.

### Technical Questions

**Q: What is the playback duration?**

A: Default is 90 seconds for the entire repository history. This can be adjusted in configuration.

**Q: How does the AI narration work?**

A: The system analyzes commit history to identify significant periods (epochs), then uses IBM Watson/Bob to generate coherent narration explaining what happened during each epoch.

**Q: Can I use it without IBM Watson?**

A: Yes! Enable offline mode or skip narration generation. The visualization works independently of narration.

**Q: What does each visual element mean?**

A:
- **Building height**: Lines of code (logarithmic scale)
- **Building color**: Modification frequency (blue = low, red = high)
- **Building brightness**: Recency (bright = recent, dark = old)
- **Neighborhood**: Directory structure

**Q: Can I customize the visual encoding?**

A: Yes! See the [Configuration Options](#configuration-options) section for details on customizing visual encoding.

**Q: Is there a limit to repository size?**

A: Configurable limits: 10,000 commits and 5,000 files by default. You can increase these, but performance may degrade.

### Usage Questions

**Q: How do I pause and inspect a building?**

A:
1. Press `Space` or click Pause
2. Click on any building
3. View file details in the sidebar
4. Press `Space` or click Play to resume

**Q: Can I jump to a specific date?**

A: Yes! Use the timeline scrubber at the bottom to jump to any point in history.

**Q: How do I control the camera?**

A:
- **Orbit**: Left-click and drag
- **Pan**: Right-click and drag
- **Zoom**: Mouse wheel or pinch
- **Reset**: Press `R` or click Reset Camera

**Q: What's the difference between auto-camera and manual control?**

A: Auto-camera follows areas of high activity cinematically. Manual control lets you explore freely. Toggle with the camera icon button.

**Q: Can I share my visualization?**

A: You can share screenshots or the repository data JSON. Full sharing features are planned for future releases.

---

## API Reference

### Command-Line Interface

#### `time-machine ingest`
Ingest a git repository for visualization.

```bash
time-machine ingest <repository> [--name NAME]
```

**Arguments**:
- `repository`: Path to local repository or remote URL (required)
- `--name`: Custom name for the repository (optional)

**Examples**:
```bash
time-machine ingest /path/to/repo
time-machine ingest https://github.com/user/repo.git
time-machine ingest . --name my-project
```

#### `time-machine list`
List all ingested repositories.

```bash
time-machine list
```

**Output**:
```
Found 3 repositories:
  - my-project (1,234 commits, 567 files)
  - react (12,345 commits, 2,345 files)
  - vue (8,901 commits, 1,234 files)
```

#### `time-machine prepare-demo`
Pre-generate all narration for offline demo mode.

```bash
time-machine prepare-demo <repository>
```

**Arguments**:
- `repository`: Repository name or path (required)

**Example**:
```bash
time-machine prepare-demo my-project
```

#### `time-machine serve`
Start the web server.

```bash
time-machine serve [--port PORT] [--debug]
```

**Arguments**:
- `--port`: Port to run server on (default: 5000)
- `--debug`: Run in debug mode (default: false)

**Examples**:
```bash
time-machine serve
time-machine serve --port 8080
time-machine serve --debug
```

### REST API Endpoints

#### `GET /api/repositories`
List all ingested repositories.

**Response**:
```json
{
  "repositories": [
    {
      "name": "my-project",
      "path": "/data/repositories/my-project",
      "commit_count": 1234,
      "file_count": 567
    }
  ]
}
```

#### `POST /api/repositories/ingest`
Ingest a new repository.

**Request**:
```json
{
  "repository": "/path/to/repo",
  "name": "my-project"
}
```

**Response**:
```json
{
  "success": true,
  "name": "my-project",
  "commit_count": 1234,
  "file_count": 567
}
```

#### `GET /api/city/:repo_name`
Get city data for a repository.

**Response**:
```json
{
  "commit_sha": "abc123...",
  "timestamp": "2026-05-16T10:30:00Z",
  "buildings": { ... },
  "neighborhoods": { ... },
  "statistics": { ... }
}
```

#### `GET /api/narration/:repo_name`
Get narration data for a repository.

**Response**:
```json
{
  "epochs": [
    {
      "start_time": "2020-01-01T00:00:00Z",
      "end_time": "2020-03-01T00:00:00Z",
      "narration": "In the beginning...",
      "highlights": ["Initial commit", "Core features"]
    }
  ]
}
```

#### `GET /api/timeline/:repo_name`
Get timeline data for a repository.

**Response**:
```json
{
  "total_duration": 90.0,
  "commits": [
    {
      "sha": "abc123...",
      "timestamp": "2020-01-01T00:00:00Z",
      "playback_time": 0.0
    }
  ]
}
```

#### `GET /api/building/:repo_name/:file_path`
Get detailed information about a specific building/file.

**Response**:
```json
{
  "file_path": "src/app.js",
  "created_at": "abc123...",
  "last_modified": "def456...",
  "modification_count": 42,
  "lines_of_code": 350,
  "history": [ ... ]
}
```

### Python API

#### RepositoryIngester

```python
from time_machine.ingestion import RepositoryIngester

ingester = RepositoryIngester()
result = ingester.ingest('/path/to/repo', name='my-project')
```

#### CityGenerator

```python
from time_machine.city import CityGenerator

generator = CityGenerator()
city_state = generator.generate_city(commits, neighborhoods)
```

#### CityRenderer

```python
from time_machine.rendering import CityRenderer

renderer = CityRenderer(width=1920, height=1080)
renderer.initialize_context()
renderer.load_city_state(city_state)
renderer.render()
```

#### NarrationSync

```python
from time_machine.narration import NarrationSync

sync = NarrationSync(timeline_controller, playback_controller)
sync.add_narrations(epoch_narrations)
sync.update()
```

---

## Getting Help

### Support Channels
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check this guide and ARCHITECTURE.md
- **Examples**: See the `examples/` directory
- **Community**: Join our Discord/Slack (links in README)

### Reporting Bugs
When reporting bugs, please include:
1. Operating system and version
2. Python and Node.js versions
3. Full error message and stack trace
4. Steps to reproduce
5. Repository size (commits/files)
6. Configuration settings (sanitized)

### Contributing
We welcome contributions! See CONTRIBUTING.md for guidelines.

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-16  
**Maintained By**: IBM Bob Hackathon Team

**Happy Visualizing! 🏙️⏰**