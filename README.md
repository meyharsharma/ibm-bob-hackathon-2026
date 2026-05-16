# The Time Machine 🏙️⏰

A 3D visualization that renders any git repository as a living city and plays its history back as an animated, narrated flythrough. Powered by IBM Watson/Bob for AI-generated narration.

## Overview

The Time Machine transforms git repositories into immersive 3D cities where:
- **Files are buildings** - Each file appears as a distinct 3D structure
- **Directories are neighborhoods** - Related files cluster together spatially
- **History comes alive** - Watch your codebase evolve through time with smooth animations
- **AI tells the story** - IBM Watson/Bob narrates major events and milestones

## Features

- 🏗️ **3D City Generation** - Automatic conversion of repository structure to 3D city
- 🎬 **Time Playback** - Animated flythrough of entire repository history (~90 seconds)
- 🎨 **Visual Encoding** - Building height = complexity, color = age since last modification
- 🎥 **Cinematic Camera** - Auto-camera highlights areas of high activity
- 🤖 **AI Narration** - IBM Watson/Bob generates coherent story from commit history
- 🎮 **Interactive Controls** - Play, pause, scrub, speed adjust, manual camera control
- 🔍 **Building Inspector** - Click any building to see its detailed history
- 📴 **Offline Demo Mode** - Pre-rendered narration for reliable presentations

## Project Structure

```
time-machine/
├── src/
│   └── time_machine/
│       ├── ingestion/       # Git repository parsing
│       ├── city/            # 3D city generation
│       ├── rendering/       # 3D visualization and animation
│       ├── narration/       # IBM Watson/Bob integration
│       ├── api/             # Flask web server
│       └── utils/           # Configuration and utilities
├── frontend/                # React + Three.js UI
├── tests/                   # Test suite
├── data/                    # Repository data and cache
└── docs/                    # Documentation

```

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- Git
- IBM Watson API credentials (for narration)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/time-machine.git
cd time-machine
```

### 2. Set up Python environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### 3. Set up frontend

```bash
# Install Node.js dependencies
npm install
```

### 4. Configure environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your IBM Watson credentials
# IBM_WATSON_API_KEY=your_api_key_here
# IBM_WATSON_URL=your_watson_url
# IBM_WATSON_ASSISTANT_ID=your_assistant_id
```

## Quick Start

### Running the application

```bash
# Terminal 1: Start the backend server
python -m time_machine.api.server

# Terminal 2: Start the frontend development server
npm run dev
```

Then open your browser to `http://localhost:5173`

### Ingesting a repository

```bash
# Ingest a local repository
time-machine ingest /path/to/repository

# Ingest a remote repository
time-machine ingest https://github.com/user/repo.git
```

### Running in demo mode (offline)

```bash
# Pre-generate all narration for a repository
time-machine prepare-demo /path/to/repository

# Start in offline mode
ENABLE_OFFLINE_MODE=True python -m time_machine.api.server
```

## Development

### Running tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=time_machine --cov-report=html

# Run specific test file
pytest tests/unit/test_ingestion.py
```

### Code quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Architecture

### Backend (Python)

- **Ingestion Layer**: Parses git repositories using GitPython/pygit2
- **City Generation**: Converts repository structure to 3D city data model
- **Rendering Engine**: ModernGL-based 3D rendering pipeline
- **Narration Service**: IBM Watson/Bob integration for AI-generated stories
- **API Server**: Flask REST API for frontend communication

### Frontend (React + Three.js)

- **3D Visualization**: Three.js for WebGL rendering
- **UI Controls**: React components for playback controls
- **State Management**: React hooks for application state
- **API Client**: Axios for backend communication

## Configuration

Key configuration options in `.env`:

```bash
# IBM Watson Configuration
IBM_WATSON_API_KEY=your_key
IBM_WATSON_URL=your_url
IBM_WATSON_ASSISTANT_ID=your_id

# Repository Limits
MAX_COMMITS=10000
MAX_FILES=5000

# Playback Settings
DEFAULT_PLAYBACK_DURATION=90  # seconds

# Logging
LOG_LEVEL=INFO
LOG_FILE=time_machine.log

# Demo Mode
ENABLE_OFFLINE_MODE=False
```

## User Flows

### UF1: First-Time Setup
1. Point the tool at a repository (local path or URL)
2. System ingests full history
3. City becomes ready to view

### UF2: The Flythrough
1. Open prepared repository
2. Press play
3. Watch city evolve through history with narration
4. Flythrough completes in ~90 seconds

### UF3: Pause and Inspect
1. Pause during playback
2. Click any building
3. View file history and AI explanation
4. Resume playback

### UF4: Jump to a Moment
1. Scrub timeline to specific date/commit
2. City reflects state at that moment
3. Narration available on demand

### UF5: Demo Mode
1. Pre-index repository with narration
2. Run flythrough without network access
3. Graceful degradation if anything fails

## Supported Repository Sizes

- **Maximum commits**: 10,000 (configurable)
- **Maximum files**: 5,000 (configurable)
- **Recommended**: Projects with 1,000-5,000 commits for best experience

## Troubleshooting

### Import errors
```bash
# Reinstall in development mode
pip install -e .
```

### Missing dependencies
```bash
# Reinstall all dependencies
pip install -r requirements.txt
npm install
```

### Watson API errors
- Verify credentials in `.env`
- Check API quota and limits
- Enable offline mode for testing: `ENABLE_OFFLINE_MODE=True`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- IBM Watson/Bob for AI narration capabilities
- Three.js community for 3D rendering tools
- GitPython and pygit2 for git integration

## Contact

For questions or support, please open an issue on GitHub.

---

Built with ❤️ for the IBM Bob Hackathon 2026