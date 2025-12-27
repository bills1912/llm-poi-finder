# Assumptions Made

This document outlines the assumptions made during the development of the HeyPico Maps LLM application.

## Technical Assumptions

### 1. Local LLM Environment

**Assumption:** The evaluator has or can install Ollama on their local machine.

**Justification:** 
- Ollama is free, open-source, and easy to install
- Supports multiple operating systems (Linux, macOS, Windows)
- Provides a simple API interface
- No cloud dependencies or API costs

**Alternative:** If Ollama is not available, the system can be modified to use:
- OpenAI API
- Anthropic Claude API
- Google Gemini API
- Any OpenAI-compatible endpoint

### 2. Google Cloud Free Tier

**Assumption:** A new Google Cloud account provides $300 free credit, sufficient for testing.

**Justification:**
- New Google Cloud accounts receive $300 credit valid for 90 days
- Maps API has a $200/month free tier even after credit expires
- Reasonable rate limits set to prevent exceeding free tier

**Cost Estimates (Monthly):**
| API | Free Tier | Est. Test Usage |
|-----|-----------|-----------------|
| Maps JavaScript | 25,000 loads | ~100 loads |
| Places API | $17/1000 requests | ~500 requests = ~$8.50 |
| Directions API | $5/1000 requests | ~100 requests = ~$0.50 |
| Geocoding API | $5/1000 requests | ~100 requests = ~$0.50 |

**Total estimated test cost: ~$10 (well within free credit)**

### 3. Modern Browser Environment

**Assumption:** Users access the application via a modern web browser with:
- JavaScript enabled
- Geolocation API support
- ES6+ support (Chrome 80+, Firefox 74+, Safari 13+, Edge 80+)

**Justification:**
- These features are standard in all major browsers since 2020
- Required for Google Maps JavaScript API
- Enables location-based features

### 4. Network Configuration

**Assumption:** The application runs in a development environment where:
- Localhost ports 3000 and 8000 are available
- No restrictive firewall blocking local connections
- Ollama runs on default port 11434

**Handling:** Port numbers are configurable via environment variables.

---

## Architectural Decisions

### 1. Backend-Only Google Maps API Calls

**Decision:** All Google Maps API calls are made from the backend, not directly from the frontend.

**Justification:**
- **Security:** API keys are never exposed to the client
- **Rate Limiting:** Centralized control over usage
- **Quota Management:** Server-side tracking prevents abuse
- **Logging:** All API usage can be logged and monitored

**Exception:** The Maps JavaScript API requires a frontend key for map rendering, but this key is restricted to specific HTTP referrers.

### 2. Ollama as Default LLM Provider

**Decision:** Use Ollama for local LLM inference instead of cloud APIs.

**Justification:**
- **No API costs:** Completely free to use
- **Privacy:** All data stays local
- **No rate limits:** Unlimited local inference
- **Test requirement:** Specification mentions "local LLM"

**Trade-offs:**
- Requires sufficient hardware (8GB+ RAM recommended)
- Model quality may vary based on chosen model
- Initial model download required

### 3. Simple In-Memory Rate Limiting

**Decision:** Use in-memory token bucket algorithm instead of Redis.

**Justification:**
- **Simplicity:** No additional infrastructure required
- **Demo scope:** Suitable for single-server deployment
- **Easy testing:** No external dependencies

**Production recommendation:** Use Redis for distributed rate limiting.

### 4. Stateless Conversation History

**Decision:** Conversation history is maintained client-side and sent with each request.

**Justification:**
- **Simplicity:** No database required for demo
- **Privacy:** User controls their data
- **Scalability:** Server remains stateless

**Trade-off:** History is lost on page refresh.

---

## Feature Scope Assumptions

### 1. Single User Focus

**Assumption:** The application is designed for single-user or limited concurrent user testing.

**Justification:**
- Demo/test environment
- In-memory rate limiting
- No user authentication

**Production requirements:** Add user authentication, persistent storage, and distributed caching.

### 2. Geographic Scope

**Assumption:** Default location is set to Yogyakarta, Indonesia (configurable).

**Justification:**
- Developer's location for realistic testing
- Easily changeable via configuration
- Google Maps API works globally

### 3. Language Support

**Assumption:** Interface is in English, but Google Maps results appear in the local language.

**Justification:**
- Simplifies development
- Google handles localization for place names
- LLM (Llama 3.2) has good multilingual support

---

## Model Selection Rationale

### Recommended: Llama 3.2 (3B or 7B)

**Justification:**
- Good instruction following for JSON output
- Reasonable size for local deployment
- Good general knowledge
- Fast inference on modern hardware

### Alternatives Considered

| Model | Pros | Cons |
|-------|------|------|
| Mistral 7B | Fast, good quality | Slightly worse at structured output |
| Phi-3 | Very small, fast | May miss nuances |
| Llama 3.1 70B | Best quality | Too large for most local machines |

---

## Security Assumptions

### 1. Development Environment

**Assumption:** The application runs in a trusted development environment.

**Production requirements:**
- HTTPS enforcement
- Proper CORS configuration
- API key rotation
- Input sanitization (implemented)
- Rate limiting (implemented)

### 2. API Key Handling

**Assumption:** Evaluator will create their own Google Cloud API keys.

**Best practices implemented:**
- Keys stored in environment variables
- Never logged or exposed in responses
- Masked in health check output
- Separate keys for frontend/backend

---

## Error Handling Assumptions

### 1. Graceful Degradation

**Assumption:** The application should continue to function partially if:
- LLM is unavailable → Show error, allow direct search
- Google Maps quota exceeded → Show error message
- Location unavailable → Use default location

### 2. User-Friendly Errors

**Assumption:** Technical errors should be translated to user-friendly messages.

**Implementation:**
- API errors caught and wrapped
- User sees helpful message, not stack traces
- Debug mode for development logging

---

## Future Enhancements (Out of Scope)

The following features were considered but not implemented for this test:

1. **User Authentication** - Would add complexity beyond demo scope
2. **Persistent Chat History** - Would require database
3. **Multiple Language UI** - English only for demo
4. **Real-time Updates** - WebSocket support
5. **Offline Support** - Service workers
6. **Mobile App** - React Native version
7. **Voice Input** - Speech-to-text integration
8. **Review Aggregation** - Multiple review sources

These features could be added in a production version.
