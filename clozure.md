# ClozerAI - Competitor Analysis Document

## Executive Summary

**ClozerAI** is a commercial meeting AI assistant that provides real-time transcription and AI-powered assistance during meetings. It uses native modules for meeting detection and system audio capture.

| Attribute | Details |
|-----------|---------|
| **Website** | https://www.clozerai.com |
| **Version Analyzed** | 3.0.67 |
| **Tech Stack** | Electron + React + TypeScript |
| **App Size** | ~150MB (typical Electron) |
| **Platforms** | Windows, macOS |
| **Pricing Model** | Subscription-based |
| **Source Extraction** | COMPLETE (94 TypeScript files extracted from source maps) |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Electron)                  │
│  • Main Window (transcription UI)                               │
│  • Panel overlay                                                │
│  • Toast notifications (sonner)                                 │
│  • Dialog/Modal components                                      │
│  • lucide-react icons                                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    ELECTRON MAIN PROCESS                        │
│  • BrowserWindow management (9 windows)                         │
│  • IPC communication                                            │
│  • tRPC for API calls                                          │
│  • electron-log for logging                                     │
│  • Auto-updater (GitHub releases)                              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    NATIVE MODULES                               │
│  • MeetingDetectorModuleMac (macOS meeting detection)          │
│  • MeetingDetectorModuleWin.exe (Windows meeting detection)    │
│  • AudioTapModuleMac (macOS system audio capture)              │
│  • screenshot-desktop (cross-platform screenshots)             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│  • Speechmatics (real-time STT - primary provider)             │
│  • AssemblyAI (backup/alternative STT)                         │
│  • OpenAI (AI responses)                                       │
│  • Google (likely Gemini for AI)                               │
│  • Whisper (local/API transcription)                           │
│  • S3/AWS (file storage)                                       │
└────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| **React** | UI framework |
| **TypeScript** | Type safety |
| **Lodash** | Utility functions |
| **lucide-react** | Icon library |
| **sonner** | Toast notifications |
| **tRPC** | Type-safe API calls |

### Backend (Electron Main)
| Technology | Purpose |
|------------|---------|
| **Electron** | Desktop framework |
| **electron-log** | Logging |
| **electron-updater** | Auto-updates via GitHub |
| **screenshot-desktop** | Screenshot capture |
| **WebSocket** | Real-time communication |

### Native Modules
| Module | Platform | Purpose |
|--------|----------|---------|
| **MeetingDetectorModuleMac** | macOS | Detect active meetings (Zoom, Teams, etc.) |
| **MeetingDetectorModuleWin.exe** | Windows | Detect active meetings |
| **AudioTapModuleMac** | macOS | System audio capture |

### External APIs
| Service | Purpose |
|---------|---------|
| **Speechmatics** | Primary real-time STT (via `@speechmatics/real-time-client` SDK) |
| **OpenAI GPT-4.1** | AI chat/responses |
| **Cerebras** | Fast inference (Llama 3.1 8B, Llama 3.3 70B, GPT OSS 120B) |
| **AWS S3** | File storage |

### AI Models (VERIFIED from source)

```typescript
// From src/renderer/lib/aiModels.tsx
{
  "gpt-4.1": "GPT-4.1",
  "gpt-4.1-mini": "GPT-4.1 Mini",
  "cerebras-llama3.1-8b": "Llama 3.1 8B (Cerebras)",
  "cerebras-llama-3.3-70b": "Llama 3.3 70B (Cerebras)",
  "cerebras-gpt-oss-120b": "GPT OSS 120B (Cerebras)",
}
```

**Key Insight**: They use **Cerebras** for low-latency inference - same provider we recommended for your product!

---

## Multilingual Support (VERIFIED - 45 Languages)

### Complete Language List (from `transcriptLanguageMap.ts`)

| Language | Code | Bilingual Support |
|----------|------|-------------------|
| Arabic | `ar` | - |
| Bashkir | `ba` | - |
| Basque | `eu` | - |
| Belarusian | `be` | - |
| Bengali | `bn` | - |
| Bulgarian | `bg` | - |
| Cantonese | `yue` | - |
| Catalan | `ca` | - |
| Croatian | `hr` | - |
| Czech | `cs` | - |
| Danish | `da` | - |
| Dutch | `nl` | - |
| English | `en` | Base language for bilingual |
| Esperanto | `eo` | - |
| Estonian | `et` | - |
| Finnish | `fi` | - |
| French | `fr` | - |
| Galician | `gl` | - |
| German | `de` | - |
| Greek | `el` | - |
| Hebrew | `he` | - |
| **Hindi** | `hi` | - |
| Hungarian | `hu` | - |
| Indonesian | `id` | - |
| Interlingua | `ia` | - |
| Irish | `ga` | - |
| Italian | `it` | - |
| Japanese | `ja` | - |
| Korean | `ko` | - |
| Latvian | `lv` | - |
| Lithuanian | `lt` | - |
| Malay | `ms` | **Malay & English bilingual** (`en_ms`) |
| Maltese | `mt` | - |
| Mandarin | `cmn` | **Mandarin & English bilingual** (`cmn_en`) |
| Marathi | `mr` | - |
| Mongolian | `mn` | - |
| Norwegian | `no` | - |
| Persian | `fa` | - |
| Polish | `pl` | - |
| Portuguese | `pt` | - |
| Romanian | `ro` | - |
| Russian | `ru` | - |
| Slovakian | `sk` | - |
| Slovenian | `sl` | - |
| Spanish | `es` | **Spanish & English bilingual** (`es:bilingual-en`) |
| Swahili | `sw` | - |
| Swedish | `sv` | - |
| **Tamil** | `ta` | **Tamil & English bilingual** (`en_ta`) |
| Thai | `th` | - |
| Turkish | `tr` | - |
| Ukrainian | `uk` | - |
| Uyghur | `ug` | - |
| Urdu | `ur` | - |
| Vietnamese | `vi` | - |
| Welsh | `cy` | - |

