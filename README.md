# Local Media Transcription Tool

A powerful, privacy-focused tool for transcribing audio and video files locally using OpenAI's Whisper model. No data is sent to external servers - everything runs on your machine.

**Author:** Brad Stoner (bmstoner@cisco.com)  
**Created for:** Splunk and Cisco  
**Version:** 1.1.0

---

## 📖 Quick Navigation

**New here?** → [START_HERE.md](START_HERE.md) | **Quick Start** → [QUICKSTART.md](QUICKSTART.md) | **🌐 Web UI** → [WEB_INTERFACE.md](WEB_INTERFACE.md)

**Examples** → [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) | **Docker** → [DOCKER.md](DOCKER.md) | **Share** → [SHARING.md](SHARING.md)

---

> **🚀 New here? Start with [START_HERE.md](START_HERE.md) - Complete guide in one place!**

## ✨ NEW! Web Interface 🌐

**Perfect for non-technical users!** No command line needed!

- 🖱️ **Drag & Drop Interface** - Just drop your files
- 📊 **Real-Time Progress Bars** - See live processing status
- 🎯 **Visual Options** - Select model, language, and features with clicks
- 📥 **Auto Downloads** - Results ready instantly
- 🚀 **Multiple Files** - Process many files with queue management

**Launch Web Interface:**
```bash
./transcribe-web.sh    # Mac/Linux
transcribe-web.bat     # Windows
```

Then open: **http://localhost:5000**

📖 **[Full Web Interface Guide →](WEB_INTERFACE.md)**

---

## Features

- 🎵 **Audio Support**: MP3, WAV, M4A, AAC, FLAC, OGG, WMA
- 🎬 **Video Support**: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
- 🌍 **Multi-language**: Auto-detect or specify language
- 🔄 **Batch Processing**: Transcribe multiple files at once
- 📁 **Recursive**: Process files in subdirectories
- 🎯 **Multiple Models**: Choose from tiny to large Whisper models
- 📝 **Multiple Outputs**: Text files and detailed JSON with timestamps
- 🎭 **Animated Quote Detection**: Find the most exciting quotes with voice inflection analysis
- 📋 **Two-List Quote Detection**: Generate two distinct lists - arbitrary quotes and animated quotes with topic mix
- 🏷️ **Topic Classification**: Automatically categorize content (Cisco AI topics)
- 👥 **Speaker Detection**: Identify speaker changes and assign speaker IDs
- ⏱️ **Precise Timestamps**: Exact 15-second quote segments with timestamps
- 🌐 **Web Interface**: Browser-based UI for non-technical users (NEW!)
- 🐳 **Docker Support**: Run anywhere with zero setup hassles
- 🔒 **Privacy**: Everything runs locally, no data leaves your machine

## Quick Start

### Option 1: Web Interface (Easiest!)

**Perfect for beginners and non-technical users!**

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Run the web interface:

**macOS/Linux:**
```bash
./transcribe-web.sh
```

**Windows:**
```batch
transcribe-web.bat
```

3. Open browser to: **http://localhost:5000**
4. Drag & drop files, select options, and download results!

📖 **[Complete Web Interface Guide →](WEB_INTERFACE.md)**

---

### Option 2: Command Line (Docker)

**For power users and automation!**

**macOS/Linux:**

```bash
# Basic transcription (output saved in same folder as video)
./transcribe.sh /path/to/your/video.mp4

# Use a larger model for better accuracy
./transcribe.sh /path/to/video.mp4 --model large

# Detect animated quotes
./transcribe.sh /path/to/video.mp4 --animated-quotes

# Generate two lists of quotes
./transcribe.sh /path/to/video.mp4 --two-lists

# Specify language
./transcribe.sh /path/to/video.mp4 --language es
```

**Windows:**

```cmd
REM Basic transcription
transcribe.bat C:\path\to\your\video.mp4

REM Use a larger model
transcribe.bat C:\path\to\video.mp4 --model large

REM Detect animated quotes
transcribe.bat C:\path\to\video.mp4 --animated-quotes
```

**First Run:** The script will automatically build the Docker image the first time you run it. This takes a few minutes but only happens once.

**Output:** Transcription files are automatically saved in the same directory as your input video file with the naming pattern:
- `videoname_transcription.txt` - Plain text transcript
- `videoname_transcription.json` - Detailed JSON with timestamps
- `videoname_animated_quotes.txt` - Animated quotes (if using `--animated-quotes`)
- `videoname_two_list_quotes.txt` - Two lists (if using `--two-lists`)

📖 **For more Docker details, see [DOCKER.md](DOCKER.md)**

## Quick Start (Python - Advanced Users)

### 1. Setup

```bash
cd local-transcription
python setup.py
```

This will:
- Install FFmpeg (if needed)
- Install Python dependencies
- Make the script executable

### 2. Basic Usage

