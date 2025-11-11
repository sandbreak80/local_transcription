# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2024-11-11

### Added - AI Speaker Detection 🎤

#### Speaker Detection Features
- **🎤 Local Voice-Based Speaker Detection**: AI-powered speaker identification using audio feature clustering
  - No cloud services required - 100% offline
  - No HuggingFace account needed
  - Uses MFCC and spectral features for voice analysis
  - Automatic clustering of speakers by voice characteristics
  - Fallback to librosa-based audio analysis if needed
- **👥 Custom Speaker Names**: Automatically assign human-readable names to speakers
  - Simple comma-separated input: `"Alice,Bob,Charlie"`
  - Intelligent mapping to detected speakers
  - Auto-feedback for extra/missing names
- **🎯 Configurable Speaker Count**: Optionally specify expected number of speakers
- **📝 Speaker Labels in Transcripts**: Each line shows who said what
  - Format: `[timestamp] Speaker_Name: text`
  - Works in both CLI and Web UI
- **🌐 Web UI Integration**: Full speaker detection controls in web interface
  - Checkbox to enable/disable
  - Input for number of speakers
  - Text field for custom names

#### New Files
- `local_speaker_detection.py` - Local voice-based speaker detection module
- `SPEAKER_MODEL_SETUP.md` - Documentation for embedded speaker model

#### Updated Files
- `app.py` - Added speaker detection options to web API
- `transcribe.py` - Integrated LocalSpeakerDetector
- `templates/index.html` - Added speaker detection UI controls
- `static/js/app.js` - Frontend support for speaker options
- `requirements.txt` - Added librosa, scikit-learn, scipy for audio analysis
- `Dockerfile` - Embedded speaker recognition model (no downloads needed)
- `README.md` - Updated with speaker detection features

### Fixed
- **CLI Flag Mismatch**: Changed `--two-list-quotes` to `--two-lists` in web backend
- **Speaker Name Mapping Bug**: Fixed parameter type mismatch causing crash
- **UUID in Filenames**: Cleaned up UUID prefixes in output file content
- **Download Links Persistence**: Added `/scan-outputs` endpoint to restore links after container restart
- **File Display in UI**: Added dedicated file list display area
- **Port Configuration**: Changed default port from 5000 to 5731

### Changed
- **Port Number**: Web interface now runs on port 5731 (was 5000)
- **Speaker Detection**: Switched from `pyannote.audio` to local clustering method
- **Embedded Model**: Speaker recognition model now embedded in Docker image (~87MB)

### Technical Details
- Audio feature extraction using MFCCs and spectral analysis
- AgglomerativeClustering for speaker grouping
- Cosine similarity for speaker embeddings
- Fallback mechanism if speechbrain unavailable
- Smart name mapping with feedback
- Zero external dependencies for speaker detection

## [1.1.0] - 2024-11-10

### Added - Web Interface 🌐
This is a major feature release adding a complete web-based user interface!

#### Web Interface Features
- **🌐 Browser-Based UI**: Modern, beautiful web interface for non-technical users
- **🖱️ Drag & Drop Upload**: Easy file selection with drag-and-drop support
- **📊 Real-Time Progress**: Live progress bars showing transcription status
- **🎯 Visual Options**: Point-and-click selection for models, languages, and features
- **📥 Auto Downloads**: Instant download of completed transcriptions
- **🔄 Multiple Files**: Queue-based processing of multiple files simultaneously
- **📱 Responsive Design**: Works on desktop, tablet, and mobile devices
- **🎨 Modern UI**: Gradient backgrounds, smooth animations, clean design

#### New Files
- `app.py` - Flask web application with job queue and processing
- `templates/index.html` - Beautiful HTML interface
- `static/css/style.css` - Modern, responsive CSS styling
- `static/js/app.js` - Dynamic frontend with real-time updates
- `transcribe-web.sh` - Web launcher for Mac/Linux
- `transcribe-web.bat` - Web launcher for Windows
- `WEB_INTERFACE.md` - Complete web interface documentation

#### Updated Files
- `Dockerfile` - Added web interface support, exposed port 5000
- `docker-compose.yml` - Added `web` service for browser access
- `requirements.txt` - Added Flask and Werkzeug dependencies
- `README.md` - Added web interface section and quick start
- `.dockerignore` - Added web-related entries

#### Technical Details
- Flask web server on port 5000
- Background worker thread for job processing
- Queue-based job management
- Real-time status polling (2-second intervals)
- Support for files up to 2GB
- Automatic cleanup of processed files
- JSON API endpoints for status and downloads

### Enhanced
- Docker container now supports both CLI and Web modes
- Better documentation structure with web UI guide
- Improved user experience for non-technical users

## [1.0.1] - 2024-11-10

### Changed
- Added author attribution (Brad Stoner, bmstoner@cisco.com)
- Added organization information (Created for Splunk and Cisco)
- Updated documentation with version and author information at top of README
- Enhanced HOW_TO_USE_THE_ZIP.md with production testing section prominently displayed
- Updated VERSION_INFO.txt with complete author and organization details

### Documentation
- Added version, author, and organization info to README.md header
- Enhanced HOW_TO_USE_THE_ZIP.md with prominent testing validation section
- Updated all version references from 1.0.0 to 1.0.1

## [1.0.0] - 2024-11-10

### Added - Docker Release 🐳

