# Contributing to Local Media Transcription Tool

Thank you for your interest in contributing! This project is designed to be easy to use and share.

## Ways to Contribute

### 1. Report Issues
- Found a bug? Open an issue on GitHub
- Include your OS, Docker version, and steps to reproduce
- Attach relevant error messages

### 2. Suggest Features
- Have an idea? Open a feature request
- Describe the use case and expected behavior
- Consider if it fits the project's goal of simplicity

### 3. Improve Documentation
- Fix typos or unclear instructions
- Add examples or use cases
- Improve troubleshooting guides

### 4. Submit Code Changes
- Fork the repository
- Create a feature branch
- Make your changes
- Test thoroughly (see TEST_CHECKLIST.md)
- Submit a pull request

## Development Setup

### For Python Development (without Docker)

```bash
# Clone the repository
git clone <your-repo-url>
cd local-transcription

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (if not already installed)
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: Download from ffmpeg.org
```

### For Docker Development

```bash
# Build the Docker image
docker build -t local-transcription .

# Test the image
docker run --rm -v "/path/to/test:/media" local-transcription /media/test.mp4
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and small
- Write docstrings for public functions

Example:
```python
def process_audio(file_path, language=None):
    """
    Process audio file and return transcription.
    
    Args:
        file_path (str): Path to audio/video file
        language (str, optional): Language code (e.g., 'en', 'es')
    
    Returns:
        dict: Transcription result with text and metadata
    """
    # Implementation here
    pass
```

## Testing

Before submitting changes:

1. **Run the test checklist:** Follow TEST_CHECKLIST.md
2. **Test on multiple formats:** Try with different audio/video formats
3. **Test all features:**
   - Basic transcription
   - Animated quotes
   - Two-list quotes
   - Different models
4. **Test Docker:** Rebuild and test the Docker image
5. **Update docs:** If you changed functionality, update relevant documentation

## Docker Changes

If you modify the Dockerfile or dependencies:

1. Test the build: `docker build -t local-transcription .`
2. Check image size: `docker images local-transcription`
3. Test functionality with the new image
4. Update .dockerignore if needed

## Documentation Changes

If you update documentation:

1. Check all links work
2. Verify code examples are correct
3. Test any commands you document
4. Keep the tone friendly and accessible
5. Update FILES_OVERVIEW.md if you add/remove files

## Pull Request Process

1. **Fork and Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write clear commit messages
   - Keep commits focused and atomic
   - Follow existing code patterns

3. **Test Thoroughly**
   - Run through TEST_CHECKLIST.md
   - Test on your platform (Mac/Windows/Linux)
   - Verify Docker still works

4. **Update Documentation**
   - Update README.md if needed
   - Add to USAGE_EXAMPLES.md if relevant
   - Update CHANGELOG.md

5. **Submit PR**
   - Provide clear description of changes
   - Reference any related issues
   - Include test results
   - Explain why the change is needed

6. **Code Review**
   - Address feedback promptly
   - Be open to suggestions
   - Update based on review

## Commit Message Format

Use clear, descriptive commit messages:

```
feat: Add support for WebM video format
fix: Resolve FFmpeg extraction issue on Windows
docs: Update Docker installation instructions
test: Add tests for animated quote detection
refactor: Simplify batch processing logic
```

Prefixes:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## Feature Requests

When suggesting features:

1. **Check existing issues** - Maybe it's already planned
2. **Describe the use case** - Why is this useful?
3. **Provide examples** - Show how it would work
4. **Consider complexity** - Is it worth the added complexity?

Good feature request:
```
Title: Add support for SRT subtitle export

Use case: I want to create subtitle files from transcriptions
for adding to videos.

Proposed solution: Add a --srt flag that exports timing and text
in SRT format alongside the existing outputs.

Example:
./transcribe.sh video.mp4 --srt
Creates: video_subtitles.srt

This would be useful for content creators who need subtitles
for accessibility and SEO.
```

## Bug Reports

Good bug reports include:

1. **Environment:**
   - OS and version
   - Docker version
   - Python version (if not using Docker)
   - FFmpeg version

2. **Steps to reproduce:**
   ```bash
   ./transcribe.sh test.mp4 --model base
   ```

3. **Expected behavior:**
   "Should create transcription.txt"

4. **Actual behavior:**
   "Crashes with error: ..."

5. **Error messages:**
   Include full error output

6. **Test file:**
   If possible, provide a test file or link

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions
- Help others learn

## Questions?

- Check existing documentation first
- Search closed issues
- Open a discussion for general questions
- Open an issue for specific problems

## Recognition

Contributors will be:
- Listed in the contributors section
- Credited in release notes
- Acknowledged in documentation

## License

By contributing, you agree that your contributions will be licensed
under the MIT License.

---

**Thank you for contributing!** Every contribution, no matter how small,
helps make this tool better for everyone. 🙏

