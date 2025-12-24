# Malware Analysis Project - Context Document

## Overview
Analyzing a scam APK ("IGL CONNECT GAS.apk") that was sent by someone impersonating a Gas Pipeline Executive. The goal is to reverse engineer the malware, extract C2 (Command & Control) servers, and gather evidence for reporting to authorities.

---

## What We're Analyzing

| Item | Details |
|------|---------|
| **APK Name** | IGL CONNECT GAS.apk |
| **Package** | com.tdqs.brrnnlanhgeh |
| **SHA256** | f6539cd867703d32b1b4ea0a81cc7ba97bb38c2fdb24b606ad7e5cb76db43f86 |
| **Size** | 19.8 MB |
| **Type** | Banking Trojan / RAT (Remote Access Trojan) |
| **Disguised As** | Trojanized "Auto Auto-Rotate" app by Juan García Basilio |

---

## What We've Done

### Phase 1: Static Analysis (Windows)
- [x] Extracted APK contents
- [x] Analyzed AndroidManifest.xml - found dangerous permissions
- [x] Identified malware capabilities:
  - SMS interception
  - Accessibility service abuse
  - Screen capture / Keylogging
  - Overlay attacks (fake login screens)
  - Device admin privileges
- [x] Generated file hashes for reporting
- [x] Created initial malware report

### Phase 2: Kali Linux Setup
- [x] Set up Kali Linux VM with SSH access
- [x] Configured shared folder between Windows and Kali
- [x] Installed analysis tools: jadx, apktool, radare2, Ghidra

### Phase 3: Deep Static Analysis (Kali)
- [x] Decompiled classes.dex with jadx
- [x] Identified native library loader: `plmtzb/c0mzt1.java`
- [x] Analyzed native library `liblqlgelbnp.so` (443KB, ARM64)
- [x] Found 9 JNI entry points, main functions:
  - `attachBaseContext`: 31KB - initialization/decryption
  - `onCreate`: 17KB - activity setup
  - `run`: 50KB - main malware logic

### Phase 4: Encryption Analysis (BREAKTHROUGH!)
- [x] **Cracked the encryption algorithm!**
  - Type: XOR cipher with 8-byte repeating key
  - **XOR Key: `07 26 0c 6f 0f f2 8e 73`**
- [x] Successfully decrypted main payload (CiNHl → 6.2MB DEX file)
- [x] Identified C2 mechanism: Firebase Cloud Messaging (FCM)
- [x] Found OEM security bypass targets (Xiaomi, Huawei, Samsung, OPPO, Vivo)

### Phase 5: Dynamic Analysis Setup
- [x] Expanded Kali VM disk to 60GB
- [x] Created /data partition (38GB) for analysis tools
- [x] Installed Android SDK and emulator
- [x] Installed mitmproxy for traffic interception
- [x] Installed Frida for runtime hooking
- [x] Downloaded Frida server for Android (v17.5.2)
- [x] Started Android emulator in SOFTWARE MODE (`-accel off`)
- [x] Installed malware APK in emulator
- [x] Launched malware with Frida hooks

### Phase 6: Dynamic Analysis Attempt
- [x] Malware detected emulator environment and killed itself
- [x] Identified anti-emulator evasion technique:
  - Process sends `SIGKILL (signal 9)` to itself
  - Detection via `ro.hardware: ranchu`, `ro.build.characteristics: emulator`
  - Serial number: `EMULATOR36X3X10X0`
- [x] Attempted Frida bypass with:
  - Java hooks: `Process.killProcess()`, `System.exit()`
  - Native hooks: `libc.so` `exit()`, `_exit()`, `kill()`
  - Build property spoofing (Samsung Galaxy A52s)
- [x] **BLOCKED**: Native code kills process before Frida can fully attach
- [x] Analyzed native library decryption routines in radare2

---

## Current Status

**SUCCESS!** Anti-emulator bypass achieved! Malware running and analyzed.

---

## Phase 7: SUCCESSFUL Dynamic Analysis (December 21, 2025)

### Anti-Emulator Bypass Method
**Combined approach that worked:**
1. **Patched native library** - Replaced `abort()` PLT at `0x632e0` with ARM64 RET instruction (`c0 03 5f d6`)
2. **Frida Java hooks** - Blocked `Process.killProcess()` and `System.exit()`
3. **Replaced patched library** directly on installed app via root access

### Malware Successfully Running
- Main process: PID 5687 (`com.tdqs.brrnnlanhgeh`)
- Miner process: PID 6139 (`com.tut.lgygjojdmwa`)
- Both processes connected and communicating

