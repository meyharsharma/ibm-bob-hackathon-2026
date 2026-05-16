# Demo Repository Selection Guide

## Table of Contents
1. [Selection Criteria](#selection-criteria)
2. [Recommended Repositories](#recommended-repositories)
3. [Repository Preparation](#repository-preparation)
4. [Pre-Indexing Instructions](#pre-indexing-instructions)
5. [Narration Pre-Generation](#narration-pre-generation)
6. [Validation Checklist](#validation-checklist)

---

## Selection Criteria

### Essential Criteria

A good demo repository must meet these requirements:

#### 1. Size and Complexity
- **Commits**: 500-5,000 commits (sweet spot: 1,000-2,000)
- **Files**: 100-2,000 files (sweet spot: 300-800)
- **Duration**: Repository should span 6+ months of development
- **Rationale**: Large enough to show patterns, small enough to process quickly

#### 2. Activity Patterns
- **Consistent activity**: Regular commits over time (not sporadic)
- **Clear epochs**: Identifiable phases (initial development, feature additions, refactoring)
- **Variety**: Mix of file additions, modifications, and deletions
- **Hotspots**: Some files with high modification frequency
- **Rationale**: Makes visual patterns obvious and narration interesting

#### 3. Structure
- **Clear organization**: Well-organized directory structure
- **Multiple modules**: At least 3-5 distinct neighborhoods/modules
- **Logical grouping**: Related files grouped together
- **Rationale**: Shows neighborhood clustering effectively

#### 4. History Quality
- **Meaningful commits**: Descriptive commit messages
- **Atomic commits**: Each commit represents a logical change
- **No garbage**: Minimal auto-generated commits or noise
- **Rationale**: Enables better AI narration generation

#### 5. Technical Characteristics
- **Popular language**: JavaScript, Python, Java, Go, or TypeScript
- **Active project**: Still maintained (shows growth)
- **Open source**: Publicly accessible for demos
- **Well-known**: Recognizable name helps audience engagement
- **Rationale**: Audience familiarity and relatability

### Nice-to-Have Criteria

These enhance the demo but aren't required:

- **Interesting story**: Major refactorings, pivots, or milestones
- **Multiple contributors**: Shows collaboration patterns
- **Documentation**: README and docs help explain context
- **Tests**: Test files create interesting visual patterns
- **Build files**: Configuration files add to city complexity

### Criteria to Avoid

Repositories with these characteristics make poor demos:

- ❌ **Too small**: < 100 commits or < 50 files (not interesting)
- ❌ **Too large**: > 10,000 commits or > 5,000 files (slow to process)
- ❌ **Monorepo**: Multiple projects in one repo (confusing visualization)
- ❌ **Generated code**: Lots of auto-generated files (skews metrics)
- ❌ **Binary heavy**: Many binary files (limited visualization value)
- ❌ **Inactive**: No commits in last year (stale story)
- ❌ **Messy history**: Squashed commits, rebases, or force pushes
- ❌ **Private/sensitive**: Contains proprietary or sensitive information

---

## Recommended Repositories

### Tier 1: Excellent Demo Repositories

These repositories are ideal for demos and have been tested:

#### 1. Express.js (Node.js Web Framework)
```bash
Repository: https://github.com/expressjs/express.git
Language: JavaScript
Size: ~2,000 commits, ~200 files
Duration: 10+ years
```

**Why it's great**:
- ✅ Well-known framework (audience recognition)
- ✅ Clear structure (lib, test, examples)
- ✅ Consistent activity over many years
- ✅ Interesting evolution story
- ✅ Perfect size for visualization

**Story highlights**:
- Initial minimalist design
- Gradual feature additions
- Major version transitions
- Refactoring for performance
- Community contributions

**Preparation time**: 2-3 minutes

---

#### 2. Flask (Python Web Framework)
```bash
Repository: https://github.com/pallets/flask.git
Language: Python
Size: ~3,000 commits, ~300 files
Duration: 12+ years
```

**Why it's great**:
- ✅ Popular Python framework
- ✅ Clean, organized structure
- ✅ Rich history with clear phases
- ✅ Good mix of code and tests
- ✅ Excellent commit messages

**Story highlights**:
- Microframework origins
- Extension ecosystem growth
- Python 3 migration
- Type hints addition
- Documentation improvements

**Preparation time**: 3-4 minutes

---

#### 3. Vue.js (JavaScript Framework)
```bash
Repository: https://github.com/vuejs/vue.git
Language: JavaScript/TypeScript
Size: ~3,500 commits, ~400 files
Duration: 8+ years
```

**Why it's great**:
- ✅ Extremely popular framework
- ✅ Clear architectural evolution
- ✅ TypeScript migration visible
- ✅ Active development
- ✅ Great visual patterns

**Story highlights**:
- Rapid initial development
- Component system evolution
- TypeScript adoption
- Performance optimizations
- Vue 3 rewrite

**Preparation time**: 4-5 minutes

---

#### 4. Lodash (JavaScript Utility Library)
```bash
Repository: https://github.com/lodash/lodash.git
Language: JavaScript
Size: ~4,000 commits, ~500 files
Duration: 10+ years
```

**Why it's great**:
- ✅ Well-known utility library
- ✅ Modular structure (many small files)
- ✅ Consistent patterns
- ✅ Good for showing file organization
- ✅ Interesting refactoring history

**Story highlights**:
- Underscore.js fork origins
- Modularization efforts
- Performance improvements
- ES6 adoption
- Tree-shaking support

**Preparation time**: 4-5 minutes

---

#### 5. Requests (Python HTTP Library)
```bash
Repository: https://github.com/psf/requests.git
Language: Python
Size: ~2,500 commits, ~150 files
Duration: 12+ years
```

**Why it's great**:
- ✅ Iconic Python library
- ✅ Simple, focused codebase
- ✅ Clear evolution
- ✅ Excellent for showing simplicity
- ✅ Good commit history

**Story highlights**:
- "HTTP for Humans" philosophy
- API refinement over time
- Security improvements
- Python 3 support
- Maintenance mode transition

**Preparation time**: 2-3 minutes

---

### Tier 2: Good Demo Repositories

These work well but may require more preparation:

#### 6. Axios (JavaScript HTTP Client)
```bash
Repository: https://github.com/axios/axios.git
Size: ~1,500 commits, ~100 files
```
- Good for showing focused libraries
- Clear structure
- Smaller but still interesting

#### 7. Django (Python Web Framework)
```bash
Repository: https://github.com/django/django.git
Size: ~30,000 commits, ~3,000 files
```
- ⚠️ Large - may need filtering
- Rich history
- Complex structure
- Requires more processing time

#### 8. React (JavaScript Library)
```bash
Repository: https://github.com/facebook/react.git
Size: ~15,000 commits, ~1,000 files
```
- ⚠️ Large - may need filtering
- Very popular
- Interesting architecture changes
- Longer processing time

#### 9. FastAPI (Python Web Framework)
```bash
Repository: https://github.com/tiangolo/fastapi.git
Size: ~2,000 commits, ~200 files
```
- Modern framework
- Rapid growth story
- Good structure
- Active development

#### 10. Gin (Go Web Framework)
```bash
Repository: https://github.com/gin-gonic/gin.git
Size: ~1,000 commits, ~150 files
```
- Good for Go audience
- Clean structure
- Focused scope
- Fast processing

---

### Tier 3: Specialized Demo Repositories

Use these for specific audiences or purposes:

#### For Educational Demos
- **Learn Python**: Small tutorial repos with clear progression
- **30 Days of Code**: Shows learning journey
- **Algorithm implementations**: Clear structure, many small files

#### For Enterprise Audiences
- **Kubernetes**: Large-scale system (requires filtering)
- **Terraform**: Infrastructure as code
- **Jenkins**: CI/CD evolution

#### For Open Source Advocates
- **Linux kernel**: Massive scale (demo filtering capabilities)
- **Git itself**: Meta demonstration
- **VS Code**: Popular editor with rich history

---

## Repository Preparation

### Step 1: Clone and Verify

```bash
# Clone the repository
git clone https://github.com/user/repo.git demo-repo
cd demo-repo

# Verify it's a valid git repository
git status

# Check repository size
git rev-list --count HEAD  # Count commits
find . -type f | wc -l     # Count files

# Check date range
git log --reverse --format="%ai" | head -1  # First commit
git log --format="%ai" | head -1            # Last commit
```

### Step 2: Clean Up (if needed)

```bash
# Remove large binary files (optional)
git filter-branch --tree-filter 'rm -rf path/to/binaries' HEAD

# Remove sensitive data (if any)
git filter-branch --tree-filter 'rm -f sensitive-file.txt' HEAD

# Compact repository
git gc --aggressive --prune=now
```

### Step 3: Analyze Structure

```bash
# List top-level directories
ls -la

# Count files by type
find . -type f -name "*.js" | wc -l
find . -type f -name "*.py" | wc -l
find . -type f -name "*.go" | wc -l

# Check for interesting patterns
git log --all --format='%aN' | sort -u  # Contributors
git log --oneline | head -20             # Recent commits
```

### Step 4: Test Ingestion

```bash
# Ingest the repository
time-machine ingest ./demo-repo --name demo-test

# Verify ingestion
time-machine list

# Check for errors in logs
tail -f time_machine.log
```

---

## Pre-Indexing Instructions

### Full Pre-Indexing Process

This ensures the demo runs smoothly without delays:

```bash
# 1. Ingest repository
time-machine ingest https://github.com/user/repo.git --name demo-repo

# 2. Verify ingestion completed
time-machine list

# 3. Generate city data (happens automatically during ingestion)
# City data is stored in: data/repositories/demo-repo/

# 4. Pre-generate narration (see next section)
time-machine prepare-demo demo-repo

# 5. Verify all data is ready
ls -la data/repositories/demo-repo/
ls -la data/narration/demo-repo/

# 6. Test loading in UI
# Start services and load repository in browser
```

### Timing Estimates

| Repository Size | Ingestion Time | Narration Generation | Total Time |
|----------------|----------------|---------------------|------------|
| Small (< 500 commits) | 30-60 sec | 1-2 min | 2-3 min |
| Medium (500-2000 commits) | 1-3 min | 3-5 min | 5-8 min |
| Large (2000-5000 commits) | 3-8 min | 5-10 min | 10-18 min |
| Very Large (> 5000 commits) | 8-15 min | 10-20 min | 20-35 min |

### Optimization Tips

```bash
# Limit commits for faster processing
MAX_COMMITS=2000 time-machine ingest repo-url

# Limit files
MAX_FILES=1000 time-machine ingest repo-url

# Skip binary files
SKIP_BINARY_FILES=True time-machine ingest repo-url

# Use multiple cores (if supported)
PARALLEL_PROCESSING=True time-machine ingest repo-url
```

---

## Narration Pre-Generation

### Why Pre-Generate Narration?

1. **Reliability**: No dependency on network during demo
2. **Speed**: Instant narration playback
3. **Consistency**: Same narration every time
4. **Quality control**: Review and edit before demo
5. **Offline capability**: Works without internet

### Pre-Generation Process

```bash
# Basic pre-generation
time-machine prepare-demo demo-repo

# With custom settings
EPOCH_COUNT=10 time-machine prepare-demo demo-repo

# Verbose output
LOG_LEVEL=DEBUG time-machine prepare-demo demo-repo
```

### What Gets Generated

The `prepare-demo` command creates:

1. **Epoch identification**: Significant time periods
2. **Epoch narration**: AI-generated text for each epoch
3. **Building explanations**: Descriptions for key files
4. **Timeline mapping**: Narration timing data
5. **Cache files**: All stored in `data/narration/demo-repo/`

### Narration Quality Check

After generation, review the narration:

```bash
# View generated narration
cat data/narration/demo-repo/epochs.json | jq '.[] | .narration'

# Check for issues:
# - Grammatical errors
# - Factual inaccuracies
# - Awkward phrasing
# - Missing context
```

### Manual Narration Editing

If needed, you can edit the generated narration:

```bash
# 1. Open narration file
nano data/narration/demo-repo/epochs.json

# 2. Edit the "narration" field for each epoch
# Keep the structure intact, only modify text

# 3. Save and test
time-machine serve
# Load repository and verify narration
```

### Narration Best Practices

**Good narration**:
- ✅ Explains what happened and why
- ✅ Mentions key contributors or features
- ✅ Uses clear, concise language
- ✅ Flows naturally from epoch to epoch
- ✅ Provides context for changes

**Poor narration**:
- ❌ Just lists commit messages
- ❌ Too technical or jargon-heavy
- ❌ Lacks context or explanation
- ❌ Repetitive or boring
- ❌ Factually incorrect

### Example Good Narration

```json
{
  "epoch": 1,
  "narration": "In the beginning, the project started with a simple foundation. The core architecture was established, including basic routing and data models. The team focused on getting the fundamentals right before adding features.",
  "highlights": ["Initial commit", "Core architecture", "Basic routing"]
}
```

### Example Poor Narration

```json
{
  "epoch": 1,
  "narration": "Files were added. Code was written. Commits were made.",
  "highlights": []
}
```

---

## Validation Checklist

### Pre-Demo Validation

Complete this checklist 24 hours before your demo:

#### Repository Validation
- [ ] Repository ingested successfully
- [ ] Commit count within acceptable range (500-5,000)
- [ ] File count within acceptable range (100-2,000)
- [ ] No errors in ingestion logs
- [ ] City data generated correctly

#### Narration Validation
- [ ] All epochs have narration
- [ ] Narration is grammatically correct
- [ ] Narration is factually accurate
- [ ] Narration flows naturally
- [ ] No placeholder text or errors

#### Visual Validation
- [ ] City loads in browser
- [ ] All buildings render correctly
- [ ] Neighborhoods are clearly defined
- [ ] Colors and heights look reasonable
- [ ] No visual glitches or artifacts

#### Playback Validation
- [ ] Play button works
- [ ] Animation runs smoothly (60 FPS)
- [ ] Narration syncs with visuals
- [ ] Timeline scrubbing works
- [ ] Pause/resume works correctly

#### Interaction Validation
- [ ] Can click buildings
- [ ] Building details display correctly
- [ ] Camera controls work (orbit, zoom, pan)
- [ ] Speed adjustment works
- [ ] All UI elements functional

#### Offline Mode Validation
- [ ] Offline mode enabled
- [ ] Disconnect from internet
- [ ] Demo still works completely
- [ ] Narration plays from cache
- [ ] No network errors
- [ ] Reconnect to internet

#### Performance Validation
- [ ] Loads in < 5 seconds
- [ ] Runs at 60 FPS
- [ ] No memory leaks
- [ ] CPU usage reasonable
- [ ] No crashes or freezes

#### Backup Validation
- [ ] Backup repository prepared
- [ ] Backup video recorded
- [ ] Screenshots captured
- [ ] Slides prepared
- [ ] All backups tested

---

## Repository-Specific Notes

### Express.js
```bash
# Recommended settings
MAX_COMMITS=2000
EPOCH_COUNT=8

# Interesting epochs to highlight:
# - Initial release (2009)
# - 3.x series (major refactor)
# - 4.x series (middleware improvements)
# - 5.x series (modern features)
```

### Flask
```bash
# Recommended settings
MAX_COMMITS=3000
EPOCH_COUNT=10

# Interesting epochs to highlight:
# - Initial release (2010)
# - Blueprint system
# - Python 3 migration
# - Type hints addition
# - Modern async support
```

### Vue.js
```bash
# Recommended settings
MAX_COMMITS=3500
EPOCH_COUNT=12

# Interesting epochs to highlight:
# - Initial release (2014)
# - Component system
# - Vue 2.0 rewrite
# - TypeScript adoption
# - Vue 3.0 composition API
```

---

## Troubleshooting

### Issue: Narration Generation Fails

**Symptoms**: `prepare-demo` command errors or produces empty narration

**Solutions**:
1. Check Watson API credentials in `.env`
2. Verify API quota not exceeded
3. Try with smaller epoch count
4. Check logs for specific errors
5. Fall back to manual narration

### Issue: Repository Too Large

**Symptoms**: Ingestion takes > 15 minutes or runs out of memory

**Solutions**:
1. Reduce MAX_COMMITS limit
2. Reduce MAX_FILES limit
3. Filter to specific branches
4. Use a smaller repository
5. Increase system resources

### Issue: Poor Visual Results

**Symptoms**: City looks messy or uninteresting

**Solutions**:
1. Try different repository
2. Adjust layout configuration
3. Filter out generated files
4. Customize visual encoding
5. Focus on specific modules

### Issue: Boring Narration

**Symptoms**: Generated narration is generic or uninteresting

**Solutions**:
1. Choose repository with better commit messages
2. Manually edit narration
3. Adjust epoch identification parameters
4. Provide more context in prompts
5. Use repository with clearer story

---

## Quick Reference

### Best Repositories by Use Case

| Use Case | Repository | Why |
|----------|-----------|-----|
| General demo | Express.js | Perfect size, well-known |
| Python audience | Flask | Popular, clean history |
| JavaScript audience | Vue.js | Modern, active development |
| Enterprise audience | Django | Large-scale, mature |
| Educational | Requests | Simple, focused |
| Performance demo | Lodash | Many small files |

### Command Quick Reference

```bash
# Ingest repository
time-machine ingest <url> --name <name>

# Pre-generate narration
time-machine prepare-demo <name>

# List repositories
time-machine list

# Start demo
ENABLE_OFFLINE_MODE=True time-machine serve
```

---

## Final Recommendations

### For Your First Demo
**Use**: Express.js or Flask
**Why**: Perfect size, well-known, reliable narration

### For Technical Audiences
**Use**: Vue.js or React
**Why**: Modern frameworks, interesting evolution

### For Quick Demos
**Use**: Requests or Axios
**Why**: Small, fast to process, clear story

### For Impressive Demos
**Use**: Vue.js or Django
**Why**: Rich history, complex patterns, engaging story

---

**Remember**: The best demo repository is one that:
1. Processes quickly
2. Looks interesting visually
3. Has a compelling story
4. Works reliably offline
5. Resonates with your audience

**Good luck with your demo! 🎬**

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-16  
**Maintained By**: IBM Bob Hackathon Team