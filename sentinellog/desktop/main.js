/**
 * SentinelLog — Native Desktop App (Electron)
 * =============================================
 * Provides a dedicated native Windows desktop window for SentinelLog
 * so users don't need to open a web browser.
 *
 * Features:
 *   - Sleek dark window titlebar
 *   - Minimizes to System Tray (near Windows clock)
 *   - Auto-launches server & collector if not already running
 *   - Single instance lock (prevents multiple duplicate windows)
 */

const { app, BrowserWindow, Tray, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

// Set a dedicated user data path to avoid Chromium lock file conflicts
app.setPath('userData', path.join(app.getPath('appData'), 'SentinelLogDesktopData'));
app.setAppUserModelId('com.sentinellog.desktop');

let mainWindow = null;
let tray = null;
let serverProcess = null;
let collectorProcess = null;

const SERVER_URL = 'http://127.0.0.1:3000';

// Enforce single app instance gracefully
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  console.log('[Desktop] SentinelLog Desktop App is already running. Focus brought to existing window.');
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

/**
 * Check if the Express API server is already responding at http://127.0.0.1:3000
 */
function checkServerHealth() {
  return new Promise((resolve) => {
    const req = http.get(`${SERVER_URL}/api/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Start background Server and Collector processes if not already active
 */
async function ensureBackendRunning() {
  const isServerRunning = await checkServerHealth();
  if (!isServerRunning) {
    console.log('[Desktop] Starting background server process...');
    const serverScript = path.join(__dirname, '..', 'server', 'index.js');
    serverProcess = spawn(process.execPath, [serverScript], {
      cwd: path.join(__dirname, '..'),
      env: process.env,
      stdio: 'ignore'
    });
  } else {
    console.log('[Desktop] Server is already running on 127.0.0.1:3000');
  }

  // Also launch collector if not running as a Windows service
  console.log('[Desktop] Launching collector process...');
  const collectorScript = path.join(__dirname, '..', 'collector', 'index.js');
  collectorProcess = spawn(process.execPath, [collectorScript], {
    cwd: path.join(__dirname, '..'),
    env: process.env,
    stdio: 'ignore'
  });
}

/**
 * Create the main desktop window
 */
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 830,
    minWidth: 1000,
    minHeight: 650,
    title: 'SentinelLog — Process Activity Monitor',
    icon: path.join(__dirname, 'icon.ico'),
    backgroundColor: '#030712', // slate-950
    autoHideMenuBar: true,
    show: false, // Don't show until ready
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  // Load the web app
  mainWindow.loadURL(SERVER_URL);

  // Smooth fade-in when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle external links (open in default browser, not in app window)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(SERVER_URL)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  // Close to tray instead of quitting app
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
    return false;
  });
}

/**
 * Create system tray icon and context menu
 */
function createSystemTray() {
  const { nativeImage } = require('electron');
  const iconPath = path.join(__dirname, 'icon.ico');

  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(iconPath);
    if (trayIcon.isEmpty()) {
      trayIcon = nativeImage.createEmpty();
    }
  } catch (e) {
    trayIcon = nativeImage.createEmpty();
  }

  try {
    tray = new Tray(trayIcon);
    tray.setToolTip('SentinelLog — Windows Activity Monitor');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Open SentinelLog Window',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        }
      },
      { type: 'separator' },
      {
        label: 'Open in Browser (http://127.0.0.1:3000)',
        click: () => shell.openExternal(SERVER_URL)
      },
      { type: 'separator' },
      {
        label: 'Exit SentinelLog',
        click: () => {
          app.isQuitting = true;
          if (serverProcess) serverProcess.kill();
          if (collectorProcess) collectorProcess.kill();
          app.quit();
        }
      }
    ]);

    tray.setContextMenu(contextMenu);

    // Double click tray icon toggles window visibility
    tray.on('double-click', () => {
      if (mainWindow) {
        if (mainWindow.isVisible()) {
          mainWindow.hide();
        } else {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    });
  } catch (err) {
    console.warn('[Desktop] System Tray could not be created:', err.message);
  }
}

// App lifecycle
app.whenReady().then(async () => {
  await ensureBackendRunning();

  // Wait 1.5 seconds for server startup if launched fresh
  setTimeout(() => {
    createMainWindow();
    createSystemTray();
  }, 1500);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (serverProcess) serverProcess.kill();
  if (collectorProcess) collectorProcess.kill();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Keep app running in tray on Windows
  }
});
