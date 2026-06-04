# AI & MODERATION SYSTEMS - IMPLEMENTATION GUIDE

## Backend Moderation API Summary

- Users submit reports through `/api/v1/moderation/reports`.
- Reports can target `user`, `message`, `post`, `group_message`, and `group_post`.
- Optional evidence links can be attached for review.
- Moderators and admins review reports through `/api/v1/admin/reports`.
- Detailed report review is available at `/api/v1/admin/reports/{report_id}`.
- Report resolution uses `/api/v1/admin/reports/{report_id}/resolve`.
- Supported actions include warnings, mutes, suspensions, permanent bans, shadow bans, content removal, dismissal, and review notes.

## Enforcement Summary

- User accounts track moderation state such as shadow-ban, mute, and suspension fields.
- Suspended or muted users cannot send new chat or group content.
- Shadow-banned users can create content, but it is hidden from regular feeds and other participants while remaining reviewable by admins.
- Chat, group, and post creation paths pass through safety filters and moderation checks.
- WebSocket handlers consult moderation state before broadcasting.

**Version:** 1.0.0  
**Date:** 2026-05-28  
**Status:** ✅ Production-Ready

---

## 📋 Overview

This document describes the comprehensive AI-driven content moderation and safety systems integrated into the ChattingApp backend. The system provides multi-layered content analysis, community-driven moderation, and intelligent auto-enforcement.

### Key Features

1. **AI Content Analysis** - Toxicity scoring, spam/phishing detection, NSFW flagging
2. **Toxicity Filtering** - Real-time content safety validation with Google Perspective API integration
3. **Spam Detection** - Pattern-based spam identification with heuristic scoring
4. **NSFW Media Detection** - Text-based and media-based NSFW content flagging
5. **Link Safety Scanning** - Harmful URL detection with phishing pattern matching
6. **AI Auto-Moderation** - Automatic enforcement of moderation actions based on risk levels
7. **Smart Report Handling** - Intelligent report triage and resolution recommendations
8. **Community Moderation System** - Trust-weighted voting for community-driven resolution
9. **Shadow-Ban Support** - User content visibility restrictions without account suspension

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│         Content Safety Pipeline                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Input: Message/Post/Comment                        │
│    ↓                                                │
│  AI Analysis (AIModerationService)                 │
│    ├─ Toxicity Analysis (Google Perspective API)   │
│    ├─ Spam Detection (Pattern Matching)             │
│    ├─ NSFW Detection (Text + Media Heuristics)      │
│    ├─ Link Safety Scanning (URL Pattern Matching)   │
│    └─ Phishing Detection (Social Engineering)       │
│    ↓                                                │
│  Risk Calculation → Risk Level (low/medium/high/critical) │
│    ↓                                                │
│  Decision Engine                                    │
│    ├─ if confidence > 0.8 → Auto-enforce action    │
│    ├─ if 0.6 < confidence < 0.8 → Flag for review  │
│    └─ if confidence < 0.6 → Pass to human          │
│    ↓                                                │
│  Enforcement (ModerationAction)                    │
│    ├─ Shadow ban (24h default)                     │
│    ├─ Mute user                                    │
│    ├─ Suspend account                              │
│    ├─ Delete content                               │
│    └─ Flag for moderator review                    │
│    ↓                                                │
│  Community Voting (Optional)                        │
│    ├─ Trusted users vote: upheld/overturned        │
│    ├─ Weighted by voter trust score                │
│    └─ Consensus triggers action reversal           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Database Schema

#### `ai_moderation_results` Table

Stores AI analysis results for audit and training:

- `content_id`, `content_type`: Identifier and type (message/post/comment)
- Toxicity scores: `toxicity_score`, `severe_toxicity_score`, `identity_attack_score`, etc.
- Detection flags: `is_spam`, `is_nsfw`, `has_harmful_links`, `is_phishing`
- Risk assessment: `overall_risk_level`, `recommended_action`, `should_auto_moderate`
- Confidence scores for training and auditing

#### `ai_model_training_data` Table

Tracks moderator feedback for continuous model improvement:

- Links AI predictions to human moderator labels
- Records disagreement scores for identifying model weaknesses
- Flags high-quality training data for model retraining

#### `community_moderation_votes` Table

