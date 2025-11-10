# Usage Examples

This document provides real-world examples of using the Local Media Transcription Tool.

## Basic Examples

### Simple Video Transcription

**Scenario:** You have a meeting recording in MP4 format that you want to transcribe.

```bash
./transcribe.sh ~/Videos/meeting-2024-01-15.mp4
```

**Output:**
- `meeting-2024-01-15_transcription.txt` - Plain text with timestamps
- `meeting-2024-01-15_transcription.json` - Detailed JSON

### High-Quality Transcription

**Scenario:** Important presentation that needs the most accurate transcription possible.

```bash
./transcribe.sh ~/Videos/product-launch.mp4 --model large
```

**Note:** The `large` model is slower but more accurate. Use for:
- Professional presentations
- Legal recordings
- Medical dictations
- Important interviews

### Quick Preview

**Scenario:** You want a quick rough transcript to decide if the content is useful.

```bash
./transcribe.sh ~/Videos/webinar-recording.mp4 --model tiny
```

**Note:** The `tiny` model is fast but less accurate. Good for:
- Previewing content
- Checking if recording worked
- Low-stakes transcriptions
- Testing the tool

## Language-Specific Examples

### Spanish Audio

```bash
./transcribe.sh ~/Audio/podcast-espanol.mp3 --language es
```

### French Video (Translate to English)

```bash
./transcribe.sh ~/Videos/french-interview.mp4 --language fr --task translate
```

### Auto-Detect Language

```bash
# No --language flag = automatic detection
./transcribe.sh ~/Videos/multilingual-conference.mp4
```

## Advanced Features

### Animated Quote Detection

**Scenario:** You have a 1-hour product presentation and want to extract the most exciting 10 moments.

```bash
./transcribe.sh ~/Videos/cisco-ai-presentation.mp4 --animated-quotes
```

**Output:**
- Regular transcription files
- `cisco-ai-presentation_animated_quotes.txt` - Top 10 exciting quotes with timestamps
- `cisco-ai-presentation_animated_quotes.json` - Structured data

**What you get:**
- 10 most animated/excited quotes (15 seconds each)
- Topic categorization (Current State, Future Direction, Product Pipeline)
- Excitement scores
- Exact timestamps for video editing

**Use cases:**
- Creating highlight reels
- Finding key moments for social media
- Identifying quotable content
- Sales enablement materials

### Two-List Quote Detection

**Scenario:** You need both representative samples AND exciting highlights from a presentation.

```bash
./transcribe.sh ~/Videos/keynote.mp4 --two-lists
```

**Output:**
- **List 1:** 10 arbitrary 15-second quotes (evenly distributed, representative sample)
- **List 2:** 12 most animated quotes with balanced topic coverage

**Use cases:**
- Marketing teams needing variety
- Creating multiple types of content
- A/B testing different quote styles
- Comprehensive content analysis

### Custom Quote Settings

**Scenario:** You want 20-second quotes instead of 15-second, and need 20 quotes total.

```bash
./transcribe.sh ~/Videos/long-interview.mp4 \
  --animated-quotes \
  --quote-duration 20 \
  --num-quotes 20
```

## Batch Processing Examples

### Process Entire Folder

**Scenario:** You have 50 podcast episodes to transcribe.

```bash
./transcribe.sh ~/Podcasts --batch
```

### Recursive Processing

**Scenario:** You have videos organized in subdirectories by date.

```
~/Videos/
  ├── 2024-01/
  │   ├── meeting-01.mp4
  │   └── meeting-02.mp4
  ├── 2024-02/
  │   ├── meeting-01.mp4
  │   └── meeting-02.mp4
```

```bash
./transcribe.sh ~/Videos --batch --recursive
```

**Result:** All videos in all subdirectories get transcribed, with outputs saved next to each video.

### Custom Output Directory

**Scenario:** You want all transcriptions in a central location instead of next to the videos.

```bash
./transcribe.sh ~/Videos --batch --output-dir ~/Transcriptions
```

## Real-World Workflows

### Workflow 1: Meeting Recording → Transcript → Summary

```bash
# 1. Record meeting (creates meeting.mp4)
# 2. Transcribe
./transcribe.sh ~/Recordings/meeting.mp4 --model medium

# 3. Output files are created:
#    - meeting_transcription.txt (easy to read)
#    - meeting_transcription.json (for further processing)

# 4. Use the .txt file for quick review
# 5. Use the .json file with other tools for analysis
```

### Workflow 2: Interview → Highlight Clips

```bash
# 1. Record 1-hour interview
# 2. Find the best moments
./transcribe.sh ~/Videos/ceo-interview.mp4 --animated-quotes

# 3. Review the animated quotes file to see the top 10 moments
# 4. Use the timestamps to create video clips

# Example output:
# [00:12:30.000 - 00:12:45.000]
# "This is going to completely transform how we think about AI..."
# Excitement Score: 0.847

# 5. Use video editor to extract clip from 00:12:30 to 00:12:45
```

