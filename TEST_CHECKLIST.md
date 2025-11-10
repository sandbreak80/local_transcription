# Docker Setup Test Checklist

Use this checklist to verify your Docker setup works correctly before sharing.

## Pre-Testing Setup

- [ ] Docker Desktop is installed
- [ ] Docker Desktop is running (check menu bar/system tray)
- [ ] You have a test video file (ideally < 5 minutes for quick testing)

**Verify Docker:**
```bash
docker --version
# Should show: Docker version 20.x.x or higher
```

## Test 1: Script Execution

**Mac/Linux:**
```bash
# Make executable
chmod +x transcribe.sh

# Verify it's executable
ls -l transcribe.sh
# Should show: -rwxr-xr-x
```

- [ ] Script is executable
- [ ] No permission errors

**Windows:**
```cmd
# Just verify the file exists
dir transcribe.bat
```

- [ ] Batch file exists
- [ ] Can be run from Command Prompt

## Test 2: Docker Image Build

```bash
# Build the image manually first
docker build -t local-transcription .
```

**Expected behavior:**
- [ ] Build starts without errors
- [ ] All steps complete successfully
- [ ] No "failed" or "error" messages
- [ ] Build completes in 5-10 minutes
- [ ] Final message: "Successfully tagged local-transcription:latest"

**Verify the image:**
```bash
docker images | grep local-transcription
```

- [ ] Image appears in list
- [ ] Size is ~1-2GB

## Test 3: Basic Transcription (Tiny Model)

```bash
# Use tiny model for quick test (replace with your video path)
./transcribe.sh /path/to/your/test-video.mp4 --model tiny
```

**Expected behavior:**
- [ ] "Loading Whisper model 'tiny'..." message appears
- [ ] "Processing: test-video.mp4" message appears
- [ ] Progress indicators show up
- [ ] No error messages
- [ ] "Transcription saved:" message appears
- [ ] Process completes without crashes

**Verify outputs:**
```bash
# Check the output files exist (in same folder as video)
ls -l /path/to/your/test-video*.txt
ls -l /path/to/your/test-video*.json
```

- [ ] `test-video_transcription.txt` exists
- [ ] `test-video_transcription.json` exists
- [ ] Both files are not empty (> 0 bytes)
- [ ] TXT file is human-readable
- [ ] JSON file is valid JSON

**Verify content quality:**
```bash
# View the transcript
cat /path/to/your/test-video_transcription.txt
```

- [ ] Text is readable English (or correct language)
- [ ] Timestamps are present in format [HH:MM:SS.mmm - HH:MM:SS.mmm]
- [ ] Content matches what's in the video
- [ ] No gibberish or random characters

## Test 4: Medium/Large Model

```bash
./transcribe.sh /path/to/test-video.mp4 --model medium
```

- [ ] Works without errors
- [ ] Better accuracy than tiny model
- [ ] Takes longer (expected)
- [ ] Output files created

## Test 5: Animated Quotes

```bash
./transcribe.sh /path/to/test-video.mp4 --animated-quotes --model tiny
```

**Expected behavior:**
- [ ] Regular transcription happens first
- [ ] "Detecting animated quotes..." message appears
- [ ] "Quote detector loaded successfully!" message
- [ ] Process completes

**Verify outputs:**
```bash
ls -l /path/to/your/test-video*animated_quotes*
```

- [ ] `test-video_animated_quotes.txt` exists
- [ ] `test-video_animated_quotes.json` exists
- [ ] Files contain quote data with timestamps
- [ ] Excitement scores are present
- [ ] Topics are categorized

## Test 6: Two-List Quotes

```bash
./transcribe.sh /path/to/test-video.mp4 --two-lists --model tiny
```

- [ ] Works without errors
- [ ] Creates `_two_list_quotes.txt`
- [ ] Creates `_two_list_quotes.json`
- [ ] Contains both List 1 and List 2
- [ ] List 1: Arbitrary quotes
- [ ] List 2: Animated quotes with topics

## Test 7: Language Handling

**If you have non-English content:**

```bash
# Auto-detect language
./transcribe.sh /path/to/spanish-video.mp4 --model tiny

# Specify language
./transcribe.sh /path/to/spanish-video.mp4 --language es --model tiny

# Translate to English
./transcribe.sh /path/to/spanish-video.mp4 --task translate --model tiny
```

- [ ] Auto-detection works correctly
- [ ] Specified language works
- [ ] Translation to English works

## Test 8: Different File Formats

Test with various formats if available:

**Video formats:**
- [ ] MP4 works
- [ ] MOV works (if available)
- [ ] AVI works (if available)
- [ ] MKV works (if available)

**Audio formats:**
- [ ] MP3 works
- [ ] WAV works (if available)
- [ ] M4A works (if available)

## Test 9: Error Handling

**Non-existent file:**
```bash
./transcribe.sh /path/to/nonexistent.mp4
```

- [ ] Shows clear error message
- [ ] Doesn't crash or hang
- [ ] Error message is helpful

**Invalid file:**
```bash
# Try with a text file renamed to .mp4
./transcribe.sh /path/to/invalid-file.mp4
```

- [ ] Shows error about invalid format
- [ ] Doesn't crash
- [ ] Container exits cleanly

**Without arguments:**
```bash
./transcribe.sh
```

- [ ] Shows usage help
- [ ] Lists examples
- [ ] Shows available options

## Test 10: Windows Compatibility

**If you have access to Windows:**

```cmd
transcribe.bat C:\path\to\video.mp4 --model tiny
```