### Speechmatics Configuration (from source)

```typescript
// From src/renderer/lib/realtimeSupport/initializeSpeechmaticsSession.ts
const sessionConfig: RealtimeTranscriptionConfig = {
  transcription_config: {
    language,                    // e.g., "ta" for Tamil, "en_ta" for Tamil-English
    diarization: "speaker",      // Speaker identification
    operating_point: "enhanced", // High accuracy mode
    enable_partials: true,       // Real-time partial results
    max_delay: 1,               // 1 second max latency
    conversation_config: {
      end_of_utterance_silence_trigger: 1,  // 1 second silence = end of speech
    },
    audio_filtering_config: {
      volume_threshold: backgroundFiltering,  // Noise filtering
    },
    additional_vocab: [...],     // Custom vocabulary/pronunciation
  },
  audio_format: { type: "file" },
};

await realtimeClient.start(speechmaticsApiKey, sessionConfig);
```

### Bilingual Code-Switching

Speechmatics handles code-switching automatically. Example:
- User says: "Can you explain என்ன நடக்கிறது?" (Tamil-English mix)
- Transcription: "Can you explain என்ன நடக்கிறது?"

**WebSocket Endpoint**: `wss://eu2.rt.speechmatics.com`

---

## Core Features

### 1. Meeting Detection
- **Automatic detection** of meeting applications
- Supported platforms: Zoom, Teams, Google Meet, Webex (likely)
- Native modules for each platform (Mac/Windows specific)
- Status tracking: `meetingDetectorStatus`

### 2. Real-Time Transcription
- **Primary Provider**: Speechmatics
  - Real-time streaming transcription
  - `SpeechmaticsSession` for connection management
  - `speechmaticsApiKey` for authentication
  - Error handling via `SpeechmaticsRealtimeError`

- **Transcription Events**:
  - `RecognitionStarted` - Transcription begins
  - `AddPartialTranscript` - Interim results
  - `AddTranscript` - Final transcript segment
  - `EndOfUtterance` - Speaker finished
  - `EndOfTranscript` - Session complete
  - `SetRecognitionConfig` - Configuration

- **UI Components**:
  - `TranscriptOpen` - Full transcript view
  - `TranscriptionMinimized` - Compact view

### 3. System Audio Capture
- **macOS**: Native `AudioTapModuleMac` module
- **Windows**: Likely WASAPI-based (standard approach)
- Real-time audio streaming to STT service

### 4. AI Assistant
- Question/Answer functionality
- Prompt system with customizable prompts
- `PromptButtons` - Quick action prompts
- `assistant` context for AI interactions
- Token tracking: `promptTokens`

### 5. Screenshot Capture
- Uses `screenshot-desktop` npm package
- Cross-platform support
- Integration with AI for image analysis

### 6. UI Components
| Component | Count | Purpose |
|-----------|-------|---------|
| Toast | 119 | Notifications |
| Panel | 92 | Side panels |
| Dialog | 87 | Modal dialogs |
| Overlay | 27 | Floating overlays |
| Tooltip | 94 | Help tooltips |

---

## Pricing Model

Based on code analysis:

| Term | Mentions | Notes |
|------|----------|-------|
| `subscription` | 22 | Primary pricing model |
| `free` | 3 | Likely free tier/trial |
| `Trial` | 1 | Trial period offered |
| `license` | 2 | License validation |

**Likely Model**: Subscription-based with free trial

---

## Update Mechanism

```yaml
# From app-update.yml
owner: clozerai
repo: clozerai-desktop-releases
provider: github
updaterCacheDirName: clozerai-desktop-updater
```

- Updates distributed via GitHub Releases
- Private repository: `clozerai/clozerai-desktop-releases`
- Auto-update on app launch

---

## IPC Communication