---

## CRITICAL C2 INTELLIGENCE EXTRACTED

### Firebase Command & Control Infrastructure

| Component | Firebase Project ID | Purpose |
|-----------|---------------------|---------|
| **Main Malware** | `1:404147416670:android:e4455734535a59e35f8ecf` | Primary C2 |
| **Miner Component** | `1:389276937727:android:5d2302e81e7952858d0bca` | Mining C2 |

### Firebase Cloud Messaging (FCM)
- **FCM Topic**: `topic5` - Miner receives commands via this topic
- **Firebase Installation ID (FID)**: `ft5BqDNvQ2qlnaUqON-68-`

### Telegram Exfiltration (CONFIRMED)
- Functions found: `sendTelegramMessage`, `sendToTelegram`
- Message: `(Missing bot_token or chat_id in Firebase` - **Credentials stored in Firebase DB!**
- Telegram used for data exfiltration to attackers

### Miner Component Details
| Property | Value |
|----------|-------|
| **Package Name** | `com.tut.lgygjojdmwa` |
| **Service** | `com.components.ExternalForegroundConnectorService` |
| **Keep-Alive Service** | `ExternalKeepAliveServiceMediaPlayback` |
| **Keep-Alive Method** | Fake MP3 playback (output8.mp3) |
| **FCM Topic** | `topic5` |

### Extracted Payloads
Located at `/data/data/com.tdqs.brrnnlanhgeh/files/`:
```
├── gFNQOMMbEch (4.6MB) - Decrypted DEX payload (uses BouncyCastle GCM encryption)
├── CZ (2.6MB) - Additional payload
├── arm64-v8a (1.4MB) - Native library
├── ic_google_play (182KB) - Fake Play Store icon
├── images (758KB) - UI elements
├── img_everyone (75KB) - Rating stars for fake reviews
├── rating (23KB) - Fake app rating content
├── original_miner/ - Miner APK source
├── processed_miner/ - Processed miner APK (53MB!)
├── original_user/ - User payload sources
└── processed_user/ - Processed user payload
```

### Malware Behavior Observed
1. **MinerCommunicator** - Connects main malware to miner service
2. **TaskManager** - Manages malware tasks, monitors thermal state
3. **ApkPreprocessor** - Processes and installs hidden APKs
4. **FCMSubscriber** - Subscribes to Firebase topics for commands
5. **Reports Sent**:
   - `app_alive_report` - Heartbeat to C2
   - `thermal_report` - Device temperature monitoring
   - `mining_report` - Cryptocurrency mining stats
   - `waken_up_report` - Device wake events

---

## What's Next

1. **Report to Google/Firebase** - Report both Firebase Project IDs for takedown
2. **Report to Telegram** - If bot token is recovered
3. **Report to Indian authorities** - CERT-In, Cyber Crime Portal
4. **Extract Telegram credentials** - May require hooking at runtime
5. **Capture live C2 traffic** - Set up mitmproxy to intercept Firebase traffic

---

## SSH Connection Information

```bash
# From Windows Command Prompt or PowerShell:
ssh b34s7@192.168.116.132

# SSH Key already configured (passwordless login)
```

| Setting | Value |
|---------|-------|
| **Host** | 192.168.116.132 |
| **Username** | b34s7 |
| **Port** | 22 (default) |
| **Auth** | SSH Key (passwordless) |
| **Sudo** | Passwordless (configured) |

---

## Important Paths

### Windows
```
D:\SCAM DISECTION\                    # Main project folder
D:\SCAM DISECTION\IGL CONNECT GAS.apk # Malware sample
D:\SCAM DISECTION\extracted\          # Extracted APK contents
D:\SCAM DISECTION\MALWARE_ANALYSIS_REPORT.txt  # Full report
```

### Kali Linux
```
/mnt/hgfs/SCAM DISECTION/             # Shared folder (Windows files)
/data/                                 # Analysis partition (38GB)
/data/android-sdk/                     # Android SDK
/data/frida/frida-server              # Frida server for Android
/data/captures/                        # Network capture directory
/data/malware_analysis.sh             # Analysis automation script
/tmp/decrypted_malware/               # Decrypted payload files
~/analysis_output/decompiled/         # Jadx decompiled output
```

---

## Key Findings Summary

### Encryption Key (CRITICAL)
```
XOR Key: 07 26 0c 6f 0f f2 8e 73
```

