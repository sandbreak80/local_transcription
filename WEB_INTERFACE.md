# 🌐 Web Interface Guide

The Local Transcription Tool now includes a beautiful, user-friendly web interface! Perfect for non-technical users or anyone who prefers a visual interface over command-line tools.

**Author:** Brad Stoner (bmstoner@cisco.com)  
**Created for:** Splunk and Cisco  
**Version:** 1.1.0+

---

## 🎯 Why Use the Web Interface?

- ✅ **No Command Line Required** - Point, click, and go!
- ✅ **Drag & Drop Files** - Easy file upload
- ✅ **Multiple Files** - Process many files at once
- ✅ **Real-Time Progress** - See live progress bars
- ✅ **Visual Options** - Select model, language, and features visually
- ✅ **Auto Downloads** - Results are ready to download instantly
- ✅ **Queue Management** - See all your jobs in one place

---

## 🚀 Quick Start

### macOS & Linux

```bash
cd local-transcription
./transcribe-web.sh
```

### Windows

```batch
cd local-transcription
transcribe-web.bat
```

### Docker Compose

```bash
docker-compose up web
```

Then open your browser to: **http://localhost:5000**

---

## 📖 How to Use

### 1. Upload Files

**Three ways to add files:**

1. **Drag & Drop** - Drag files directly onto the upload area
2. **Click to Browse** - Click the upload box to select files
3. **Multiple Files** - Select as many files as you want!

**Supported formats:**
- Video: MP4, AVI, MOV, MKV, WMV, FLV, WebM
- Audio: MP3, WAV, M4A, AAC, FLAC, OGG, WMA

**File size limit:** 2GB per file

---

### 2. Select Options

**Model Quality** - Choose based on your needs:
- **Tiny** - Fastest (~5 min for 1hr video)
- **Base** - Balanced ⭐ Recommended (~10 min)
- **Small** - Better quality (~20 min)
- **Medium** - High quality (~40 min)
- **Large** - Best quality (~90 min)

**Language:**
- Auto-detect (recommended for most cases)
- Or select specific language for better accuracy

**Optional Features:**
- ☑️ **Animated Quotes** - Extract quotes with voice inflection
- ☑️ **Two-List Quotes** - Generate categorized quote lists

---

### 3. Start Transcription

Click **"Upload & Start Transcription"** button.

Your files will be:
1. ✅ Uploaded to the server
2. ✅ Added to the processing queue
3. ✅ Processed one at a time

---

### 4. Monitor Progress

**Each job card shows:**
- 📄 Filename
- 🎚️ Model & language
- 💾 File size
- 📊 Real-time progress bar (0-100%)
- 💬 Status messages
- 🏷️ Current status badge

**Status Types:**
- 🟡 **Queued** - Waiting to start
- 🔵 **Processing** - Currently transcribing
- 🟢 **Completed** - Done! Ready to download
- 🔴 **Failed** - Error occurred

---

### 5. Download Results

When a job completes:
1. ✅ Green "Completed" badge appears
2. ✅ Download section shows all output files
3. ✅ Click any file to download it instantly

**Output files you'll get:**
- `filename_transcription.txt` - Plain text transcript
- `filename_transcription.json` - Detailed JSON with timestamps
- `filename_animated_quotes.txt` - Animated quotes (if enabled)
- `filename_animated_quotes.json` - Animated quotes JSON (if enabled)
- `filename_two_list_quotes.txt` - Two-list quotes (if enabled)
- `filename_two_list_quotes.json` - Two-list quotes JSON (if enabled)

---

## 🎨 Web Interface Features

### Beautiful, Modern UI
- Clean, professional design
- Gradient backgrounds
- Smooth animations
- Responsive layout (works on mobile!)

### Real-Time Updates
- Progress bars update every 2 seconds
- No page refresh needed
- Live status badges

### Multiple File Support
- Upload multiple files at once
- Process them in order
- Track all jobs in one place

