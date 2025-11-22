# Application Issues Analysis

## Critical Issues (Prevent App from Running)

### 1. Missing FFmpeg Installation ❌
**Location:** System dependency
**Impact:** Application cannot process videos at all
**Evidence:**
- `ffmpeg` and `ffprobe` not found in system PATH
- All video processing modules depend on FFmpeg
- Video cropping, audio merging, subtitle compositing will fail

**Fix Required:**
```bash
# Ubuntu/Debian
apt-get update && apt-get install -y ffmpeg

# MacOS
brew install ffmpeg
```

---

### 2. Missing Python Dependencies ❌
**Location:** `requirements.txt` not installed
**Impact:** Cannot import required modules
**Evidence:**
- `ModuleNotFoundError: No module named 'pydantic_settings'`
- Virtual environment likely not set up

**Fix Required:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Missing Environment Configuration ❌
**Location:** `.env` file
**Impact:** No API keys configured, all external services will fail
**Evidence:**
- `.env` file does not exist
- OpenAI, ElevenLabs, RunPod endpoints won't work

**Fix Required:**
```bash
cp .env.example .env
# Edit .env with actual API keys
```

---

## Security Issues 🔒

### 4. Hardcoded API Key in Test File
**Location:** `test_runpod_direct.py:7`
**Impact:** Security vulnerability - exposed RunPod API key
**Evidence:**
```python
headers = {
    "Authorization": "Bearer rpa_MBB20AN2T8P8AFLINDQH9PB8XBXVB5KUVT0DQ99J12yoxr",
```

**Fix Required:**
- Remove hardcoded key
- Load from environment variables
- Rotate the exposed API key

---

## Configuration Issues ⚙️

### 5. Hardcoded File Paths in Tests
**Location:** `test_gen.py:6-7`
**Impact:** Tests won't work on different machines
**Evidence:**
```python
GAMEPLAY_VIDEO = "/Users/naman/Downloads/videoplayback.mp4"
EXISTING_AUDIO = "/Users/naman/Downloads/clip_app2/..."
```

**Fix Required:**
- Use relative paths: `test_assets/example_gameplay.mp4`
- Make paths configurable or use Path objects

---

### 6. Missing Font Files
**Location:** `subtitle_styles/` directory
**Impact:** Subtitle rendering will fail or use fallback fonts
**Evidence:**
- Styles reference fonts like "Arial-Bold", "Impact"
- No .ttf or .otf files found in repository
- Will fall back to `ImageFont.load_default()`

**Fix Required:**
- Include required font files in repository
- Document font installation requirements
- Or use system fonts with proper fallback handling

---

## Feature Implementation Issues 🚧

### 7. YOLO Face Tracking Not Implemented
**Location:** `modules/video_processor.py:108-111`
**Impact:** Videos are center-cropped instead of subject-tracked
**Evidence:**
```python
# If we had face tracking, we'd use it here.
# Let's just use center for now.
face_x=width//2, # Center
face_y=height//2, # Center
```

**Dependencies Listed But Unused:**
- `ultralytics>=8.3.0` in requirements.txt (appears twice - line 12 & 16)
- No YOLO model imports or usage

**Missing Implementation:**
- Object/person detection using YOLO
- Tracking logic to follow main subject
- Fallback to center when no subject detected

---

### 8. Duplicate Dependencies
**Location:** `requirements.txt:12,16`
**Impact:** Minor - redundant package specification
**Evidence:**
```
ultralytics>=8.3.0
...
ultralytics>=8.3.0  # Listed twice
```

---

## Potential Runtime Issues ⚠️

### 9. Async/Await Mismatch in Main Endpoint
**Location:** `main.py:48`
**Impact:** May cause issues with transcription
**Evidence:**
- `process_script` is async def
- Calls `await transcriber.transcribe()` (correct)
- But transcriber uploads to tmpfiles.org using async httpx
- Need to ensure all async contexts are properly handled

---

### 10. No Error Handling for Missing Test Assets
**Location:** `test_gen.py`, `test_runpod_direct.py`
**Impact:** Unclear error messages when files don't exist
**Evidence:**
- No validation that GAMEPLAY_VIDEO exists
- No validation that test assets are present

---

### 11. Logger Handler Duplication
**Location:** `utils/logging.py:4-18`
**Impact:** Duplicate log entries if logger is called multiple times
**Evidence:**
```python
def setup_logger(name: str, log_file: Path, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.addHandler(handler)  # No check if handler already exists
    logger.addHandler(console_handler)
```

**Fix Required:**
- Check if logger already has handlers
- Clear handlers before adding new ones
- Or use a different logger name each time

---

### 12. tmpfiles.org URL Dependency
**Location:** `modules/transcriber.py:8-49`
**Impact:** Single point of failure for transcription
**Evidence:**
- Depends on tmpfiles.org availability (1-hour expiry)
- No fallback upload service
- If tmpfiles.org is down, transcription fails entirely

**Improvement Suggestions:**
- Add fallback file hosting options
- Support direct file upload to RunPod (if available)
- Add retry logic with exponential backoff

---

## Testing Recommendations

### To Test the App:

1. **Setup Environment**
   ```bash
   # Install FFmpeg
   apt-get install -y ffmpeg

   # Setup Python environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Configure API keys
   cp .env.example .env
   # Edit .env with real keys
   ```

2. **Fix Test Files**
   ```bash
   # Update test_gen.py to use local assets
   # Remove hardcoded paths
   ```

3. **Run Tests**
   ```bash
   # Start server
   python main.py

   # In another terminal - test basic transcription
   python test_runpod_direct.py  # After fixing API key issue

   # Test full pipeline
   python test_gen.py  # After fixing paths
   ```

4. **Implement YOLO Tracking**
   - Load YOLO model (YOLOv8)
   - Detect person/main subject per frame
   - Track centroid across frames
   - Use tracked position for video cropping

---

## Priority Fix Order

1. **Critical (Must Fix to Run):**
   - Install FFmpeg
   - Install Python dependencies
   - Create .env file with API keys

2. **Security (Fix Before Production):**
   - Remove hardcoded API key from test file
   - Add .env to .gitignore (verify)

3. **Configuration:**
   - Fix hardcoded paths in test files
   - Add font files or document font requirements

4. **Features:**
   - Implement YOLO tracking
   - Remove duplicate dependencies
   - Add error handling and fallbacks

5. **Code Quality:**
   - Fix logger handler duplication
   - Add tmpfiles.org fallback options
