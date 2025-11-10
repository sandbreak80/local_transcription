# How to Share This Tool

This guide explains how to share the Local Media Transcription Tool with colleagues, team members, or the public.

## What Makes This Easy to Share?

✅ **Docker-based** - Recipients only need Docker installed  
✅ **Zero dependencies** - No Python, FFmpeg, or library headaches  
✅ **Simple scripts** - One command to transcribe  
✅ **Cross-platform** - Works on Mac, Windows, and Linux  
✅ **Self-contained** - Everything needed is in this repository  

## Sharing Options

### Option 1: Share the GitHub Repository (Recommended)

**Best for:** Teams, open source, ongoing updates

1. Push this repository to GitHub/GitLab/Bitbucket
2. Share the repository URL
3. Recipients follow [QUICKSTART.md](QUICKSTART.md):
   - Install Docker
   - Clone the repo
   - Run `./transcribe.sh video.mp4` (or `transcribe.bat` on Windows)

**Advantages:**
- Easy updates (git pull)
- Issue tracking
- Version control
- Collaborative improvements

**Example README for your repo:**
```markdown
# Transcription Tool

Transcribe videos with one command!

## Quick Start

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Clone this repo: `git clone <your-repo-url>`
3. Run: `./transcribe.sh /path/to/video.mp4`

See [QUICKSTART.md](QUICKSTART.md) for details.
```

### Option 2: Share as a ZIP File

**Best for:** Non-technical users, one-time sharing, no GitHub account

1. Create a ZIP of this entire directory
2. Share via email, Dropbox, Google Drive, etc.
3. Recipients:
   - Extract the ZIP
   - Install Docker Desktop
   - Open terminal/command prompt in the extracted folder
   - Run `./transcribe.sh video.mp4` (Mac/Linux) or `transcribe.bat video.mp4` (Windows)

**Include these instructions in your email:**
```
How to use:

1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
2. Extract the attached ZIP file
3. Open Terminal (Mac) or Command Prompt (Windows)
4. Navigate to the extracted folder
5. Run one of:
   Mac/Linux: ./transcribe.sh /path/to/your/video.mp4
   Windows:   transcribe.bat C:\path\to\your\video.mp4

The first run takes ~5 minutes to setup. After that it's fast!

See QUICKSTART.md for more details.
```

### Option 3: Share the Docker Image

**Best for:** Air-gapped systems, restricted environments, frequent distribution

#### 3a. Save and Share Image File

```bash
# Build the image
docker build -t local-transcription .

# Save to a file
docker save local-transcription > local-transcription.tar

# Compress for easier sharing (optional)
gzip local-transcription.tar
```

Share the `.tar` or `.tar.gz` file. Recipients load it:

```bash
# Load the image
docker load < local-transcription.tar

# Or if compressed
gunzip -c local-transcription.tar.gz | docker load

# Use it
docker run --rm -v "/path/to/videos:/media" local-transcription /media/video.mp4
```

**Pro:** No build time for recipients  
**Con:** Large file (~2GB), harder to update

#### 3b. Publish to Docker Hub

```bash
# Tag the image
docker tag local-transcription yourusername/local-transcription:latest

# Login to Docker Hub
docker login

# Push the image
docker push yourusername/local-transcription:latest
```

Recipients use it:

```bash
# Pull the image
docker pull yourusername/local-transcription:latest

# Run it
docker run --rm -v "/path/to/videos:/media" yourusername/local-transcription /media/video.mp4
```

**Pro:** Easy updates, professional distribution  
**Con:** Requires Docker Hub account, images are public (unless paid plan)

#### 3c. Use Private Docker Registry

For organizations with their own Docker registry:

```bash
# Tag for your registry
docker tag local-transcription registry.yourcompany.com/local-transcription:latest

# Push
docker push registry.yourcompany.com/local-transcription:latest
```

### Option 4: Internal Wiki/Confluence Page

**Best for:** Large organizations, corporate environments

Create a wiki page with:

1. Link to internal Git repository or shared drive
2. Installation instructions (customized for your IT environment)
3. Usage examples specific to your use cases
4. Contact person for support
5. FAQs based on your team's questions

**Example structure:**

```markdown
# Video Transcription Tool

## What It Does
Transcribe meeting recordings, presentations, and interviews locally.

## Access
- Internal Git: https://git.company.com/tools/transcription
- Or download: \\shared-drive\tools\transcription.zip

## Setup
1. Install Docker Desktop (request via IT ServiceDesk: TOOL-12345)
2. Clone/download the tool
3. Follow QUICKSTART.md

## Usage Examples
### Weekly Team Meetings
./transcribe.sh "\\shared-drive\meetings\team-weekly-2024-01-15.mp4"

### Customer Interviews  
./transcribe.sh ~/Downloads/customer-interview.mp4 --animated-quotes

## Support
- Slack: #transcription-tool
- Email: tools-support@company.com
```

## What to Include When Sharing

### Minimum Files Needed

```
local-transcription/
├── Dockerfile              # Docker configuration
├── transcribe.py           # Main script
├── animated_quotes.py      # Quote detection
├── two_list_quotes.py      # Two-list quotes
├── requirements.txt        # Python dependencies
├── transcribe.sh           # Mac/Linux wrapper
├── transcribe.bat          # Windows wrapper
├── .dockerignore          # Docker build optimization
├── QUICKSTART.md          # Getting started guide
└── README.md              # Full documentation
```

### Optional but Recommended

```
├── DOCKER.md              # Detailed Docker docs
├── USAGE_EXAMPLES.md      # Real-world examples
├── SHARING.md             # This file
├── docker-compose.yml     # Alternative usage method
└── media/                 # Example directory for testing
```

### Not Needed for Distribution

