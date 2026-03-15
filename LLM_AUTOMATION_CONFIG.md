# LLM Automation Configuration Guide

This document describes how to configure Claude-powered task completion for automation tasks.

## Environment Variables

Add the following to your `.env` file to enable LLM-based task completion:

### Required Configuration

```bash
# Anthropic API Key (required if LLM_AUTO_COMPLETE_TASKS=true)
# Get your API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

### Optional Configuration

```bash
# Enable or disable LLM auto-complete (default: false)
# Set to true to automatically generate task completion details when tasks start
LLM_AUTO_COMPLETE_TASKS=false

# Claude model to use (default: claude-3-5-sonnet-20241022)
# See Anthropic docs for latest available models
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Maximum tokens for Claude response (default: 1024)
# Increase if you need longer completions
CLAUDE_MAX_TOKENS=1024

# Temperature for Claude responses (default: 0.7)
# Range: 0.0 (deterministic) to 1.0 (creative)
CLAUDE_TEMPERATURE=0.7
```

## Setup Steps

### 1. Install Dependencies

The `anthropic` package is already in `requirements.txt`. Install or update:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install anthropic==0.39.0
```

### 2. Get Your API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to "API Keys"
4. Create a new API key
5. Copy the key (it starts with `sk-ant-`)

### 3. Configure Environment

Add to `.env`:

```bash
ANTHROPIC_API_KEY=your-actual-api-key-here
LLM_AUTO_COMPLETE_TASKS=true
```

### 4. Verify Configuration

Run this to verify settings are loaded correctly:

```bash
python -c "from services.llm_config import validate_llm_config; validate_llm_config(); print('✓ LLM config valid')"
```

## How It Works

### Auto-Completion Flow

When you start an automation task:

1. **Task Starts**: Task transitions to `in_progress` status
2. **Trigger**: System asynchronously calls Claude to analyze the task
3. **Analysis**: Claude reads task details (title, description, metadata, context)
4. **Generation**: Claude generates three fields:
   - `implementation_summary`: 2-3 sentence summary of what was completed
   - `review_notes`: 2-3 bullet points for reviewer
   - `execution_notes`: 2-3 technical details or supporting evidence
5. **Submission**: Task automatically moves to `ready_for_review` with AI-generated details
6. **Human Review**: Compliance team reviews and can approve, edit, or reject

### Non-Blocking Execution

- The LLM analysis runs **asynchronously** in the background
- Starting a task returns immediately (doesn't wait for Claude)
- If Claude fails, task remains in `in_progress` state with error logged
- Human can still manually complete the task

### Feature Flag

Set `LLM_AUTO_COMPLETE_TASKS=false` to:
- Disable LLM auto-complete entirely
- Fall back to manual task completion
- **No code changes needed** — just update the env variable

## Examples

### Example 1: Local Development (Disabled)

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx  # For future use
LLM_AUTO_COMPLETE_TASKS=false                    # Don't run LLM yet
```

### Example 2: Staging (Enabled with Sonnet)

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
LLM_AUTO_COMPLETE_TASKS=true
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=1024
CLAUDE_TEMPERATURE=0.7
```

### Example 3: Production (Enabled with Opus for Quality)

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
LLM_AUTO_COMPLETE_TASKS=true
CLAUDE_MODEL=claude-3-5-opus-20240514               # Higher quality
CLAUDE_MAX_TOKENS=1500                              # Longer responses allowed
CLAUDE_TEMPERATURE=0.5                              # More deterministic
```

## Monitoring and Debugging

### Check if LLM is Enabled

```bash
python -c "from services.llm_config import get_llm_config; c = get_llm_config(); print(f'Enabled: {c.enabled}, Model: {c.model}')"
```

### View LLM Logs

Watch application logs for LLM activity:

```bash
# Look for these log patterns:
# "Spawning LLM completion for task X"
# "Analyzing task X with Claude..."
# "LLM analysis completed for task X"
# "Error in LLM completion for task X" (if something fails)
```

### Test LLM Connection

```python
from services.llm_completion_service import LLMCompletionAnalyzer

analyzer = LLMCompletionAnalyzer()
if analyzer.can_analyze():
    print("✓ LLM analyzer is ready")
else:
    print("✗ LLM analyzer not available (check config)")
```

### Check Task Metadata After LLM Completes

Task metadata will include:

```json
{
  "llm_completion_attempted": true,
  "llm_completion_timestamp": "2026-03-15T14:30:00+00:00",
  "llm_model": "claude-3-5-sonnet-20241022",
  "llm_completion_source": "claude_auto"
}
```

## API Costs

Claude API pricing varies by model. Visit https://anthropic.com/pricing for current rates.

**Cost Optimization Tips:**
- Use `claude-3-5-sonnet` for balance of quality and cost
- Keep `CLAUDE_MAX_TOKENS` reasonable (1024-1500)
- Set `CLAUDE_TEMPERATURE` lower (0.5-0.7) for deterministic responses
- Monitor usage in Anthropic dashboard

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not set"

**Solution:** Add a valid API key to `.env` and restart the app.

### Error: "anthropic package not installed"

**Solution:** Run `pip install anthropic`

### Tasks not automatically completing

**Check:**
1. Is `LLM_AUTO_COMPLETE_TASKS=true`?
2. Is `ANTHROPIC_API_KEY` set and valid?
3. Are there errors in logs? Look for "Error in LLM completion"

**Workaround:** Manually set task status to `ready_for_review` with implementation details.

### Claude responses are too generic or wrong

**Improve:**
1. Add more context to task description
2. Use task metadata fields (suggested_improvement, area, risk)
3. Refine Claude prompt in `services/llm_completion_service.py`
4. Lower CLAUDE_TEMPERATURE for consistency

### Rate limiting or quota exceeded

**Solution:**
1. Check Anthropic dashboard for usage
2. Upgrade API plan if needed
3. Implement batch processing (Phase 2)
4. Set LLM_AUTO_COMPLETE_TASKS=false temporarily

## Next Steps (Phase 2+)

Planned enhancements:
- [ ] Cost tracking and budget alerts
- [ ] Batch processing for multiple tasks
- [ ] Prompt optimization based on feedback
- [ ] Support for multiple LLM providers
- [ ] Streaming responses for real-time UI updates
- [ ] Manual override/edit UI for LLM summaries

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log | grep LLM`
2. Review Anthropic API docs: https://docs.anthropic.com/
3. Check Claude model availability: https://console.anthropic.com/docs/models
