# GEMINI.md - Gemini AI Integration Documentation

## Overview

ARGUS uses Google Gemini AI models for vision analysis and reasoning tasks. This document describes how Gemini is integrated, configured, and used throughout the platform.

## Gemini Models Used

### Primary Models
- **gemini-2.0-flash** - Latest Gemini model for vision and text (primary)
- **gemini-2.0-flash** - Used for both vision and text analysis

### Fallback Models
When the primary model hits quota limits, ARGUS automatically switches to:
- **gemini-1.5-flash** - Fast, efficient model for quick analysis
- **gemini-1.5-pro** - Higher accuracy model for complex tasks

## Configuration

Gemini is configured in `backend/app/config.py`:

```python
GEMINI_MODEL: str = "gemini-2.0-flash"
GEMINI_VISION_MODEL: str = "gemini-2.0-flash"
GEMINI_FALLBACK_MODELS: List[str] = ["gemini-1.5-flash", "gemini-1.5-pro"]
```

API key is set via environment variable:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

## Usage in Agents

### Vision Agent (`backend/app/agents/vision.py`)

The Vision Agent uses Gemini Vision API to analyze uploaded images:

**Capabilities:**
- Detect objects and damage indicators
- Classify incident types (bridge collapse, flood, wildfire, etc.)
- Estimate severity levels (low, medium, high, critical)
- Extract visual evidence
- Identify location clues
- Recommend risk factors

**Implementation:**
```python
import google.generativeai as genai

# Initialize with API key
genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel(settings.GEMINI_VISION_MODEL)

# Analyze image
response = model.generate_content([
    prompt,
    image_data
])
```

**Fallback Logic:**
If the primary model hits quota limits (HTTP 429, quota exceeded), the agent automatically tries fallback models in sequence, logging warnings for each attempt.

### Other Agents

While most text-based agents use Groq for speed, Gemini is available for:
- Complex reasoning tasks
- Vision-text multimodal analysis
- When Groq models are unavailable

## API Key Management

### Getting a Free API Key

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add to `.env` file

### Quota Management

Free tier limits:
- 15 requests per minute
- 1,500 requests per day
- Rate limiting with HTTP 429 errors

ARGUS handles quota limits gracefully:
- Automatic model fallback
- Retry with exponential backoff
- Warning logs for diagnostics
- Pipeline continues with degraded results if all models fail

## System Prompts

### Vision Agent System Prompt

The Vision Agent uses a detailed system prompt to guide Gemini's analysis:

```
You are a specialized infrastructure damage analysis AI.
Your role is to analyze images of infrastructure incidents...
```

This ensures consistent, high-quality analysis focused on:
- Structural damage detection
- Incident classification
- Severity estimation
- Evidence extraction

## Error Handling

### Common Errors

**Quota Exceeded (429):**
- Automatically tries fallback models
- Logs warning with model name
- Continues pipeline if possible

**Invalid API Key:**
- Raises clear error message
- Prevents pipeline execution
- Requires valid key in `.env`

**Content Policy Violation:**
- Logs error details
- Skips analysis if content is blocked
- Continues with other agents

## Performance Optimization

### Image Preprocessing
- Resize large images to reduce API calls
- Convert to optimal format (PNG/JPEG)
- Base64 encoding for transmission

### Caching
- Vision analysis results cached in database
- Reuse for report generation
- Avoid redundant API calls

### Batch Processing
- Multiple images analyzed in parallel
- Synthesis of findings across images
- Efficient use of API quota

## Testing

### Manual Testing

Test Gemini integration with:
```bash
cd backend
python -c "from app.agents.vision import VisionAgent; agent = VisionAgent(); print(agent)"
```

### Demo Mode

Use built-in demo scenarios to test without API quota:
- Bridge Failure
- Urban Flood
- Wildfire
- Power Grid Failure

## Troubleshooting

### Issue: "API key not valid"
**Solution:** Check `.env` file has correct `GOOGLE_API_KEY`

### Issue: "Quota exceeded"
**Solution:** Wait for quota reset or upgrade to paid tier

### Issue: "Content blocked"
**Solution:** Ensure images don't violate content policies

### Issue: Slow analysis
**Solution:** Check image size, resize if needed

## Future Enhancements

- Add Gemini 1.5 Pro for higher accuracy
- Implement streaming responses for real-time updates
- Add Gemini Flash for ultra-fast analysis
- Integrate Gemini Code for code generation tasks
- Use Gemini for report generation

## References

- [Google AI Studio](https://aistudio.google.com)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Gemini Vision Guide](https://ai.google.dev/gemini-api/docs/vision)
- [Quota and Pricing](https://ai.google.dev/pricing)