- [ ] Works on Windows
- [ ] Paths with spaces work
- [ ] Backslashes in paths work
- [ ] Output appears in correct location

## Test 11: Docker Compose (Optional)

```bash
# Build with docker-compose
docker-compose build

# Test help
docker-compose run --rm transcribe --help

# Copy test video to media folder
cp /path/to/test-video.mp4 ./media/

# Run transcription
docker-compose run --rm transcribe /media/test-video.mp4 --model tiny
```

- [ ] Docker compose builds successfully
- [ ] Help command works
- [ ] Transcription works
- [ ] Output appears in ./media/

## Test 12: Performance Check

**Time the execution:**

```bash
time ./transcribe.sh /path/to/5min-video.mp4 --model tiny
```

**Expected timing for 5-minute video:**
- [ ] Tiny model: < 2 minutes
- [ ] Base model: < 5 minutes
- [ ] Medium model: < 10 minutes
- [ ] Large model: < 20 minutes

**Note:** Times vary by hardware. These are rough estimates.

## Test 13: Resource Usage

**While transcription is running:**

```bash
# In another terminal
docker stats
```

**Check:**
- [ ] Container appears in stats
- [ ] CPU usage is high (expected during processing)
- [ ] Memory usage is reasonable (< 4GB for tiny/base, < 8GB for large)
- [ ] No memory leaks (usage doesn't keep growing)

## Test 14: Cleanup

**After transcription:**

```bash
# Check no containers left running
docker ps

# Check no dangling volumes
docker volume ls
```

- [ ] No containers running after completion
- [ ] No dangling volumes created
- [ ] Workspace is clean

## Test 15: Rebuild Test

**Test rebuilding the image:**

```bash
# Rebuild with cache
docker build -t local-transcription .

# Rebuild without cache
docker build -t local-transcription . --no-cache
```

- [ ] Both rebuilds work
- [ ] Cached build is fast (< 1 min)
- [ ] No-cache build works (takes full time)

## Test 16: Documentation Check

- [ ] README.md has Docker instructions at top
- [ ] QUICKSTART.md is clear and accurate
- [ ] DOCKER.md covers troubleshooting
- [ ] All links in docs work
- [ ] Code examples in docs use correct syntax

## Test 17: User Simulation

**Pretend you're a new user:**

1. [ ] Can you find installation instructions quickly?
2. [ ] Are the commands copy-pasteable?
3. [ ] Do the examples work as written?
4. [ ] Are error messages helpful?
5. [ ] Can you find help when stuck?

## Final Verification

**Before sharing:**

- [ ] All tests above passed
- [ ] No errors in any test
- [ ] Documentation is accurate
- [ ] Scripts have correct permissions
- [ ] Repository is clean (no test files)
- [ ] .gitignore is working
- [ ] README has been updated with Docker info
- [ ] You've tested on at least one other machine (if possible)

## Optional: External Testing

**If you want to be thorough:**

- [ ] Test on a friend's machine
- [ ] Test with someone not familiar with Docker
- [ ] Test on different OS (Mac, Windows, Linux)
- [ ] Test with their video files (different formats/sources)
- [ ] Gather their feedback on documentation

## Common Issues Found During Testing

### Issue: "Docker is not installed"
**Fix:** Reminder in docs that Docker Desktop must be installed and running.

### Issue: "Permission denied" on transcribe.sh
**Fix:** Add to docs: `chmod +x transcribe.sh`

### Issue: Output files not found
**Reason:** User used relative paths, volume mount didn't work.
**Fix:** Emphasized absolute paths in documentation.

### Issue: Out of memory
**Reason:** Large model on 4GB RAM machine.
**Fix:** Added model size recommendations to docs.

### Issue: First run takes forever
**Reason:** Downloading Whisper model.
**Fix:** Added "First run notes" to QUICKSTART.md.

## Post-Testing Actions

After all tests pass:

1. **Document your test environment:**
   ```
   Tested on:
   - OS: macOS 14.2 / Windows 11 / Ubuntu 22.04
   - Docker: Version 24.0.x
   - Hardware: 16GB RAM, 8-core CPU
   - Test video: 5-minute MP4, 1080p
   - Date: 2024-01-15
   ```

2. **Update docs based on findings:**
   - Add any missing troubleshooting steps
   - Clarify confusing instructions
   - Add warnings for common mistakes

3. **Create a test report:**
   - All tests passed: ✓
   - Issues found: [list]
   - Issues fixed: [list]
   - Ready for distribution: Yes/No

4. **Tag a release (if using Git):**
   ```bash
   git tag -a v1.0.0 -m "First stable Docker release"
   git push origin v1.0.0
   ```

## Automated Testing Script (Optional)

Create `test.sh` for quick testing:

```bash
#!/bin/bash
# Quick automated test

echo "Testing Docker setup..."

# Check Docker
docker --version || exit 1

# Build image
docker build -t local-transcription . || exit 1

# Test with help
./transcribe.sh --help || exit 1

echo "✓ All automated tests passed!"
echo "Now run manual tests with a real video."
```

## Success Criteria

Your Docker setup is ready to share when:

✅ All tests in this checklist pass  
✅ Documentation is clear and accurate  
✅ No errors or crashes in normal usage  
✅ Someone else can use it successfully  
✅ You're confident in supporting it  

## You're Ready!

Once this checklist is complete, you're ready to share your tool with the world! 🚀

See [SHARING.md](SHARING.md) for distribution strategies.

