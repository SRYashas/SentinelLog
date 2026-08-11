/**
 * SentinelLog — Native Desktop App (Electron)
 * =============================================
 * Provides a dedicated native Windows desktop window for SentinelLog.
 *
 * Behavior:
 *   - Auto-launches server & collector background processes using system Node.js
 *   - Closes and kills ALL background processes (server, collector) when window is closed
 *   - Prevents duplicate app instances
 */

const { app, BrowserWindow, Tray, Menu, shell } = require('electron');
const path = require('path');
const http = require('http');
const { spawn, execSync } = require('child_process');
const fs = require('fs');

let mainWindow = null;
let tray = null;
let serverProcess = null;
let collectorProcess = null;

const SERVER_URL = 'http://127.0.0.1:3000';

// Disable hardware acceleration to prevent GPU rendering black screen issues on Windows GPUs
app.disableHardwareAcceleration();

/**
 * Locate system Node.js executable path.
 * Electron's process.execPath is electron.exe, so we find node.exe for child processes.
 */
function findNodePath() {
  try {
    const cmd = process.platform === 'win32' ? 'where node' : 'which node';
    const result = execSync(cmd, { encoding: 'utf8' }).trim();
    const nodePath = result.split(/\r?\n/)[0].trim();
    if (fs.existsSync(nodePath)) return nodePath;
  } catch (e) {
    // Fall through
  }
  if (process.platform === 'win32') {
    const common = path.join(process.env.ProgramFiles || 'C:\\Program Files', 'nodejs', 'node.exe');
    if (fs.existsSync(common)) return common;
  }
  return 'node';
}

/**
 * Force kill child process and tree on Windows
 */
function killChildProcess(proc) {
  if (!proc) return;
  try {
    if (process.platform === 'win32' && proc.pid) {
      execSync(`taskkill /F /T /PID ${proc.pid}`, { stdio: 'ignore' });
    } else {
      proc.kill('SIGKILL');
    }
  } catch (e) {
    // Process already exited
  }
}

/**
 * Kill all spawned background processes
 */
function stopAllBackgroundProcesses() {
  console.log('[Desktop] Stopping all background processes...');
  if (serverProcess) {
    killChildProcess(serverProcess);
    serverProcess = null;
  }
  if (collectorProcess) {
    killChildProcess(collectorProcess);
    collectorProcess = null;
  }
}

/**
 * Check if Express API server is listening on 127.0.0.1:3000
 */