```
├── venv/                  # Virtual environment (local only)
├── __pycache__/          # Python cache (local only)
├── setup.py              # Only for non-Docker installation
├── test_*.py             # Development tests
├── example_usage.py      # Development examples
├── .git/                 # Git history (unless using Git)
└── media/*.mp4           # Don't share media files
```

## Customization Before Sharing

### 1. Update Repository URL

In QUICKSTART.md and README.md, replace `<your-repo-url>` with your actual URL:

```bash
git clone https://github.com/yourname/local-transcription
```

### 2. Add Your Branding (Optional)

Update README.md header:

```markdown
# YourCompany Video Transcription Tool

Powered by OpenAI Whisper | Maintained by Your Team Name
```

### 3. Customize Default Settings (Optional)

In `transcribe.sh` and `transcribe.bat`, you can change the default model:

```bash
# Change from 'base' to 'medium' for better default accuracy
--model medium
```

### 4. Add Company-Specific Examples

Add your use cases to USAGE_EXAMPLES.md:

```markdown
### Your Company Use Case
./transcribe.sh ~/CompanyFolder/sales-call.mp4 --animated-quotes
```

## Support Strategy

### For Small Teams (< 10 people)

- Share your email/Slack for questions
- Add FAQ to README as questions come up
- Schedule a 15-minute demo call

### For Large Teams/Organizations

- Create Slack/Teams channel
- Designate 1-2 support contacts
- Document common issues in wiki
- Hold weekly office hours initially
- Create video tutorial
- Set up ticketing system

### For Open Source

- Use GitHub Issues for support
- Create Discussion forum for questions
- Add Contributing.md for improvements
- Use GitHub Releases for versions
- Add CI/CD for automated testing

## Example Support Response Template

For common questions:

```
Hi [Name],

Thanks for trying the transcription tool! 

For your issue with [X], try:

1. Make sure Docker Desktop is running
2. Use the full path to your video file
3. Try with --model tiny first to test

See [DOCKER.md](DOCKER.md) for more troubleshooting.

Need more help? Reply with:
- Your OS (Mac/Windows/Linux)
- The exact command you ran
- The error message you got

Thanks!
```

## License Considerations

This tool uses:
- **OpenAI Whisper** - MIT License
- **FFmpeg** - LGPL/GPL (depending on build)
- **Python libraries** - Various open source licenses

If distributing publicly, include a LICENSE file. MIT or Apache 2.0 are common choices.

Example LICENSE file (MIT):

```
MIT License

Copyright (c) 2024 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy...
[full MIT license text]
```

## Tracking Usage (Optional)

For internal tools, you might want to track usage:

**Option 1: Simple Logging**

Add to transcribe.sh:

```bash
# Log usage (append to shared file)
echo "$(date),$(whoami),$FILE_NAME" >> /shared/transcription-usage.log
```

**Option 2: Analytics (for public tools)**

Add basic telemetry (with user consent) to track:
- Number of transcriptions
- Model sizes used
- Feature usage (animated quotes, etc.)
- Error rates

**Important:** Always disclose telemetry and make it opt-in!

## Update Strategy

### Notifying Users of Updates

**Git-based:**
```bash
git pull  # Users pull latest changes
```

**Email/Slack:**
```
New version available!

Changes:
- Fixed bug in animated quotes
- Added support for new video formats
- Improved accuracy with model updates

To update:
1. cd local-transcription
2. git pull
3. docker build -t local-transcription . --no-cache

See CHANGELOG.md for details.
```

**Docker Hub:**
```bash
docker pull yourusername/local-transcription:latest
```

### Versioning

Use semantic versioning in your README:

```markdown
# Local Media Transcription Tool v1.2.0

Version 1.2.0 - 2024-01-15
- Added two-list quote detection
- Improved performance for large files
- Bug fixes

See CHANGELOG.md for full history.
```

## Security Considerations

When sharing:

✅ **Do:**
- Remove any hardcoded credentials
- Remove company-specific paths/names
- Remove test media files
- Review Docker image for sensitive data
- Document security features (runs locally, no external calls)

❌ **Don't:**
- Include production credentials
- Include proprietary media files
- Include personal information
- Expose internal infrastructure details

## Success Metrics

Track adoption:

- Number of clones/downloads
- GitHub stars/forks (if public)
- Support questions (decreasing over time = good docs)
- Feature requests (increasing = engagement)
- Success stories from users

## Getting Feedback

Add to your README:

```markdown
## Feedback

Love this tool? Have suggestions?

- Open an [issue](https://github.com/yourname/repo/issues)
- Email: your-email@example.com
- Slack: #transcription-tool

We'd love to hear how you're using it!
```

## Example Launch Announcement

**Email/Slack:**

```
🎉 New Tool: Local Video Transcription

Tired of manually transcribing meeting recordings?

We built a tool that transcribes videos locally on your machine:
- Works with any video/audio format
- Finds exciting quotes automatically
- Completely private (nothing leaves your computer)
- One command to use

Try it:
1. Install Docker Desktop
2. Clone: git clone [repo-url]
3. Run: ./transcribe.sh your-video.mp4

Full docs: [link to README]
Quick start: [link to QUICKSTART.md]

Questions? Ask in #transcription-tool or reply to this message.

Happy transcribing! 🎙️
```

## Conclusion

Choose the sharing method that fits your audience:

| Audience | Best Method | Pros |
|----------|-------------|------|
| Technical team | Git repo | Easy updates, collaboration |
| Small non-tech team | ZIP file | Simple, self-contained |
| Large organization | Docker Hub + wiki | Professional, scalable |
| Public/open source | GitHub | Community, visibility |

The Docker-based approach makes this tool remarkably easy to share. Recipients only need Docker - everything else is included!