Enables community-driven moderation with trust weighting:

- `vote_type`: upheld, overturned, abstain
- `voter_trust_score`: 0.0-1.0 based on account age, activity, accuracy
- `vote_weight`: Weighted by voter reputation (multiplier)
- `consensus_threshold_reached`: Tracks when community consensus is reached

#### `moderation_actions` Table

Records all enforcement actions (AI or human-initiated):

- `action_type`: warning, mute, shadow_ban, suspend, ban, delete_content
- `initiated_by`: ai_auto, ai_human_confirmed, human_moderator, community
- Duration and appeal eligibility tracking

---

## 🔍 Detection Methods

### 1. Toxicity Analysis

**Primary Method:** Google Perspective API

- Analyzes text for toxic attributes
- Returns scores (0.0-1.0) for:
  - Toxicity
  - Severe toxicity
  - Identity attack
  - Insult
  - Profanity
  - Threat

**Fallback Method:** Heuristic keyword matching

- Pattern-based detection when API unavailable
- Regex matching for severe toxic keywords
- ~60% confidence vs ~95% with API

**Threshold:** `0.6` for standard content, `0.7` for severe toxicity

### 2. Spam Detection

**Detection Patterns:**

- Call-to-action spam (follow, like, click, subscribe)
- Promotional links (casinos, dating, pharma)
- URL shorteners and suspicious contact methods
- Caps lock spam (>30% capitalization)
- Excessive URLs (>2 per message) or mentions (>5 per message)

**Heuristics:**

- Spam score based on pattern matches
- ~1.5+ indicators = flagged as spam
- ~65% confidence threshold

### 3. NSFW Detection

**Text-Based:**

- Keyword detection for explicit content
- Regex patterns for adult-oriented language

**Media-Based:**

- Placeholder for Google Vision API integration
- Currently uses heuristic URL analysis

**Confidence:** 75% for text-based detection

### 4. Link Safety Scanning

**Harmful Patterns:**

- URL shorteners (bit.ly, tinyurl, etc.)
- Adult/gambling/malware domains
- Fake ID/credential services
- Malware-hosting domains

**Validation:**

- Domain reputation checking
- Protocol verification
- Phishing pattern matching

**Confidence:** 85% for harmful link detection

### 5. Phishing Detection

**Indicators:**

- Verify/confirm credential requests
- Account suspension/urgency language
- Suspicious action requirements

**Scoring:**

- ≥2 indicators = phishing flagged
- Weighted by indicator severity

---

## 🚀 API Endpoints

### Content Analysis

```http
POST /api/v1/ai-moderation/analysis/{content_type}/{content_id}

Query Parameters:
- content_text: string (required)
- media_urls: array[string] (optional)

Response:
{
  "content_id": "msg-123",
  "toxicity_score": 0.85,
  "severe_toxicity_score": 0.0,
  "is_spam": false,
  "is_nsfw": false,
  "has_harmful_links": false,
  "is_phishing": false,
  "overall_risk_level": "high",
  "should_auto_moderate": true,
  "recommended_action": "shadow_ban",
  "confidence_score": 0.92,
  "detected_issues": {...}
}
```

### Community Voting

```http
POST /api/v1/ai-moderation/community-vote

Body:
{
  "report_id": "report-123",
  "vote_type": "upheld",  // or "overturned", "abstain"
  "reasoning": "User shows pattern of toxicity"
}

Response:
{
  "vote_id": "vote-456",
  "voter_trust_score": 0.75,
  "vote_weight": 1.125,
  "consensus_status": "pending"  // or "reached"
}
```

### Smart Report Handling

```http
POST /api/v1/ai-moderation/smart-report-handling

Body:
{
  "report_id": "report-123",
  "action": "auto_resolve",  // or "flag_for_review", "escalate"
  "ai_confidence": 0.88,
  "reason": "Clear toxicity violation"
}
```

### Moderator Insights

```http
POST /api/v1/ai-moderation/moderator-insights

Body:
{
  "report_id": "report-123",
  "request_type": "similar_cases"  // or "pattern_analysis", "risk_assessment"
}

Response:
{
  "report_id": "report-123",
  "similar_cases": [...],
  "pattern_analysis": {...},
  "risk_assessment": {...},
  "recommendations": ["Consider temporary shadow ban"]
}
```