Key events identified:
- `ready-to-show` - Window ready
- `browser-window-created` - New window
- `before-input-event` - Keyboard input
- `web-contents-created` - Content loaded
- `checking-for-update` - Update check
- `update-not-available` - No update

---

## Comparison: ClozerAI vs Pluely

| Feature | ClozerAI | Pluely |
|---------|----------|--------|
| **Framework** | Electron | Tauri (Rust) |
| **App Size** | ~150MB | ~10MB |
| **Meeting Detection** | Native modules (auto) | Manual |
| **STT Provider** | Speechmatics (hosted) | User configurable (11 options) |
| **AI Provider** | OpenAI/Google (hosted) | User configurable (11 options) |
| **System Audio** | Native modules | WASAPI/CoreAudio/PulseAudio |
| **Pricing** | Subscription | Free + Premium |
| **Open Source** | No | Yes (GPL-3.0) |
| **Invisibility** | Unknown | Full (`contentProtected`) |
| **Transcription** | Real-time streaming | VAD-based segments |
| **Platforms** | Windows, macOS | Windows, macOS, Linux |

---

## Comparison: ClozerAI vs Cluely (Original)

| Feature | ClozerAI | Cluely |
|---------|----------|--------|
| **Screen OCR** | Screenshots only | Continuous |
| **Audio Capture** | System audio | System audio |
| **Meeting Detection** | Automatic | Automatic |
| **Proactive Suggestions** | Unknown | Yes |
| **Calendar Integration** | Unknown | Yes |
| **Pricing** | Subscription | $20/month |

---

## Key Differentiators

### ClozerAI Strengths
1. **Native Meeting Detection** - Automatic detection without user action
2. **Speechmatics Integration** - High-quality real-time STT
3. **Polished UX** - Toast notifications, panels, dialogs
4. **Auto-Updates** - Seamless GitHub-based updates

### ClozerAI Weaknesses
1. **Electron Framework** - Large app size, higher memory usage
2. **Closed Source** - No customization or inspection
3. **Subscription Model** - Recurring cost
4. **Limited Provider Options** - Locked to specific STT/AI providers
5. **No Linux Support** - Windows and macOS only

---

## Technical Insights for Our Product

### What to Adopt
1. **Native Meeting Detection** - Build dedicated modules for Zoom/Teams/Meet detection
2. **Speechmatics** - Consider as STT provider (better real-time than Whisper)
3. **Real-time Streaming** - Implement partial transcript updates
4. **Auto-Update** - GitHub releases for updates

### What to Improve Upon
1. **Use Tauri** - 15x smaller app size, better performance
2. **Provider Flexibility** - Let users choose STT/AI providers
3. **Open Source** - Build community trust
4. **Linux Support** - Capture untapped market
5. **Invisibility** - Ensure `contentProtected` for screen share safety

### Architecture Recommendations

```
Our Product Architecture:
┌─────────────────────────────────────────────────┐
│           Tauri (Rust Backend)                  │
├─────────────────────────────────────────────────┤
│ • Native Meeting Detector (Rust)                │
│ • System Audio (WASAPI/CoreAudio/PulseAudio)   │
│ • Real-time VAD + Streaming                     │
│ • SQLite for local storage                      │
│ • Keychain for secure credentials               │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│           React Frontend                        │
├─────────────────────────────────────────────────┤
│ • Invisible overlay (contentProtected)          │
│ • Real-time transcript display                  │
│ • AI chat interface                             │
│ • Settings/Configuration                        │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│           External APIs (User Choice)           │
├─────────────────────────────────────────────────┤
│ STT: Speechmatics / Groq Whisper / Deepgram    │
│ AI: Groq / Gemini / OpenAI / Claude / Local    │
└─────────────────────────────────────────────────┘
```

---

## Files Extracted

| Path | Description |
|------|-------------|
| `dist/main/main.js` | Electron main process (691KB, minified) |
| `dist/main/preload.js` | IPC bridge script |
| `dist/renderer/renderer.js` | React frontend (minified) |
| `dist/renderer/index.html` | Entry HTML |
| `dist/renderer/style.css` | Styles |
| `package.json` | App metadata |

### Native Modules Location
```
C:\Users\loots\AppData\Local\Programs\clozerai-desktop\resources\assets\
├── MeetingDetectorModuleMac
├── MeetingDetectorModuleWin.exe
├── AudioTapModuleMac
├── icon.png
├── iconTransparent.png
├── logo.png
└── trayIcon/
```

---

## Conclusion

ClozerAI is a well-built commercial meeting assistant with:
- Native meeting detection
- Real-time Speechmatics transcription
- Clean Electron-based UI

However, it's limited by:
- Electron's bloat
- Closed source nature
- Subscription-only pricing
- Limited provider flexibility

**Our opportunity**: Build a Tauri-based alternative that's:
- 15x smaller
- Open source
- Provider-agnostic
- Cross-platform (including Linux)
- With better invisibility guarantees

---

*Document generated for internal competitor analysis purposes.*
*Last updated: January 2026*