#### Core Features
- **Docker Support**: Complete Docker containerization for zero-setup usage
- **Cross-Platform Scripts**: 
  - `transcribe.sh` for Mac/Linux
  - `transcribe.bat` for Windows
  - Auto-builds Docker image on first run
- **Volume Mounting**: Automatic directory mounting for easy file access
- **Output Management**: Transcriptions saved automatically in same directory as input video

#### Transcription Features
- Multiple Whisper model sizes (tiny, base, small, medium, large)
- Animated quote detection with voice inflection analysis
- Two-list quote generation (arbitrary + animated quotes)
- Multi-language support and auto-detection
- Translation to English from any language
- Batch processing with recursive directory support
- Detailed JSON output with timestamps and metadata
- Speaker change detection
- Topic classification for quotes

#### Documentation (8 comprehensive guides)
- `QUICKSTART.md` - 5-minute getting started guide
- `DOCKER.md` - Complete Docker documentation
- `DOCKER_SETUP_SUMMARY.md` - Implementation overview
- `USAGE_EXAMPLES.md` - Real-world usage scenarios
- `SHARING.md` - Distribution strategies and guides
- `TEST_CHECKLIST.md` - Pre-distribution testing guide
- `FILES_OVERVIEW.md` - Complete file documentation
- `CONTRIBUTING.md` - Contribution guidelines
- Updated `README.md` with Docker-first approach

#### Infrastructure
- `Dockerfile` - Optimized multi-stage build
- `docker-compose.yml` - Alternative usage method
- `.dockerignore` - Build optimization
- `.gitignore` - Repository cleanup
- `LICENSE` - MIT License
- `CHANGELOG.md` - This file

### Changed
- **README restructure**: Docker instructions now at the top (recommended method)
- **Python setup**: Moved to "Advanced Users" section (still fully supported)
- **Documentation priority**: Emphasis on Docker-based workflow

### Technical Details
- Base image: Python 3.11-slim
- FFmpeg included in container
- All Python dependencies bundled
- Whisper models downloaded on first use (cached)
- Volume mounting for host file access
- Automatic cleanup after processing

### Performance
- Image size: ~1-2GB (with dependencies)
- First run: ~5 minutes (model download + setup)
- Subsequent runs: Fast (models cached)
- Tiny model: ~2 min for 5-min video
- Base model: ~5 min for 5-min video
- Large model: ~20 min for 5-min video

### Compatibility
- macOS (Intel and Apple Silicon)
- Windows 10/11
- Linux (any distro with Docker support)
- Docker Desktop 4.0+

## [0.9.0] - 2024-10-13 (Pre-Docker)

### Added
- Two-list quote detection system
- Enhanced speaker detection
- Batch processing improvements
- JSON output format

### Changed
- Improved animated quote accuracy
- Better timestamp precision
- Enhanced error handling

## [0.8.0] - 2024-10-09

### Added
- Animated quote detection feature
- Voice inflection analysis
- Topic classification (Cisco AI focused)
- Excitement scoring system

### Changed
- Improved transcription accuracy
- Better segment handling
- Enhanced timestamp formatting

## [0.7.0] - 2024-10-02

### Added
- Initial Python implementation
- Basic transcription functionality
- Multiple Whisper model support
- Multi-language support
- Setup script for dependencies

### Features
- Audio and video format support
- Language auto-detection
- Timestamp generation
- Batch processing
- Recursive directory processing

---

## Version History

- **1.0.0** - Docker Release (Current - Recommended)
- **0.9.0** - Two-list quotes
- **0.8.0** - Animated quotes
- **0.7.0** - Initial release

## Upgrade Guide

### From Pre-Docker Versions (< 1.0.0) to 1.0.0

**Option 1: Switch to Docker (Recommended)**

1. Install Docker Desktop
2. Use the new wrapper scripts:
   ```bash
   ./transcribe.sh video.mp4
   ```
3. All features work the same, but no more dependency management!

**Option 2: Keep using Python**

Continue using Python directly - it still works:
```bash
python transcribe.py video.mp4
```

No changes needed to your existing workflow.

## Future Roadmap

### Planned for v1.1.0
- [ ] GPU acceleration support
- [ ] Additional language models
- [ ] Custom model fine-tuning
- [ ] Web UI for easier usage
- [ ] Subtitle export (SRT, VTT)

### Under Consideration
- [ ] Real-time transcription
- [ ] Audio quality enhancement
- [ ] Multi-speaker identification
- [ ] Integration with video editors
- [ ] API server mode
- [ ] Cloud deployment guides

## Breaking Changes

### 1.0.0
- None - Fully backwards compatible
- Python usage remains unchanged
- New Docker method is optional

## Security Updates

### 1.0.0
- No known security issues
- All processing happens locally
- No data sent to external servers
- Docker isolation provides additional security layer

## Known Issues

### 1.0.0
- First run requires Docker image build (~5 minutes)
- Large models require significant RAM (8GB+ recommended)
- GPU acceleration not yet supported in Docker version
- Windows paths with spaces require quotes

See [GitHub Issues](https://github.com/yourname/local-transcription/issues) for full list.

## Support

- Documentation: Check the docs/ folder
- Issues: Open on GitHub
- Discussions: GitHub Discussions
- Email: your-email@example.com

---

**Note:** Version numbers follow [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for new functionality (backwards compatible)
- PATCH version for backwards compatible bug fixes

