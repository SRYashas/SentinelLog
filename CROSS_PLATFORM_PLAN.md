# SentinelLog Cross-Platform Compatibility Plan

## Overview
This document outlines the steps needed to make SentinelLog compatible with Windows, macOS, and Linux platforms.

## Current Limitations
SentinelLog is currently designed specifically for Windows with the following platform-dependent components:

1. **Collector Service**:
   - Uses `node-windows` for Windows service management
   - Uses `wevtutil` for reading Windows Event Logs (Sysmon, PowerShell)
   - Relies on Windows-specific event IDs and XML formats

2. **Desktop Application**:
   - Electron-based with Windows-specific build configuration
   - Icons and resources may be Windows-specific

3. **Python Application**:
   - PyInstaller build script focused on Windows .exe creation
   - May have Windows-specific dependencies

## Required Changes for Cross-Platform Support

### 1. Abstract Platform-Specific Functionality
Create abstraction layers for:
- Service/daemon management
- System event/log monitoring
- File system operations (paths, permissions)
- Process information gathering

### 2. Replace Windows-Specific Dependencies

#### Collector Service
Replace:
- `node-windows` → Cross-platform solution (e.g., `node-langu`, custom scripts)
- `wevtutil`/event log reading → Platform-specific implementations:
  - Windows: Continue using `wevtutil` or WMI
  - macOS: Use Apple System Log (ASL) or unified logging
  - Linux: Use auditd, journald, or procfs

#### Desktop Application
- Electron is already cross-platform, but ensure:
  - No Windows-specific APIs in renderer/main processes
  - Use `path` module for file operations
  - Test on all target platforms

#### Python Application
- PyInstaller supports cross-platform builds
- Ensure dependencies are available on all platforms
- Test GUI framework (PyQt6) on target platforms

### 3. Update Build and Packaging Scripts

#### Electron Builder Configuration
Modify `sentinellog/desktop/package.json` build section:
```json
"build": {
  "appId": "com.sentinellog.desktop",
  "productName": "SentinelLog",
  "directories": {
    "output": "../dist-exe"
  },
  "files": [
    "**/*",
    "../server/**/*",
    "../collector/**/*",
    "../dashboard/dist/**/*"
  ],
  "win": {
    "icon": "build/icon.ico",
    "target": ["portable"]
  },
  "mac": {
    "icon": "build/icon.icns",
    "target": ["dmg", "zip"]
  },
  "linux": {
    "icon": "build/icon.png",
    "target": ["AppImage", "deb", "rpm"]
  }
}
```

#### PyInstaller Script
Update `sentinellog/pyapp/build_exe.py` to detect platform and adjust parameters:
- Windows: `--onefile --windowed`
- macOS: `--onefile --windowed` (with .app bundle option)
- Linux: `--onefile` (console or GTK based on GUI needs)

### 4. Platform Detection and Configuration
Add runtime platform detection to conditionally load appropriate modules:
```javascript
const platform = require('os').platform();
// Windows: win32, macOS: darwin, linux: linux
```

### 5. Documentation and Deployment
- Update documentation to reflect cross-platform capabilities
- Provide platform-specific installation instructions
- Create separate release assets for each platform

## Implementation Approach

### Phase 1: Core Abstraction Layer
Create interfaces for:
- `ServiceManager` (install, start, stop, uninstall services)
- `EventCollector` (platform-specific event gathering)
- `SystemInfo` (cross-platform system information)

### Phase 2: Platform Implementations
Implement each interface for:
- Windows (maintain current functionality)
- macOS
- Linux

### Phase 3: Build System Updates
Modify packaging scripts to generate platform-appropriate distributables.

### Phase 4: Testing
- Automated testing on each platform
- Manual verification of core functionality
- Performance and compatibility testing

## Files to Modify

1. `sentinellog/collector/index.js` - Abstract Windows-specific calls
2. `sentinellog/collector/eventLogReader.js` - Create platform-specific readers
3. `sentinellog/collector/install-service.js` - Replace or abstract service management
4. `sentinellog/desktop/package.json` - Update build configuration for all platforms
5. `sentinellog/pyapp/build_exe.py` - Enhance for cross-platform support
6. Create new platform-specific modules in collector/

## Estimated Effort
- Core abstraction: 1-2 weeks
- Platform implementations: 2-3 weeks per platform
- Build system updates: 3-5 days
- Testing and QA: 1-2 weeks

## Risks and Mitigations
1. **Loss of Windows-specific features**: Maintain Windows implementation as reference
2. **Increased complexity**: Use dependency injection and clear interfaces
3. **Testing overhead**: Implement automated cross-platform testing early
4. **Dependency availability**: Vet cross-platform alternatives thoroughly

## Conclusion
Making SentinelLog truly cross-platform requires significant architectural changes to abstract away Windows-specific dependencies. However, with Electron and PyInstaller already being cross-platform tools, much of the foundation is in place. The primary work involves replacing the Windows-specific collector service components with platform-appropriate alternatives while maintaining the same functionality and user experience across all target platforms.