function checkServerHealth() {
  return new Promise((resolve) => {
    const req = http.get(`${SERVER_URL}/api/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Poll until server is ready
 */
async function waitForServer(maxRetries = 15, intervalMs = 1000) {
  for (let i = 0; i < maxRetries; i++) {
    const ok = await checkServerHealth();
    if (ok) {
      console.log(`[Desktop] Server is ready after ${i + 1} check(s).`);
      return true;
    }
    console.log(`[Desktop] Waiting for server... (${i + 1}/${maxRetries})`);
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

app.whenReady().then(async () => {
  app.setPath('userData', path.join(app.getPath('appData'), 'SentinelLogDesktopData'));
  app.setAppUserModelId('com.sentinellog.desktop');

  // Single instance lock
  const gotTheLock = app.requestSingleInstanceLock();
  if (!gotTheLock) {
    console.log('[Desktop] SentinelLog Desktop App is already running.');
    app.quit();
    return;
  }

  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  const NODE_PATH = findNodePath();
  console.log(`[Desktop] Using Node.js at: ${NODE_PATH}`);

  /**
   * Launch server and collector background tasks if not running
   */
  async function ensureBackendRunning() {
    const isServerRunning = await checkServerHealth();
    if (!isServerRunning) {
      console.log('[Desktop] Starting server process...');
      const serverScript = path.join(__dirname, '..', 'server', 'index.js');
      serverProcess = spawn(NODE_PATH, [serverScript], {
        cwd: path.join(__dirname, '..'),
        env: { ...process.env },
        stdio: ['ignore', 'pipe', 'pipe']
      });
      serverProcess.stdout.on('data', (d) => console.log('[Server]', d.toString().trim()));
      serverProcess.stderr.on('data', (d) => console.error('[Server:err]', d.toString().trim()));
      serverProcess.on('exit', (code) => console.log(`[Desktop] Server process exited with code ${code}`));
    } else {
      console.log('[Desktop] Server is already running on 127.0.0.1:3000');
    }

    console.log('[Desktop] Starting collector process...');
    const collectorScript = path.join(__dirname, '..', 'collector', 'index.js');
    collectorProcess = spawn(NODE_PATH, [collectorScript], {
      cwd: path.join(__dirname, '..'),
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe']
    });
    collectorProcess.stdout.on('data', (d) => console.log('[Collector]', d.toString().trim()));
    collectorProcess.stderr.on('data', (d) => console.error('[Collector:err]', d.toString().trim()));
    collectorProcess.on('exit', (code) => console.log(`[Desktop] Collector process exited with code ${code}`));
  }

  /**
   * Create BrowserWindow
   */
  function createMainWindow() {
    mainWindow = new BrowserWindow({
      width: 1280,
      height: 830,
      minWidth: 1000,
      minHeight: 650,
      title: 'SentinelLog — Process Activity Monitor',
      icon: path.join(__dirname, 'icon.ico'),
      backgroundColor: '#030712',
      autoHideMenuBar: true,
      show: true, // Render immediately
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false
      }
    });

    // Forward console logs from web dashboard
    mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
      console.log(`[Renderer Log ${level}] ${message} (${sourceId}:${line})`);
    });

    mainWindow.loadURL(SERVER_URL);

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDesc) => {
      console.error(`[Desktop] Load failed: ${errorDesc} (${errorCode})`);
      mainWindow.loadURL(`data:text/html,
        <html style="background:#030712;color:#f1f5f9;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
          <div style="text-align:center;max-width:500px">
            <h1 style="color:#f97316">⚠ Connection Failed</h1>
            <p>Could not connect to SentinelLog server at <code>${SERVER_URL}</code></p>
            <p style="color:#94a3b8">${errorDesc} (code ${errorCode})</p>
          </div>
        </html>`);
    });

    // When window is closed by user ("X" button), quit the application completely & kill all child processes!
    mainWindow.on('closed', () => {
      mainWindow = null;
      app.quit();
    });

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      if (!url.startsWith(SERVER_URL)) {
        shell.openExternal(url);
        return { action: 'deny' };
      }
      return { action: 'allow' };
    });
  }

  /**
   * Create system tray icon with Exit option
   */
  function createSystemTray() {
    const { nativeImage } = require('electron');
    let iconPath = path.join(__dirname, 'icon.ico');
    if (process.platform !== 'win32') {
      const pngIconPath = path.join(__dirname, 'tray-icon.png');
      if (fs.existsSync(pngIconPath)) iconPath = pngIconPath;
    }

    let trayIcon;
    try {
      trayIcon = nativeImage.createFromPath(iconPath);
      if (trayIcon.isEmpty()) trayIcon = nativeImage.createEmpty();
    } catch (e) {
      trayIcon = nativeImage.createEmpty();
    }

    try {
      tray = new Tray(trayIcon);
      tray.setToolTip('SentinelLog — Activity Monitor');

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
          label: 'Exit SentinelLog',
          click: () => {
            stopAllBackgroundProcesses();
            app.quit();
          }
        }
      ]);

      tray.setContextMenu(contextMenu);
    } catch (err) {
      console.warn('[Desktop] Tray creation warning:', err.message);
    }
  }

  await ensureBackendRunning();
  await waitForServer(15, 1000);

  createMainWindow();
  createSystemTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

// App-wide quit handlers: ensure background server and collector processes are killed
app.on('before-quit', () => {
  stopAllBackgroundProcesses();
});

app.on('will-quit', () => {
  stopAllBackgroundProcesses();
});

app.on('window-all-closed', () => {
  stopAllBackgroundProcesses();
  app.quit();
});