### Smart Queue Management
- Jobs process one at a time
- See position in queue
- Automatic retries on errors

---

## 🔧 Advanced Usage

### Custom Port

**macOS/Linux:**
```bash
PORT=8080 ./transcribe-web.sh
```

**Windows:**
```batch
set PORT=8080
transcribe-web.bat
```

**Docker Compose:**
```yaml
services:
  web:
    ports:
      - "8080:5000"  # Change 8080 to your desired port
```

---

### Running in Background

**Docker Compose:**
```bash
docker-compose up -d web
```

**View logs:**
```bash
docker-compose logs -f web
```

**Stop:**
```bash
docker-compose down
```

---

### Accessing from Other Devices

If you want to access the web interface from other computers on your network:

1. Find your computer's IP address:
   - **macOS/Linux:** `ifconfig | grep inet`
   - **Windows:** `ipconfig`

2. On the other device, open browser to:
   ```
   http://YOUR_IP_ADDRESS:5000
   ```

**Example:** `http://192.168.1.100:5000`

⚠️ **Security Note:** Only do this on trusted networks!

---

## 📊 System Requirements

### Minimum
- 4GB RAM
- 2GB free disk space
- Docker Desktop 4.0+
- Modern web browser

### Recommended
- 8GB+ RAM (for better performance)
- 10GB free disk space (for larger files)
- Chrome, Firefox, Safari, or Edge (latest versions)

---

## 🐛 Troubleshooting

### Port Already in Use

**Error:** "Port 5000 is already allocated"

**Solution:** Use a different port:
```bash
PORT=8080 ./transcribe-web.sh
```

---

### Cannot Upload Files

**Check:**
1. File size under 2GB?
2. Supported file format?
3. Enough disk space?

---

### Jobs Stuck in Queue

**Try:**
1. Refresh the page
2. Check Docker logs: `docker logs <container_id>`
3. Restart the web server

---

### Downloads Not Working

**Check:**
1. Job status is "Completed"?
2. Pop-up blocker disabled?
3. Browser has download permission?

---

## 🎯 Tips & Best Practices

### For Best Results

1. ✅ **Use Base model** for good balance of speed/quality
2. ✅ **Enable Auto-detect language** unless you're sure
3. ✅ **Upload smaller files first** to test
4. ✅ **Close browser tab** while processing (it's okay!)
5. ✅ **Check file format** before uploading

---

### Performance Tips

- **Tiny model** for quick previews
- **Base model** for daily use
- **Large model** for critical/published content
- Process overnight for large files
- Multiple small files > one huge file

---

### Batch Processing Strategy

1. Upload all files at once
2. Start with fastest model (tiny) to verify
3. Re-process important ones with better model
4. Download and organize results

---

## 📚 Related Documentation

- [QUICKSTART.md](QUICKSTART.md) - Basic usage
- [DOCKER.md](DOCKER.md) - Docker details
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - CLI examples
- [README.md](README.md) - Main documentation

---

## 🆘 Need Help?

### Common Questions

**Q: Can I close the browser while processing?**  
A: Yes! Jobs continue in the background. Just refresh the page to see progress.

**Q: How many files can I upload at once?**  
A: No hard limit, but they process one at a time.

**Q: Can I cancel a job?**  
A: Currently no - let it complete or restart the server.

**Q: Are my files secure?**  
A: Yes! Everything processes locally. No data leaves your machine.

**Q: Where are output files stored?**  
A: In `./outputs/` folder in your project directory.

---

## 🎉 Enjoy the Web Interface!

The web interface makes transcription accessible to everyone - no technical skills required! Perfect for:

- 👔 Business professionals
- 🎓 Students and educators
- 📹 Content creators
- 🎙️ Podcasters
- 👨‍👩‍👧‍👦 Anyone who prefers visual tools

**Made with ❤️ by Brad Stoner for Splunk and Cisco**

