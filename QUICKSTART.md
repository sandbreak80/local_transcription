# Quick Start Guide

Get transcribing in 5 minutes! 🚀

## Step 1: Install Docker

Download Docker Desktop for your operating system:

- **Mac:** https://docs.docker.com/desktop/install/mac-install/
- **Windows:** https://docs.docker.com/desktop/install/windows-install/
- **Linux:** https://docs.docker.com/engine/install/

Install and start Docker Desktop. That's your only prerequisite!

## Step 2: Get This Tool

Download or clone this repository to your computer.

```bash
git clone <your-repo-url>
cd local-transcription
```

Or download and extract the ZIP file.

## Step 3: Transcribe!

### On Mac/Linux:

```bash
./transcribe.sh /path/to/your/video.mp4
```

### On Windows:

```cmd
transcribe.bat C:\path\to\your\video.mp4
```

**First time?** The script will automatically build everything (takes ~5 minutes). After that, it's instant!

## What Happens?

1. Your video is analyzed
2. A transcript is generated
3. Output files appear in the same folder as your video:
   - `video_transcription.txt` - Easy-to-read transcript
   - `video_transcription.json` - Detailed data with timestamps

## Common Commands

### Better Accuracy (Slower)

```bash
./transcribe.sh video.mp4 --model large
```

### Find Exciting Moments

```bash
./transcribe.sh video.mp4 --animated-quotes
```

This finds the 10 most exciting/animated moments in your video!

### Spanish/Other Languages

```bash
./transcribe.sh video.mp4 --language es
```

### Process Entire Folder

```bash
./transcribe.sh /path/to/videos --batch
```

## Model Sizes

Choose based on your needs:

- `--model tiny` - ⚡ Super fast, good accuracy (default for testing)
- `--model base` - ⚡ Fast, better accuracy (recommended default)
- `--model medium` - 🎯 Slower, great accuracy (recommended for important content)
- `--model large` - 🎯 Slowest, best accuracy (professional use)

## Need Help?

```bash
./transcribe.sh --help
```

## More Information

- **Usage Examples:** See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)
- **Docker Details:** See [DOCKER.md](DOCKER.md)
- **Full Documentation:** See [README.md](README.md)

## Troubleshooting

**"Docker is not installed"**
- Make sure Docker Desktop is running (check your menu bar/system tray)

**"File not found"**
- Use the full path to your video file
- On Mac: Right-click file → "Get Info" → copy path
- On Windows: Shift + Right-click file → "Copy as path"

**Slow/Out of Memory**
- Use a smaller model: `--model tiny`
- Close other applications

**Still stuck?**
- Check [DOCKER.md](DOCKER.md) troubleshooting section
- Open an issue on GitHub

## That's It!

You're ready to transcribe. It really is that simple. Docker makes sure everything just works! 🎉

---

**Privacy Note:** Everything runs locally on your computer. No data is sent anywhere. No internet needed (after first-time setup).

