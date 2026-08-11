# SentinelLog

Cross-platform offline Windows Process & Console Activity Monitor that can be built for Windows, macOS, and Linux.

## Features

- Monitors Windows process and console activity
- Offline operation with local data storage
- System tray integration
- Cross-platform desktop application built with Electron
- Bundles all necessary files (server, collector, dashboard) into a single distributable

## Project Structure

- `sentinellog/desktop` - Main Electron application
- `sentinellog/server` - Express API server
- `sentinellog/collector` - Data collection service
- `sentinellog/dashboard` - React-based web dashboard

## Building for All Platforms

### Prerequisites

- Node.js (v18 or higher)
- npm

### Build Commands

```bash
# Install dependencies
npm install

# Build for all platforms (Windows, macOS, Linux)
npm run build-all
```

### Platform-Specific Builds

```bash
# Build for Windows only
npm run exe

# Build dashboard only
npm --prefix sentinellog/dashboard run build

# Start development mode
npm start
```

### Output

Built applications will be available in the `sentinellog/dist-exe` directory:

- Windows: `.exe`, `.zip`, and installer files
- macOS: `.dmg` and `.zip` files
- Linux: `.AppImage`, `.deb`, `.rpm`, and `.zip` files

## Running the Application

After building, you can run the platform-specific executable directly from the `dist-exe` folder.

## Development

```bash
# Start all services in development mode
npm start

# Start individual services
npm run server    # Start API server
npm run collector # Start data collector
npm run app       # Start Electron desktop app
```

## License

MIT