```bash
# Transcribe a single file
python transcribe.py audio_file.mp3

# Transcribe with a larger model for better accuracy
python transcribe.py video_file.mp4 --model large

# Specify language
python transcribe.py spanish_audio.mp3 --language es

# Translate to English
python transcribe.py french_audio.mp3 --task translate

# Detect animated quotes (NEW!)
python transcribe.py presentation.mp4 --animated-quotes

# Generate two lists of quotes (NEW!)
python transcribe.py presentation.mp4 --two-lists

# Customize animated quote detection
python transcribe.py video.mp4 --animated-quotes --quote-duration 20 --num-quotes 15
```

### 3. Batch Processing

```bash
# Transcribe all files in a directory
python transcribe.py /path/to/media/folder --batch

# Include subdirectories
python transcribe.py /path/to/media/folder --batch --recursive

# Save outputs to specific directory
python transcribe.py /path/to/media/folder --batch --output-dir /path/to/transcriptions
```

## Model Sizes

Choose the right model for your needs:

| Model  | Size  | Speed | Accuracy | Use Case |
|--------|-------|-------|----------|----------|
| tiny   | 39 MB | Fastest | Good | Quick previews |
| base   | 74 MB | Fast | Better | General use |
| small  | 244 MB | Medium | Good | Balanced |
| medium | 769 MB | Slow | Better | High accuracy |
| large  | 1550 MB | Slowest | Best | Professional use |

## Command Line Options

```
Usage: transcribe.py [OPTIONS] INPUT_PATH

Arguments:
  INPUT_PATH  File or directory to transcribe

Options:
  -m, --model TEXT        Whisper model size [tiny|base|small|medium|large]
  -l, --language TEXT     Language code (e.g., en, es, fr)
  -t, --task TEXT         Task type [transcribe|translate]
  -o, --output-dir PATH   Output directory for transcription files
  -b, --batch             Process all files in directory
  -r, --recursive         Process files recursively (use with --batch)
  -q, --animated-quotes   Detect animated quotes with voice inflection analysis
  --quote-duration FLOAT  Duration of each animated quote in seconds (default: 15.0)
  --num-quotes INTEGER    Number of animated quotes to return (default: 10)
  --help                  Show help message
```

## Output Files

For each input file, the tool creates:

1. **`filename_transcription.txt`**: Clean text transcription
2. **`filename_transcription.json`**: Detailed JSON with:
   - Full transcription text
   - Language detection
   - Timestamped segments
   - Confidence scores
   - Metadata

### Animated Quote Detection Output

When using `--animated-quotes`, additional files are created:

3. **`filename_animated_quotes.txt`**: Formatted report with:
   - Quote text and timestamps
   - Topic classification
   - Animatedness scores
   - Topic distribution summary

4. **`filename_animated_quotes.json`**: Structured JSON with:
   - All quote data
   - Formatted timestamps
   - Topic categories
   - Animatedness scores

## Examples

### Single File Transcription
```bash
python transcribe.py meeting_recording.mp3 --model medium --language en
```

### Batch Processing with Custom Output
```bash
python transcribe.py ~/Downloads/podcasts/ --batch --recursive --output-dir ~/transcriptions/
```

### Translate Non-English Content
```bash
python transcribe.py german_interview.mp4 --task translate --model large
```

### Quick Preview with Tiny Model
```bash
python transcribe.py long_video.mp4 --model tiny
```

### Animated Quote Detection
```bash
# Find the most exciting 15-second quotes
python transcribe.py cisco_presentation.mp4 --animated-quotes

# Customize quote detection
python transcribe.py interview.mp3 --animated-quotes --quote-duration 20 --num-quotes 15

# Use larger model for better accuracy
python transcribe.py conference_talk.mp4 --animated-quotes --model large
```

## Two-List Quote Detection

The tool can generate two distinct lists of quotes from your content:

### List 1: Arbitrary 15-Second Quotes
- **Quantity**: Exactly 10 quotes (adjusted for shorter videos)
- **Duration**: Exactly 15 seconds per quote
- **Selection**: Arbitrary (sentence-aligned, evenly distributed)
- **Purpose**: Representative sample of content

### List 2: Animated Quotes with Topic Mix
- **Quantity**: Exactly 12 quotes
- **Duration**: Up to 15 seconds per quote
- **Selection**: Most animated quotes based on voice inflection
- **Topic Mix**: 30% each category (Current State, Future Direction, Products)
- **Purpose**: Most exciting content with balanced topic coverage

### Usage

```bash
# Generate two lists of quotes
python transcribe.py presentation.mp4 --two-lists

# Customize list sizes
python transcribe.py video.mp4 --two-lists --list1-count 8 --list2-count 10
```

## Animated Quote Detection

The animated quote detection feature analyzes voice inflection to find the most exciting and engaging quotes from your content. It's specifically designed for Cisco AI content but works with any audio/video material.

### How It Works