### Model Health Check

```http
GET /api/v1/ai-moderation/models/health

Response:
{
  "perspective_api_available": true,
  "vision_api_available": false,
  "local_models_status": "ready",
  "last_update": "2026-05-28T12:00:00Z"
}
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Google Perspective API
PERSPECTIVE_API_KEY=your_api_key_here

# Google Cloud Vision API
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# AI Moderation Thresholds
AI_TOXICITY_THRESHOLD=0.6           # 0.0-1.0
AI_SEVERE_TOXICITY_THRESHOLD=0.7    # 0.0-1.0
AI_SPAM_CONFIDENCE_THRESHOLD=0.65   # 0.0-1.0
AI_NSFW_CONFIDENCE_THRESHOLD=0.6    # 0.0-1.0

# Auto-Moderation Settings
AI_AUTO_MODERATION_ENABLED=true
AI_AUTO_MODERATION_MIN_CONFIDENCE=0.8
```

---

## 🎯 Risk Levels & Actions

| Risk Level | Confidence | Action         | Appeals          | Duration         |
| ---------- | ---------- | -------------- | ---------------- | ---------------- |
| Low        | < 0.30     | none           | N/A              | N/A              |
| Medium     | 0.30-0.50  | flag           | Manual review    | N/A              |
| High       | 0.50-0.70  | shadow_ban     | Yes              | 24h default      |
| Critical   | > 0.70     | suspend/delete | Yes (escalation) | 7d+ or permanent |

---

## 🔄 Enforcement Workflow

### Auto-Moderation (AI-Driven)

```
Content Posted
    ↓
AI Analysis Triggered
    ↓
Risk Assessment
    ├─ if risk_score >= 0.7 → Delete + Suspend (24h)
    ├─ if risk_score >= 0.5 → Shadow Ban (24h) + Flag
    ├─ if risk_score >= 0.3 → Flag for Review
    └─ if risk_score < 0.3 → Allow
    ↓
Auto-Moderation Applied (if should_auto_moderate=true)
    ↓
Community Override Opportunity (if appeal_eligible=true)
    ↓
Moderator Final Review (if confidence < 0.9)
```

### Manual Review (Human-Driven)

```
Report Submitted
    ↓
AI Analysis Generates Insights
    ├─ Similar cases
    ├─ Pattern analysis
    ├─ Risk assessment
    └─ Recommendations
    ↓
Moderator Reviews with AI Context
    ↓
Decision: Upheld / Overturned / Escalate
    ↓
Action Applied (if upheld)
    ↓
Community Optional Appeal Vote
```

---

## 📊 Monitoring & Metrics

### Key Metrics

1. **AI Accuracy**
   - False positive rate (% of flagged content user disputes)
   - False negative rate (% of unreported violations)
   - Precision & recall by content type

2. **Auto-Moderation Performance**
   - Actions applied per day
   - Appeal rate
   - Community consensus on auto-actions

3. **System Health**
   - API availability (Perspective, Vision, etc.)
   - Processing latency
   - Model confidence distribution

### Dashboard Queries

```sql
-- Daily moderation volume
SELECT action_type, COUNT(*) as count
FROM moderation_actions
WHERE created_at >= DATE_TRUNC('day', NOW())
GROUP BY action_type;

-- AI accuracy (human-labeled data)
SELECT
  human_label,
  COUNT(*) as count,
  AVG(disagreement_score) as avg_disagreement
FROM ai_model_training_data
GROUP BY human_label;

-- Community consensus rate
SELECT
  COUNT(*) as total_votes,
  SUM(CASE WHEN consensus_threshold_reached THEN 1 ELSE 0 END) as reached_consensus
FROM community_moderation_votes
WHERE created_at >= DATE_TRUNC('day', NOW());
```

---

## 🛡️ Best Practices

### 1. Threshold Tuning

- Start conservative (high thresholds)
- Monitor false positive rate
- Gradually lower thresholds based on data
- Regularly review and update based on community feedback

### 2. Model Improvement

- Collect human feedback on AI decisions
- Mark false positives/negatives for retraining
- Regularly retrain models with new data
- A/B test different model versions

