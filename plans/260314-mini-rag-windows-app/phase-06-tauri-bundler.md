# Phase 06: Tauri Bundler & Installer

**Context:** [plan.md](./plan.md) · [Tauri sidecar research](./research/researcher-01-tauri-sidecar.md)

## Overview

- **Priority:** P1
- **Status:** Complete
- **Effort:** 1h
- **Description:** Configure Tauri NSIS installer: app icon, shortcut, installer metadata. Run final `npm run tauri build` to produce .exe installer.

## Key Insights

- Tauri generates NSIS installer by default on Windows
- `identifier` field in tauri.conf.json is used for registry + uninstall
- Icons needed: 32x32.png, 128x128.png, icon.ico (for NSIS), 256x256.png
- `shortcutName` sets what appears in Start Menu
- sidecar binary MUST be in `src-tauri/binaries/` BEFORE running `tauri build`
- Final installer location: `src-tauri/target/release/bundle/nsis/`

## Requirements

- NSIS .exe installer (not MSI for simpler distribution)
- Start Menu shortcut: "Mini RAG"
- Desktop shortcut: optional (configure in NSIS)
- App icon in taskbar + title bar
- Uninstall via Windows Add/Remove Programs

## Related Code Files

- Modify: `src-tauri/tauri.conf.json` (finalize all fields)
- Create: `src-tauri/icons/` (app icons)
- Modify: `package.json` (build scripts)

## Implementation Steps

### Step 1: Generate app icons

```bash
# Option A: Use Tauri CLI icon generator (from a 1024x1024 PNG)
npm run tauri icon -- ./app-icon-1024.png
# Generates all required icon sizes in src-tauri/icons/

# Option B: Manually create minimal icons
# Minimum required for NSIS:
# - src-tauri/icons/icon.ico (Windows ICO with multiple sizes)
# - src-tauri/icons/icon.png (128x128 PNG)
```

### Step 2: Final tauri.conf.json

```json
{
  "build": {
    "devUrl": "http://localhost:1420",
    "frontendDist": "../dist",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [
      {
        "title": "Mini RAG",
        "width": 1200,
        "height": 800,
        "minWidth": 800,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": ["nsis"],
    "identifier": "com.minirag.app",
    "publisher": "Mini RAG",
    "copyright": "2026",
    "category": "Utility",
    "shortDescription": "Local PDF semantic search",
    "longDescription": "Upload PDFs and search them semantically using local AI embeddings. No internet required.",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.ico"
    ],
    "externalBin": [
      "binaries/api-server"
    ],
    "windows": {
      "nsis": {
        "displayLanguageSelector": false,
        "shortcutName": "Mini RAG",
        "createDesktopShortcut": true,
        "createStartMenuShortcut": true,
        "installerIcon": "icons/icon.ico"
      }
    }
  }
}
```

### Step 3: package.json build scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "tauri": "tauri",
    "build:sidecar": "cd backend && build.bat",
    "build:all": "scripts\\build-all.bat"
  }
}
```

### Step 4: Build the installer

```bash
# Ensure sidecar binary is in src-tauri/binaries/ (from phase 5)
ls src-tauri/binaries/
# Should show: api-server-x86_64-pc-windows-msvc.exe

# Build everything
npm run tauri build

# Output:
# src-tauri/target/release/bundle/nsis/mini-rag_0.1.0_x64-setup.exe
```

### Step 5: Test the installer

```
1. Run: mini-rag_0.1.0_x64-setup.exe
2. Install to default location (C:\Program Files\Mini RAG\)
3. Click Start Menu "Mini RAG" shortcut
4. App opens → loading screen → main UI
5. Upload a PDF → search → verify results
6. Close app → verify api-server.exe not in Task Manager
7. Uninstall via Settings → Apps → Mini RAG
```

## Todo List

- [x] Generate app icons (1024x1024 PNG → `npm run tauri icon`)
- [x] Finalize `src-tauri/tauri.conf.json` with all bundle fields
- [x] Verify `src-tauri/binaries/api-server-x86_64-pc-windows-msvc.exe` exists
- [x] Run `npm run tauri build`
- [x] Locate installer in `src-tauri/target/release/bundle/nsis/`
- [x] Test install → open → use → close → uninstall flow

## Success Criteria

- `mini-rag_0.1.0_x64-setup.exe` exists and is ~200-350MB
- Installation completes without errors
- Start Menu shortcut launches the app
- App fully functional after install (upload + search)
- Uninstall removes app cleanly

## Risk Assessment

- **Icon missing**: `tauri build` fails if icons don't exist → generate with `tauri icon` command
- **Sidecar binary missing**: Build fails silently — verify binaries/ dir before build
- **NSIS not installed**: Tauri CLI installs NSIS automatically on Windows

## Next Steps

→ Phase 7: End-to-end testing
