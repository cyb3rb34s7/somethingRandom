# Pluely - Competitor Analysis Document

## Executive Summary

**Pluely** is an open-source alternative to Cluely - a privacy-first AI assistant designed for meetings, interviews, and conversations. It operates as an invisible overlay that helps users in real-time without being detected during screen shares.

| Attribute | Details |
|-----------|---------|
| **Repository** | https://github.com/iamsrikanthnani/pluely |
| **License** | GPL-3.0 |
| **Tech Stack** | Tauri 2 (Rust) + React 19 + TypeScript |
| **App Size** | ~10MB (vs Cluely's ~270MB) |
| **Platforms** | Windows, macOS, Linux |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 19)                     │
│  • Overlay Window (invisible to screen share)                   │
│  • Dashboard (settings, chats, configuration)                   │
│  • Tailwind CSS + Radix UI components                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                      BACKEND (Rust/Tauri 2)                     │
│  • System Audio Capture (WASAPI/CoreAudio/PulseAudio)          │
│  • Screenshot Capture (xcap library)                            │
│  • Voice Activity Detection (VAD)                               │
│  • Secure Storage (keychain)                                    │
│  • SQLite Database                                              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                      EXTERNAL APIs                              │
│  • 11 AI Providers (OpenAI, Claude, Gemini, Groq, etc.)        │
│  • 9 STT Providers (Whisper, Deepgram, ElevenLabs, etc.)       │
│  • Pluely Premium API (licensed users)                         │
└────────────────────────────────────────────────────────────────┘
```

---

## Pages & Navigation

### 1. Main Overlay (`/`)
The primary interface - a translucent floating window that stays on top of all applications.

**Features:**
- Text input for AI queries
- Voice input with real-time visualization
- System audio capture (listens to meeting participants)
- Screenshot capture and analysis
- File attachments (up to 6 files)
- Streaming AI responses with markdown rendering
- "Keep Engaged" mode for continuous conversation

### 2. Dashboard (`/dashboard`)
Central hub for app management.

**Features:**
- License activation panel
- Usage statistics and activity charts
- Token consumption tracking
- Quick access to all settings

### 3. Chats (`/chats`)
Conversation history management.

**Features:**
- All conversations grouped by date
- Search functionality
- Message count indicators
- Click to view full conversation

### 4. View Chat (`/chats/view/:id`)
Detailed conversation viewer.

**Features:**
- Full message history
- Continue conversation option
- Export to markdown
- Delete conversation

### 5. System Prompts (`/system-prompts`)
Custom AI behavior configuration.

**Features:**
- Create/edit/delete system prompts
- AI-powered prompt generation (Premium)
- Quick selection for active prompt
- Default prompts included

### 6. Settings (`/settings`)
General application preferences.

**Features:**
- Theme: Light / Dark / System
- Autostart on system boot
- App icon visibility (hide from dock/taskbar)
- Always on top toggle

### 7. Dev Space (`/dev-space`)
API provider configuration.

**Features:**
- Configure AI providers (API keys, models)
- Configure STT providers
- Add custom providers via curl commands
- Test provider connections

### 8. Shortcuts (`/shortcuts`)
Keyboard shortcut management.

**Features:**
- View all shortcuts
- Customize key bindings
- Cursor style selection (invisible/default/pointer)

### 9. Audio (`/audio`)
Audio device configuration.

**Features:**
- Select input device (microphone)
- Select output device (for system audio capture)
- Sample rate configuration
- VAD sensitivity settings

### 10. Screenshot (`/screenshot`)
Screenshot capture preferences.

**Features:**
- Capture mode: Full screen vs Selection
- Processing mode: Manual vs Auto
- Auto-prompt configuration

### 11. Responses (`/responses`)
AI response customization (Premium feature).

**Features:**
- Response length: Short / Medium / Long / Auto
- Response language: 50+ languages
- Auto-scroll toggle

---

## Core Features

### 1. Invisibility / Stealth Mode

The app is designed to be undetectable during screen shares:

| Feature | Implementation |
|---------|----------------|
| **Content Protected** | `contentProtected: true` in Tauri config - window content not captured by screen recording |
| **Transparent Window** | Translucent overlay blends with desktop |
| **Skip Taskbar** | Window doesn't appear in taskbar/dock |
| **No Window Decorations** | Borderless floating panel |
| **Invisible Cursor** | Optional cursor hiding |

### 2. System Audio Capture (Meeting Listener)

Captures audio from system output (what you hear, not your microphone).

**Technical Details:**
- Windows: WASAPI loopback capture
- macOS: Core Audio via cidre
- Linux: PulseAudio

**Features:**
- Real-time Voice Activity Detection (VAD)
- Automatic speech segmentation
- Noise gate filtering
- Pre-speech buffer (catches word beginnings)
- Configurable sensitivity

**Flow:**
```
System Audio → VAD Detection → Speech Segment →
STT Transcription → AI Processing → Response
```

### 3. Voice Input

Direct microphone input for user queries.

**Features:**
- Push-to-talk or VAD-triggered
- Real-time audio visualization
- Multiple STT provider support
- Automatic silence detection

### 4. Screenshot Capture

Capture screen content for AI analysis.

**Modes:**
1. **Full Screenshot** - Capture entire screen instantly
2. **Selection Mode** - Draw rectangle to capture specific area

**Processing:**
1. **Manual** - Screenshot added as attachment, user writes prompt
2. **Auto** - Screenshot auto-submitted with pre-configured prompt

### 5. AI Chat / Completions

Multi-provider AI integration with streaming responses.

**Supported Providers (11 built-in):**
| Provider | Vision Support | Streaming |
|----------|---------------|-----------|
| OpenAI | Yes | Yes |
| Anthropic Claude | Yes | Yes |
| Google Gemini | Yes | Yes |
| Groq | No | Yes |
| Mistral | Yes | Yes |
| Cohere | Yes | Yes |
| Perplexity | Yes | Yes |
| Grok (X.AI) | Yes | Yes |
| OpenRouter | Yes | Yes |
| Ollama (local) | Yes | Yes |
| Custom | Configurable | Configurable |

**Features:**
- Conversation history with context
- System prompt customization
- File attachments (images, documents)
- Markdown rendering with syntax highlighting
- Copy response to clipboard

### 6. Speech-to-Text (STT)

**Supported Providers (9 built-in):**
1. OpenAI Whisper
2. Groq Whisper
3. ElevenLabs
4. Google Speech-to-Text
5. Deepgram
6. Azure Speech
7. Speechmatics
8. Rev.ai
9. IBM Watson

---

## Keyboard Shortcuts

| Action | macOS | Windows/Linux |
|--------|-------|---------------|
| Toggle Overlay | `Cmd+\` | `Ctrl+\` |
| Open Dashboard | `Cmd+Shift+D` | `Ctrl+Shift+D` |
| Take Screenshot | `Cmd+Shift+S` | `Ctrl+Shift+S` |
| Voice Input | `Cmd+Shift+A` | `Ctrl+Shift+A` |
| System Audio | `Cmd+Shift+M` | `Ctrl+Shift+M` |
| Focus Input | `Cmd+Shift+I` | `Ctrl+Shift+I` |
| Move Window | `Cmd + Arrow Keys` | `Ctrl + Arrow Keys` |

**In-App Shortcuts:**
- `Enter` - Submit message
- `Shift+Enter` - New line
- `Cmd/Ctrl+K` - Toggle "Keep Engaged" mode
- `Arrow Up/Down` - Scroll responses

---

## Premium vs Free Features

### Free Features

| Feature | Availability |
|---------|--------------|
| Main overlay interface | Free |
| Text input & AI chat | Free (with own API keys) |
| Voice input | Free (with own API keys) |
| System audio capture | Free (with own API keys) |
| Screenshot capture | Free |
| Manual screenshot processing | Free |
| 11 AI providers | Free (bring your own keys) |
| 9 STT providers | Free (bring your own keys) |
| Custom providers | Free |
| Conversation history | Free |
| System prompts | Free |
| Theme customization | Free |
| Keyboard shortcuts | Free |
| Invisibility mode | Free |
| Local Ollama support | Free |

### Premium Features (Requires License)

| Feature | Description |
|---------|-------------|
| **Pluely API Access** | Use Pluely's hosted AI models without managing API keys |
| **Response Length Control** | Configure response verbosity (Short/Medium/Long/Auto) |
| **Response Language** | 50+ language options for AI responses |
| **Auto Screenshot Processing** | Screenshots auto-submitted with pre-configured prompts |
| **Activity Tracking** | Token usage analytics and activity charts |
| **AI Prompt Generation** | AI-assisted system prompt creation |
| **Priority Support** | Direct support channel |

### License Activation Flow

```
1. User clicks "Get License" → Opens checkout page
2. User completes purchase → Receives license key via email
3. User enters key in Dashboard → "Pluely API Setup" section
4. System validates key → Activates premium features
5. User selects Pluely model → Ready to use
```

### Pricing Model
- License-based (one-time or subscription - TBD by Pluely)
- Free tier fully functional with own API keys
- Premium adds convenience + managed API access

---

## Technical Specifications

### Performance

| Metric | Value |
|--------|-------|
| App Size | ~10MB |
| Memory Usage | ~50-100MB |
| Startup Time | <2 seconds |
| Audio Latency | <50ms (VAD) |
| Response Latency | Provider-dependent (~200-500ms with Groq) |

### Storage

| Type | Technology | Purpose |
|------|------------|---------|
| Settings | localStorage | Theme, preferences, selected providers |
| Conversations | SQLite | Chat history, messages |
| Secure Data | Keychain | License keys, API credentials |

### Platform Support

| Platform | System Audio | Screenshots | Invisibility |
|----------|--------------|-------------|--------------|
| Windows | WASAPI | xcap | Full |
| macOS | Core Audio | xcap | Full |
| Linux | PulseAudio | xcap | Partial |

---

## Comparison: Pluely vs Cluely

| Feature | Pluely | Cluely |
|---------|--------|--------|
| **Price** | Free + Premium option | $20/month |
| **App Size** | ~10MB | ~270MB |
| **Framework** | Tauri (Rust) | Electron |
| **Open Source** | Yes (GPL-3.0) | No |
| **Screen Capture** | Manual | Continuous OCR |
| **Audio Capture** | System audio + Mic | System audio + Mic |
| **Proactive Suggestions** | No | Yes |
| **Calendar Integration** | No | Yes |
| **Meeting Context** | No | Yes |
| **Response Latency** | ~350-650ms (with Groq) | 5-90 seconds (reported) |
| **Provider Flexibility** | 11+ providers | Proprietary |
| **Local AI Support** | Yes (Ollama) | No |
| **Invisibility** | Full | Full |
| **Platforms** | Windows, macOS, Linux | Windows, macOS |

---

## Strengths & Weaknesses

### Strengths

1. **Open Source** - Full transparency, community contributions
2. **Lightweight** - 27x smaller than Electron alternatives
3. **Provider Flexibility** - Use any AI/STT provider
4. **Privacy First** - Data stays local, no tracking
5. **Low Latency** - Rust backend, efficient processing
6. **Free Core Features** - Fully functional without payment
7. **Cross-Platform** - Works on all major OS

### Weaknesses

1. **No Continuous OCR** - Manual screenshots only
2. **No Proactive Suggestions** - Reactive, not proactive
3. **No Calendar Integration** - No meeting context awareness
4. **Setup Complexity** - Requires API key configuration
5. **No Mobile App** - Desktop only
6. **Limited Premium Value** - Most features free with own keys

---

## Opportunities for Our Product

Based on Pluely's implementation, our product could differentiate by:

1. **Continuous Screen OCR** - Automatically capture and analyze screen content
2. **Proactive AI** - Suggest answers before user asks
3. **Calendar Integration** - Meeting context awareness
4. **Faster Response Times** - Optimize for <500ms total latency
5. **Better Onboarding** - No API key setup required
6. **Mobile Companion** - Quick reference on phone
7. **Team Features** - Shared prompts, collaborative learning
8. **Meeting Transcription** - Full meeting notes generation
9. **CRM Integration** - Auto-log meeting insights
10. **Enterprise Security** - SOC2, HIPAA compliance

---

## Conclusion

Pluely represents a solid open-source foundation for meeting AI assistants. Its strengths lie in privacy, performance, and flexibility. However, it lacks the proactive intelligence and seamless experience that enterprise users expect.

**Key Takeaways:**
- Tauri/Rust is the right technical choice for performance
- System audio capture via WASAPI/CoreAudio is proven
- Invisibility via `contentProtected` works reliably
- Real value comes from proactive features, not just reactive chat
- Sub-1-second latency is achievable with the right provider stack (Groq)

---

*Document generated for internal competitor analysis purposes.*
*Last updated: January 2026*