### Malware Architecture
```
APK
 ├── classes.dex (loader only)
 ├── lib/arm64-v8a/liblqlgelbnp.so (native decryption)
 └── assets/
      ├── CiNHl (6.2MB) → Decrypts to DEX (main payload)
      ├── lvpEHKwLR (4.0MB) → Secondary payload
      ├── LVcTTVzosS (2.6MB) → Secondary payload
      └── ... other encrypted assets
```

### C2 Mechanism
- Firebase Cloud Messaging (FCM) for command & control
- Actual C2 URLs encrypted in payload, loaded at runtime
- Need dynamic analysis to capture live C2 traffic

### Anti-Analysis Techniques Discovered
1. **Anti-Emulator Detection**:
   - Checks `ro.hardware` for "ranchu"/"goldfish"
   - Checks `ro.build.characteristics` for "emulator"
   - Checks serial number for "EMULATOR" prefix
   - Checks for QEMU/goldfish services running
2. **Self-Termination**: Calls `kill(getpid(), SIGKILL)` from native code
3. **Complex Encryption**: Non-repeating XOR keys (each byte uses different key)
4. **Native Code Protection**: Critical logic in compiled ARM64 binary
5. **Target Devices**: `exynos9810` string found (Samsung targeting)

### Trojanized Legitimate App
- Original app: "Auto Auto-Rotate" by Juan García Basilio
- Legitimate source: https://gitlab.com/juanitobananas/auto-auto-rotate
- Privacy policy link embedded: Found in decompiled strings

---

## Commands Reference

### Start Analysis Environment
```bash
# SSH into Kali
ssh b34s7@192.168.116.132

# Set environment
export ANDROID_HOME=/data/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator

# Check KVM support (after enabling nested virt)
kvm-ok

# Start mitmproxy
mitmdump --listen-port 8080 -w /data/captures/traffic.flow &

# Start Android emulator
emulator -avd malware_analysis -no-window -no-audio -http-proxy http://127.0.0.1:8080 &

# Wait for boot
adb wait-for-device

# Install malware (IN EMULATOR ONLY!)
adb install "/mnt/hgfs/SCAM DISECTION/IGL CONNECT GAS.apk"

# Launch malware
adb shell monkey -p com.tdqs.brrnnlanhgeh 1
```

---

## Safety Notes

- **NEVER** run the APK on a real device or outside isolated environment
- All analysis happens inside: Windows → Kali VM → Android Emulator (triple isolation)
- Malware files stay in Kali, execution only in Android emulator
- Network traffic intercepted by mitmproxy before reaching internet

---

## Session Notes (December 21, 2025)

### SUCCESSFUL Dynamic Analysis
1. Started Android emulator in software mode (no KVM)
2. Successfully installed malware APK
3. **Patched native library** to disable `abort()` function
4. **Combined Frida hooks** with patched library
5. **MALWARE RUNNING SUCCESSFULLY!**

### Anti-Emulator Bypass Technique
**What worked:**
1. Found `abort()` PLT at offset `0x632e0` in `liblqlgelbnp.so`
2. Patched with ARM64 RET instruction: `c0 03 5f d6`
3. Pushed patched library to `/data/app/.../lib/arm64/`
4. Combined with Frida hooks for `Process.killProcess()`
5. Malware now runs without self-terminating

### Key Technical Findings
- Frida server 17.5.2 installed and working
- Native library patching + Frida bypass = SUCCESS
- Malware spawns hidden cryptocurrency miner
- Firebase used for C2, Telegram for exfiltration
- Two separate Firebase projects identified

### Files Created on Kali
- `/data/bypass_antiemu.js` - Java-level anti-emulator bypass
- `/data/bypass_native.js` - Native-level anti-emulator bypass
- `/tmp/patch_apk/liblqlgelbnp_patched.so` - Patched native library
- `/data/extracted_payloads/` - All extracted malware payloads
- `/data/extracted_payloads/miner_processed.apk` - 53MB miner APK
- `/data/extracted_payloads/decrypted_payload.dex` - 4.6MB decrypted DEX

### Evidence for Reporting
```
Firebase Project IDs (for Google abuse report):
- 1:404147416670:android:e4455734535a59e35f8ecf (Main malware)
- 1:389276937727:android:5d2302e81e7952858d0bca (Miner)

Malware Packages:
- com.tdqs.brrnnlanhgeh (Main trojan)
- com.tut.lgygjojdmwa (Hidden miner)

XOR Encryption Key: 07 26 0c 6f 0f f2 8e 73
SHA256: f6539cd867703d32b1b4ea0a81cc7ba97bb38c2fdb24b606ad7e5cb76db43f86
```

---

*Last Updated: December 21, 2025 (SUCCESSFUL Dynamic Analysis!)*