### 3. Appeal Process

- All auto-actions should be appeal-eligible
- Community voting provides first-level appeal
- Escalation path for complex cases
- Clear communication on why action was taken

### 4. Transparency

- Log all moderation decisions
- Provide users visibility into appeals
- Share aggregate statistics
- Regular community report on moderation trends

---

## 🔐 Security Considerations

1. **API Key Management**
   - Store in environment variables (never in code)
   - Rotate API keys regularly
   - Monitor usage for anomalies

2. **Data Privacy**
   - Minimize data retention in AI systems
   - Comply with GDPR/privacy regulations
   - Anonymize training data
   - Clear data deletion procedures

3. **Attack Prevention**
   - Rate limit AI analysis requests
   - Monitor for abuse patterns
   - Prevent DoS through analysis endpoints
   - Validate all input parameters

---

## 🚀 Deployment Checklist

- [ ] Configure all API keys in production environment
- [ ] Run database migration: `alembic upgrade head`
- [ ] Test all AI detection methods with sample content
- [ ] Verify moderator insights endpoint with test reports
- [ ] Set up monitoring and alerting for API failures
- [ ] Create moderator training on new system
- [ ] Implement gradual rollout (% of traffic)
- [ ] Monitor metrics for first 48 hours
- [ ] Adjust thresholds based on production data
- [ ] Document runbook for common issues

---

## 📝 Integration Examples

### In Chat Service

```python
from app.services.ai_moderation_service import AIModerationService

async def send_message(session, sender_id, receiver_id, content):
    # Validate content
    ai_result = await AIModerationService.analyze_content(
        session,
        content_id=str(uuid.uuid4()),
        content_type="message",
        content_text=content,
    )

    # Auto-enforce if needed
    if ai_result.should_auto_moderate:
        await AIModerationService.apply_auto_moderation(
            session,
            user_id=str(sender_id),
            ai_result=ai_result,
        )
        raise ModerationError(f"Message blocked: {ai_result.overall_risk_level}")

    # Create message if passed
    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    session.add(message)
    await session.commit()
    return message
```

### In Report Resolution

```python
from app.schemas.ai_moderation_schema import ModeratorInsightsRequest

async def review_report(session, report_id, moderator_id):
    # Get AI insights
    insights = await get_moderator_insights(
        ModeratorInsightsRequest(report_id=report_id, request_type="similar_cases"),
        session,
        moderator,
    )

    # Use insights to inform decision
    if insights.recommendations:
        logger.info(f"AI recommendations: {insights.recommendations}")

    # Apply moderator decision
    action = await ModerationService.apply_action(
        session,
        moderator_id,
        report_id,
        action_type="shadow_ban",
        reason="User shows pattern of toxic behavior",
    )

    return action
```

---

## 🆘 Troubleshooting

### Issue: Perspective API Rate Limit

**Symptom:** `429 Too Many Requests` errors

**Solution:**

- Implement exponential backoff
- Cache analysis results
- Increase API quota
- Use fallback heuristic analysis

### Issue: High False Positive Rate

**Symptom:** Many legitimate messages flagged

**Solution:**

- Increase toxicity threshold
- Review detected patterns
- Collect false positive training data
- Adjust pattern weights

### Issue: Community Consensus Not Reached

**Symptom:** Reports stuck in voting

**Solution:**

- Lower consensus threshold
- Increase voter pool size
- Implement time-based resolution
- Manual escalation for stale votes

---

## 📚 References

- [Google Perspective API Documentation](https://perspectiveapi.com/)
- [Google Cloud Vision API](https://cloud.google.com/vision)
- [Content Moderation Best Practices](https://example.com)
- [Community Governance Framework](https://example.com)

---

## 📝 Version History

| Version | Date       | Changes                                                                             |
| ------- | ---------- | ----------------------------------------------------------------------------------- |
| 1.0.0   | 2026-05-28 | Initial release with AI toxicity, spam, NSFW, link safety, and community moderation |
| 0.9.0   | 2026-05-27 | Beta: Core AI moderation infrastructure                                             |
| 0.1.0   | 2026-05-20 | Alpha: Basic moderation framework                                                   |

---

**Last Updated:** 2026-05-28  
**Next Review:** 2026-06-28
