# LLM Automation - Quick Reference Card

## 🚀 Enable LLM Auto-Completion

```bash
# These 2 environment variables enable the feature:
export LLM_AUTO_COMPLETE_TASKS=true
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: Configure model behavior
export CLAUDE_MODEL=claude-3-5-sonnet-20241022
export CLAUDE_MAX_TOKENS=1024
export CLAUDE_TEMPERATURE=0.7

# Restart application
python main.py
```

## 🔧 Verify Status

```bash
# Check if LLM is properly configured
curl http://localhost:8000/api/llm/status?company_id=1 \
  -H "Authorization: Bearer <your-token>"

# Expected response:
# {"enabled": true, "model": "claude-3-5-sonnet-20241022", "api_key_configured": true, ...}
```

## 📝 Frontend UI Changes

### What users see:

1. **New Badge in Task Header**
   - When LLM is generating: ⚡ Generating with AI... (animated blue)
   - After completion: ✨ AI-Generated (purple badge with date)

2. **New Section: "AI-Generated Completion Summary"**
   - Shows AI-generated content before edit form
   - Read-only display with bullet points
   - Shows model name and timestamp

3. **Existing Edit Form**
   - Still fully editable
   - Pre-populated with AI suggestions
   - All changes logged in activity trail

### When it appears:

- Task status must be: `in_progress`, `ready_for_review`, or `done`
- Requires: `metadata.llm_completion_attempted = true`

## 🔌 API Endpoints

### 1. Manually Trigger LLM
```bash
POST /api/llm/generate-completion/{task_id}?company_id=1

# Requires: Admin authorization
# Triggers LLM analysis immediately
# Moves task to ready_for_review
```

### 2. Check System Status
```bash
GET /api/llm/status?company_id=1

# Shows: enabled flag, model, API key, task count, avg time
```

### 3. Update Settings
```bash
POST /api/llm/settings

# Payload: {"enabled": true/false, "model": "...", "max_tokens": 1024}
# Requires: Super-admin authorization
# Changes apply at runtime only
```

### 4. Get Task LLM History
```bash
GET /api/llm/task-history/{task_id}?company_id=1

# Shows: generation timestamp, model, success/failure, error details
```

## 📊 Database Fields

LLM data stored in `task.metadata` JSON:

```json
{
  "llm_completion_attempted": true,
  "llm_completion_timestamp": "2024-01-15T10:30:00Z",
  "llm_model": "claude-3-5-sonnet-20241022",
  "llm_completion_source": "claude_auto",
  "llm_completion_failed": false,
  "llm_completion_error": null,
  "implementation_summary": "AI-generated text...",
  "review_notes": "Point 1\nPoint 2...",
  "execution_notes": "Detail 1\nDetail 2..."
}
```

## ⚠️ Troubleshooting

### Badges not showing?
```bash
# Check 1: Verify feature enabled
echo $LLM_AUTO_COMPLETE_TASKS  # Should be: true

# Check 2: Check task metadata
curl http://localhost:8000/api/llm/task-history/{task_id}?company_id=1 \
  -H "Authorization: Bearer <token>"

# Check 3: Browser cache
# Clear cache or use Ctrl+Shift+Delete
```

### API returns 503?
```bash
# LLM service is disabled. Fix:
export LLM_AUTO_COMPLETE_TASKS=true
export ANTHROPIC_API_KEY=sk-ant-...
# Restart application
```

### API returns 404?
```bash
# Endpoint not found. Check:
# 1. FastAPI server is running
# 2. main.py has: app.include_router(llm_admin_router)
# 3. routers/llm_admin.py exists
```

### LLM takes too long?
```bash
# Normal: 5-12 seconds (async, non-blocking)
# Check Anthropic API status at: https://status.anthropic.com
# Settings to optimize:
# - Lower CLAUDE_MAX_TOKENS (smaller output)
# - Reduce CLAUDE_TEMPERATURE (faster, less creative)
```

## 🔒 Safety Features

✅ **Disabled by default** - No API key = no LLM calls
✅ **Company scoping** - Each company's data isolated
✅ **Human review required** - AI content never auto-approved
✅ **Audit trail** - All actions logged with timestamps
✅ **Instant disable** - Set LLM_AUTO_COMPLETE_TASKS=false to stop
✅ **Graceful fallback** - If API fails, tasks marked for manual completion

## 📈 Monitoring

### Check LLM usage
```bash
# Get system status including task count
curl http://localhost:8000/api/llm/status?company_id=1

# Expected: task_with_llm_generation: (count)
```

### Monitor Anthropic costs
- Track API usage at: https://console.anthropic.com/
- Estimate: ~$0.001-0.003 per task
- Budget allocation: Consider ~$50-500/month based on volume

### View LLM audit trail
```sql
-- In database, check activity logs
SELECT * FROM activity_log 
WHERE action = 'llm_completion_generated'
ORDER BY created_at DESC;
```

## 🎯 Feature Flag Status

### For Developers
```javascript
// Frontend: Check if LLM badges should display
const isLLMGenerated = task.metadata?.llm_completion_attempted;
const isGenerating = task.status === "in_progress" && isLLMGenerated;

// Show appropriate badge
{isGenerating ? <LLMGeneratingBadge /> : <LLMGeneratedBadge />}
```

### For Operations/DevOps
```bash
# Feature flag is an environment variable
LLM_AUTO_COMPLETE_TASKS=true/false

# To disable instantly (no restart needed for checks)
# 1. Set environment variable to false
# 2. Restart application (changes applied at startup)

# To enable instantly
# 1. Set environment variable to true
# 2. Set ANTHROPIC_API_KEY
# 3. Restart application
```

## 📚 Full Documentation

- **Implementation Details**: `LLM_IMPLEMENTATION_COMPLETE.md`
- **Phase 3 & 4 Summary**: `PHASE_3_4_COMPLETION_SUMMARY.md`  
- **API Docstrings**: `routers/llm_admin.py`
- **Component Logic**: `frontend/.../TaskDetailDrawer.js`

## 💡 Quick Test Script

```bash
#!/bin/bash
# Quick validation of LLM setup

echo "1. Checking feature flag..."
echo "   LLM_AUTO_COMPLETE_TASKS=$LLM_AUTO_COMPLETE_TASKS"

echo "2. Checking API key..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "   ⚠️  ANTHROPIC_API_KEY not set"
else
  echo "   ✅ API key configured"
fi

echo "3. Testing LLM status endpoint..."
curl -s http://localhost:8000/api/llm/status?company_id=1 \
  -H "Authorization: Bearer YOUR_TOKEN" | jq .

echo "4. Done!"
```

---

**Version**: 1.0  
**Last Updated**: 2024-01  
**Next Review**: 2024-04