### Workflow 3: Podcast Production

```bash
# 1. Record raw podcast
# 2. Get transcript with quotes
./transcribe.sh ~/Podcasts/episode-042.mp3 \
  --two-lists \
  --model large

# 3. Use List 1 (arbitrary quotes) for show notes
# 4. Use List 2 (animated quotes) for social media clips
# 5. Full transcript for blog post
```

### Workflow 4: Video Localization

```bash
# 1. Original video in Spanish
./transcribe.sh ~/Videos/spanish-training.mp4 \
  --language es \
  --task translate \
  --model large

# 2. Get English translation
# 3. Use for subtitles or dubbing script
```

### Workflow 5: Content Analysis

```bash
# 1. Conference with 20 sessions
./transcribe.sh ~/Conference2024 \
  --batch \
  --recursive \
  --animated-quotes

# 2. Get transcripts + animated quotes for all sessions
# 3. Analyze which sessions had most excitement
# 4. Create highlight reel from top animated moments across all sessions
```

## Performance Comparisons

### Model Speed vs. Accuracy

**Test video:** 60-minute presentation

| Model  | Time  | Accuracy | Best For |
|--------|-------|----------|----------|
| tiny   | 5 min | 85%      | Quick preview, testing |
| base   | 10 min| 90%      | General use, good balance |
| small  | 20 min| 93%      | Important content |
| medium | 40 min| 96%      | Professional use |
| large  | 90 min| 98%      | Critical accuracy needs |

**Note:** Times are approximate and depend on your hardware.

## Tips & Tricks

### Tip 1: Start Small

Always test with a small file first:

```bash
# Test with tiny model on short file
./transcribe.sh ~/Videos/test-clip.mp4 --model tiny

# If results look good, scale up
./transcribe.sh ~/Videos/full-video.mp4 --model medium
```

### Tip 2: Use Appropriate Models

- **tiny/base**: Casual meetings, quick notes, testing
- **small/medium**: Professional work, important meetings
- **large**: Legal, medical, critical documentation

### Tip 3: Organize Your Outputs

Create a workflow:

```bash
# Project structure
~/Projects/VideoProject/
  ├── raw/              # Original videos
  ├── transcripts/      # Transcriptions
  └── highlights/       # Animated quotes

# Transcribe with custom output
./transcribe.sh ~/Projects/VideoProject/raw/video.mp4 \
  --output-dir ~/Projects/VideoProject/transcripts
```

### Tip 4: Combine with Other Tools

Use the JSON output with other tools:

```bash
# Get transcript
./transcribe.sh video.mp4

# Process JSON with jq
cat video_transcription.json | jq '.segments[].text'

# Count words
cat video_transcription.txt | wc -w

# Search for keywords
grep "AI" video_transcription.txt
```

### Tip 5: Monitor Long Runs

For batch processing:

```bash
# Start batch job
./transcribe.sh ~/BigFolder --batch --recursive --model medium

# In another terminal, monitor progress
watch -n 5 'ls -ltrh ~/BigFolder/*_transcription.txt | tail'
```

## Common Scenarios

### Scenario: Podcast Show Notes

```bash
./transcribe.sh podcast-ep42.mp3 --model base
# → Use transcript to write show notes
# → Pull out key points for description
# → Create timestamps for chapters
```

### Scenario: YouTube Video Captions

```bash
./transcribe.sh youtube-video.mp4 --model medium
# → Use JSON segments for subtitle file
# → Timestamps are already included
# → Convert to SRT/VTT format
```

### Scenario: Legal Deposition

```bash
./transcribe.sh deposition.mp4 --model large
# → Highest accuracy for legal accuracy
# → Review and verify transcript
# → Use as starting point for official transcript
```

### Scenario: Accessibility

```bash
./transcribe.sh training-video.mp4 --model medium
# → Create accessible transcript
# → Add to video as captions
# → Provide text alternative
```

## Windows-Specific Examples

All examples above work on Windows by replacing `./transcribe.sh` with `transcribe.bat` and adjusting paths:

```cmd
REM Basic transcription
transcribe.bat C:\Users\You\Videos\meeting.mp4

REM With options
transcribe.bat C:\Users\You\Videos\meeting.mp4 --model large --animated-quotes

REM Batch processing
transcribe.bat C:\Users\You\Videos --batch
```

## Getting Help

Show all available options:

```bash
./transcribe.sh --help
```

Test your setup:

```bash
# Try with a small test file and tiny model
./transcribe.sh test-video.mp4 --model tiny
```

## Next Steps

1. Try the basic examples above
2. Read [DOCKER.md](DOCKER.md) for more Docker details
3. Check [README.md](README.md) for complete documentation
4. Experiment with different models and options
5. Share with your team!