1. **Voice Inflection Analysis**: Uses advanced prosody features to detect excitement:
   - **Energy (RMS)**: Higher volume indicates excitement (20% weight)
   - **Spectral Centroid**: Brighter/more excited sound (20% weight)
   - **Zero Crossing Rate**: Rapid speech changes (15% weight)
   - **Spectral Rolloff**: High-frequency content (15% weight)
   - **MFCC Variance**: Timbre variation (15% weight)
   - **Pitch Variation**: Emotional expression (15% weight)

2. **Excitement Scoring**:
   - **Threshold**: Scores > 0.05 are considered candidates
   - **High Excitement**: Scores > 0.5 indicate strong animation
   - **Range**: 0.0 (monotone) to 1.0 (highly animated)

3. **Topic Classification**: Automatically categorizes content into:
   - **Current State**: Where Cisco currently is with AI technology
   - **Future Direction**: Where we are going
   - **Product Pipeline**: What is "on the truck" product-wise

4. **Smart Selection**: Returns exactly 10 quotes with:
   - **Even Distribution**: 3/3/4 (minimum 3 per category, remainder to strongest)
   - **Exactly 15-second duration**
   - **Highest animatedness scores**
   - **Precise timestamps**

### Example Output

```
Animated Quotes (10 found):
--------------------------------------------------

1. [00:01:15.000 - 00:01:30.000] (current_state)
   Excitement Score: 0.847 (High Excitement)
   Text: "We're already seeing incredible results with our current AI implementations..."

2. [00:03:42.500 - 00:03:57.500] (future_direction)
   Excitement Score: 0.823 (High Excitement)
   Text: "The future of AI at Cisco is going to revolutionize how we think about..."

3. [00:05:10.000 - 00:05:25.000] (product_pipeline)
   Excitement Score: 0.801 (High Excitement)
   Text: "What's coming on the truck next quarter will completely change the game..."
```

### Topic Categories

- **Current State**: Keywords like "currently", "now", "existing", "already", "in production"
- **Future Direction**: Keywords like "future", "next", "roadmap", "vision", "will be"
- **Product Pipeline**: Keywords like "on the truck", "pipeline", "launching", "shipping"

## Docker Details

### How It Works

The Docker wrapper scripts (`transcribe.sh` for macOS/Linux, `transcribe.bat` for Windows) do the following:

1. Check if Docker is installed
2. Build the Docker image on first run (only happens once)
3. Mount the directory containing your video file
4. Run the transcription inside the container
5. Save output files back to your host machine in the same directory

### Manual Docker Usage

If you prefer to use Docker commands directly:

```bash
# Build the image
docker build -t local-transcription .

# Run transcription (replace /path/to/video with your actual path)
docker run --rm \
  -v "/path/to/video/directory:/media" \
  local-transcription \
  /media/your-video.mp4 \
  --model base

# The transcription will be saved in /path/to/video/directory
```

### Docker Image Size

- Base image: ~400MB
- With all dependencies: ~2GB
- Whisper models are downloaded on first use and cached inside the container

### Rebuilding the Image

If you update the code and want to rebuild:

```bash
docker build -t local-transcription . --no-cache
```

## System Requirements

**For Docker (Recommended):**
- **Docker Desktop**: Version 4.0 or higher
- **RAM**: 4GB+ recommended (8GB+ for large model)
- **Storage**: ~2GB for Docker image + ~2GB for Whisper models
- **OS**: macOS, Windows 10/11, or Linux with Docker support

**For Python Installation:**
- **Python**: 3.8 or higher
- **FFmpeg**: For audio/video processing
- **RAM**: 4GB+ recommended (8GB+ for large model)
- **Storage**: ~2GB for all models
- **Additional Dependencies**: librosa, numpy, scipy, scikit-learn (for animated quote detection)

## Installation Troubleshooting

### FFmpeg Issues

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Python Dependencies

If you encounter issues with dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Memory Issues

If you run out of memory:
- Use a smaller model (`--model tiny` or `--model base`)
- Process files one at a time instead of batch processing
- Close other applications

## Privacy & Security

- ✅ All processing happens locally on your machine
- ✅ No data is sent to external servers
- ✅ No internet connection required after setup
- ✅ Your media files never leave your computer

## Performance Tips

1. **Model Selection**: Use `tiny` or `base` for quick processing, `large` for best accuracy
2. **Batch Processing**: More efficient than individual file processing
3. **File Formats**: WAV files process faster than compressed formats
4. **Hardware**: GPU acceleration is automatically used if available

## Troubleshooting

### Common Issues

**"No module named 'whisper'"**
```bash
pip install openai-whisper
```

**"FFmpeg not found"**
- Install FFmpeg for your system (see Installation Troubleshooting)

**"Out of memory"**
- Use a smaller model: `--model tiny`
- Process files individually

**"Unsupported file format"**
- Check that your file format is supported
- Convert to a supported format first

### Getting Help

If you encounter issues:
1. Check that all dependencies are installed
2. Verify FFmpeg is working: `ffmpeg -version`
3. Try with a smaller model first
4. Check file permissions and paths

## License

This tool uses OpenAI's Whisper model, which is licensed under the MIT License.