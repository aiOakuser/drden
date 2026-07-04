# Designer AI Setup Guide

This guide explains how to set up and use the designrden Designer AI chat assistant.

## Architecture

**Django-first flow:**
```
Browser → POST /api/ai/stream → Django (ai_chat app) → OpenAI API → SSE stream → Browser
```

- **Streaming**: `/api/ai/stream/` uses SSE for fast UX; text appears progressively
- **Fallback**: `/api/ai/designer-chat/` returns full JSON response (non-streaming)
- **Auth & DB**: Django handles auth, session, and message history

## Overview

Designer AI is a chat assistant built into designrden for the designer platform. It helps with:
- Portfolio structure and layouts
- Profile bios, proposal emails, pricing guidance
- Using designrden features
- Image sizes, formats, and media guidelines
- API and integration questions

## Features

1. **Floating Chat Bubble**: Available on all pages (bottom-right corner)
2. **SSE Streaming**: Responses stream in progressively for faster perceived performance
3. **Contextual Help Bars**: Appear on key pages like portfolio edit/create
4. **Smart Responses**: Uses OpenAI (optional) or rule-based fallback
5. **Documentation Links**: Automatically links to relevant docs (RAG)

## Setup

### Basic Setup (Rule-Based Responses)

The chat works out of the box with rule-based responses. No additional setup needed!

### OpenAI Integration (Streaming + Smart Responses)

For intelligent, streaming responses:

1. **Install OpenAI library** (already in requirements.txt):
   ```bash
   pip install openai
   ```

2. **Store OPENAI_API_KEY securely**
   - **Local dev**: Add to `.env` (copy from `.env.example`). `.env` is in `.gitignore`.
   - **Production (Coolify/VPS)**: Set `OPENAI_API_KEY` as an environment variable in your service config. Never commit keys to code.

   ```bash
   # .env (local – never commit)
   OPENAI_API_KEY=your-api-key-here
   OPENAI_MODEL=gpt-4o-mini  # Optional
   ```

3. **Restart your Django server**

The system will use OpenAI for streaming when the key is configured; otherwise it falls back to rule-based responses.

## Usage

### For Users

1. Click the "Ask Designer AI" bubble in the bottom-right corner
2. Type your question about design, portfolios, or designrden
3. Get instant help with links to documentation when relevant

### For Developers

#### API Endpoints

**Streaming (recommended for chat UI):**
```
POST /api/ai/stream/
```
Response: `text/event-stream` with `data: {"delta": "..."}` chunks.

**Non-streaming:**
```
POST /api/ai/designer-chat/
```

**Request Body (both):**
```json
{
  "message": "How do I upload images?",
  "context_page": "/dashboard/designs/",
  "current_url": "https://designrden.com/dashboard/designs/",
  "language": "en"
}
```

**Response:**
```json
{
  "success": true,
  "response": "Here's how to handle media on designrden:\n\n**Image Guidelines:**\n- Recommended size: 1920x1080px or larger..."
}
```

#### Adding Contextual Help Bars

Add to any template:

```django
{% include "designer_portfolio/includes/contextual_help_bar.html" with help_text="Your custom help text here" %}
```

#### Customizing Responses

Edit `_get_designer_ai_responses()` in `designer_portfolio/views.py` to customize rule-based responses.

#### Customizing System Prompt

Edit `designer_portfolio/ai/chat_assistant.py` to customize the Designer AI system prompt (`DESIGNER_SYSTEM_PROMPT`).

## Documentation Structure

The AI can link to documentation pages. Create documentation views at:

- `/docs/designers/getting-started`
- `/docs/designers/portfolio-layouts`
- `/docs/designers/media-guidelines`
- `/docs/api/overview`
- `/docs/api/auth`
- `/docs/api/portfolios`

## Customization

### Changing Chat Appearance

Edit styles in `designer_portfolio/templates/designer_portfolio/includes/designer_ai_chat.html`

### Adding New Response Categories

Add entries to `_get_designer_ai_responses()` dictionary in `views.py`

### Changing AI Model

Set `OPENAI_MODEL` environment variable (default: `gpt-4o-mini`)

## Troubleshooting

### Chat not appearing
- Check that the template is included in `base.html`
- Verify JavaScript console for errors

### OpenAI not working
- Check `OPENAI_API_KEY` is set correctly
- Verify `openai` library is installed: `pip install openai`
- Check Django logs for error messages
- System will fall back to rule-based responses automatically

### Responses not helpful
- Customize `_get_designer_ai_responses()` for better rule-based responses
- Adjust system prompt in `_get_designer_ai_system_prompt()`
- Ensure OpenAI API key is valid if using AI

## Support

For issues or questions, check the documentation or contact support.

