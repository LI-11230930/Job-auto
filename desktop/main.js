const { app, BrowserWindow, Menu, Notification, Tray, ipcMain, nativeImage, shell } = require('electron');
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const http = require('http');
const https = require('https');
const path = require('path');

const HOST = '127.0.0.1';
const PORT = Number(process.env.JOB_AUTO_PORT || 8788);
const CDP_PORT = Number(process.env.JOB_AUTO_CDP_PORT || 9222);
const BASE_URL = `http://${HOST}:${PORT}`;

let mainWindow = null;
let tray = null;
let sidecarProc = null;
let startedSidecarByUs = false;
let isQuitting = false;
let lastNotifiedId = 0;
let notifyTimer = null;
let lastCacheSyncMs = 0;

// Minimal 16x16 PNG (indigo rounded square) encoded as base64 for system tray/window fallback icon
const TRAY_ICON_DATA_URL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAWElEQVR4nGNgoBAwMjAw/GfAAf7//8/AyMiIrh4kB5KDqsNmADaD0NWD5ZDVMxBpAH4NoGkAYjD8Jz8AkQ3C5QZiDAALW0hNMDKgI3oYQM2Q4Q4DAwC8+A4RxR93+wAAAABJRU5ErkJggg==';

function loadAppIcon() {
  const candidates = [
    path.join(__dirname, 'assets', 'icon.png'),
    path.join(__dirname, 'assets', 'icon.ico'),
  ];
  for (const iconPath of candidates) {
    if (fs.existsSync(iconPath)) {
      const img = nativeImage.createFromPath(iconPath);
      if (!img.isEmpty()) return img;
    }
  }
  return nativeImage.createFromDataURL(TRAY_ICON_DATA_URL);
}

function resolveProjectRoot() {
  if (app.isPackaged) {
    // In packaged mode, runtime mutable workspace lives alongside userData or portable dir while code resources live in resourcesPath
    const resDir = process.resourcesPath;
    if (fs.existsSync(path.join(resDir, 'Job-auto'))) {
      return resDir;
    }
  }
  return path.resolve(__dirname, '..');
}

function resolveUserDataRoot() {
  if (process.env.JOB_AUTO_ROOT && process.env.JOB_AUTO_ROOT.trim()) {
    return path.resolve(process.env.JOB_AUTO_ROOT.trim());
  }
  if (!app.isPackaged) {
    return resolveProjectRoot();
  }
  let cursor = path.dirname(process.execPath);
  for (let i = 0; i < 4; i += 1) {
    if (
      fs.existsSync(path.join(cursor, 'Job-auto')) &&
      fs.existsSync(path.join(cursor, '.venv'))
    ) {
      return cursor;
    }
    const parent = path.dirname(cursor);
    if (!parent || parent === cursor) break;
    cursor = parent;
  }
  const portableDir = process.env.PORTABLE_EXECUTABLE_DIR;
  if (portableDir && fs.existsSync(portableDir)) {
    return path.join(portableDir, 'Job-auto-Data');
  }
  return path.join(app.getPath('userData'), 'workspace');
}

function resolvePythonExecutable(projectRoot) {
  const candidates = [
    path.join(projectRoot, '.venv', 'Scripts', 'python.exe'),
    path.join(projectRoot, '.venv', 'bin', 'python'),
    path.join(resolveUserDataRoot(), '.venv', 'Scripts', 'python.exe'),
    path.resolve(process.execPath, '..', '..', '..', '.venv', 'Scripts', 'python.exe'),
    path.resolve(process.execPath, '..', '.venv', 'Scripts', 'python.exe'),
    'python',
  ];
  for (const cand of candidates) {
    if (cand === 'python' || fs.existsSync(cand)) {
      return cand;
    }
  }
  return 'python';
}

function httpRequest(url, method = 'GET', timeoutMs = 1500) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method, timeout: timeoutMs }, (res) => {
      let body = '';
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => resolve({ status: res.statusCode || 0, body }));
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy(new Error('Request timeout'));
    });
    req.end();
  });
}

async function isBackendReady() {
  try {
    const res = await httpRequest(`${BASE_URL}/health`, 'GET', 1200);
    return res.status >= 200 && res.status < 300;
  } catch {
    return false;
  }
}

async function ensureSidecarRunning() {
  if (await isBackendReady()) {
    return true;
  }
  const codeRoot = resolveProjectRoot();
  const dataRoot = resolveUserDataRoot();
  if (app.isPackaged && !fs.existsSync(dataRoot)) {
    fs.mkdirSync(dataRoot, { recursive: true });
  }
  const pythonExe = resolvePythonExecutable(codeRoot);
  const env = {
    ...process.env,
    PYTHONIOENCODING: 'utf-8',
    JOB_AUTO_ROOT: dataRoot,
    JOB_AUTO_CODE_ROOT: codeRoot,
    PYTHONPATH: [path.join(codeRoot, 'Job-auto'), process.env.PYTHONPATH || '']
      .filter(Boolean)
      .join(path.delimiter),
  };
  const args = [
    '-m',
    'job_agent.cli',
    'up',
    '--no-browser',
    '--host',
    HOST,
    '--port',
    String(PORT),
    '--cdp-port',
    String(CDP_PORT),
  ];

  sidecarProc = spawn(pythonExe, args, {
    cwd: app.isPackaged ? codeRoot : codeRoot,
    env,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  startedSidecarByUs = true;

  sidecarProc.stdout.on('data', (d) => process.stdout.write(`[sidecar] ${d}`));
  sidecarProc.stderr.on('data', (d) => process.stderr.write(`[sidecar] ${d}`));
  sidecarProc.on('exit', () => {
    sidecarProc = null;
  });

  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    if (await isBackendReady()) {
      return true;
    }
    await new Promise((r) => setTimeout(r, 350));
  }
  return false;
}

function stopSidecar() {
  if (!startedSidecarByUs || !sidecarProc) {
    return;
  }
  const pid = sidecarProc.pid;
  try {
    if (process.platform === 'win32' && pid) {
      spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true });
    } else {
      sidecarProc.kill('SIGTERM');
    }
  } catch {
    // ignore cleanup failures on shutdown
  }
  sidecarProc = null;
}

function getOptimisticCachePath() {
  return path.join(resolveUserDataRoot(), 'local', 'optimistic_cache.json');
}

function readOptimisticCache() {
  try {
    const p = getOptimisticCachePath();
    if (!fs.existsSync(p)) return { total: 0, items: [] };
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return { total: 0, items: [] };
  }
}

async function syncOptimisticCache() {
  if (Date.now() - lastCacheSyncMs < 45000) return;
  try {
    const res = await httpRequest(`${BASE_URL}/api/packages?decision=all&job_type=all`, 'GET', 1800);
    if (res.status < 200 || res.status >= 300) return;
    const data = JSON.parse(res.body || '{}');
    const pkgs = Array.isArray(data.packages) ? data.packages : [];
    const compact = pkgs.slice(0, 15).map((p) => ({
      package_id: p.package_id,
      company: p.company,
      title: p.title,
      score: p.score,
      job_type: p.job_type,
      decision: p.decision,
    }));
    const cachePath = getOptimisticCachePath();
    fs.mkdirSync(path.dirname(cachePath), { recursive: true });
    fs.writeFileSync(
      cachePath,
      JSON.stringify({ updated_at: new Date().toISOString(), total: pkgs.length, items: compact }),
      'utf-8',
    );
    lastCacheSyncMs = Date.now();
  } catch {
    // non-fatal cache refresh
  }
}

function checkGitHubLatestRelease() {
  return new Promise((resolve) => {
    const req = https.request(
      'https://api.github.com/repos/LI-11230930/Job-auto/releases/latest',
      {
        method: 'GET',
        timeout: 4500,
        headers: { 'User-Agent': 'Job-auto-Desktop-Updater' },
      },
      (res) => {
        let raw = '';
        res.on('data', (c) => { raw += c; });
        res.on('end', () => {
          try {
            const parsed = JSON.parse(raw || '{}');
            resolve({
              ok: res.statusCode === 200,
              current_version: app.getVersion(),
              latest_tag: parsed.tag_name || null,
              html_url: parsed.html_url || 'https://github.com/LI-11230930/Job-auto/releases',
            });
          } catch {
            resolve({ ok: false, current_version: app.getVersion(), error: 'parse_error' });
          }
        });
      },
    );
    req.on('error', (err) => resolve({ ok: false, current_version: app.getVersion(), error: err.message }));
    req.on('timeout', () => {
      req.destroy();
      resolve({ ok: false, current_version: app.getVersion(), error: 'timeout' });
    });
    req.end();
  });
}

function registerIpcHandlers() {
  ipcMain.handle('desktop:get-cached-snapshot', () => readOptimisticCache());
  ipcMain.handle('desktop:open-logs', () => {
    const logsDir = path.join(resolveUserDataRoot(), 'logs');
    fs.mkdirSync(logsDir, { recursive: true });
    return shell.openPath(logsDir);
  });
  ipcMain.handle('desktop:open-offline-progress', () => {
    const progHtml = path.join(resolveUserDataRoot(), 'local', 'progress.html');
    if (fs.existsSync(progHtml) && mainWindow && !mainWindow.isDestroyed()) {
      return mainWindow.loadFile(progHtml);
    }
    return null;
  });
  ipcMain.handle('desktop:retry-sidecar', async () => {
    stopSidecar();
    const ok = await ensureSidecarRunning();
    if (ok && mainWindow && !mainWindow.isDestroyed()) {
      await mainWindow.loadURL(`${BASE_URL}/review`);
    } else if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('sidecar:status', {
        state: 'error',
        message: '重试启动仍未就绪，请打开日志目录排查 Python 环境或端口占用。',
      });
    }
    return ok;
  });
  ipcMain.handle('desktop:check-updates', () => checkGitHubLatestRelease());
}

function buildLoadingHtml(errorMessage = '') {
  const detail = errorMessage
    ? `<p style="color:#b91c1c;">${errorMessage}</p><p>请确认已安装 Python 3.12+ 并运行过依赖初始化（根目录 start.bat）。</p>`
    : '<p>正在启动本地工作台与扩展接收器（127.0.0.1:8788）...</p>';
  return `data:text/html;charset=utf-8,${encodeURIComponent(`
    <!doctype html>
    <html lang="zh-CN">
      <body style="font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f8fafc;color:#0f172a;">
        <div style="text-align:center;max-width:460px;padding:24px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;">
          <h2 style="margin:0 0 10px 0;">Job-auto 智能求职助手 App</h2>
          ${detail}
        </div>
      </body>
    </html>
  `)}`;
}

async function launchCollectorBrowser() {
  try {
    await httpRequest(`${BASE_URL}/api/system/launch-browser`, 'POST', 5000);
  } catch {
    // fallback: ignore if backend busy
  }
}

function showWindow(targetPath = '/review') {
  if (!mainWindow) {
    createWindow(targetPath);
    return;
  }
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
  if (targetPath && mainWindow.webContents.getURL() !== `${BASE_URL}${targetPath}`) {
    mainWindow.loadURL(`${BASE_URL}${targetPath}`);
  }
}

function createTray() {
  if (tray) return;
  const icon = loadAppIcon();
  tray = new Tray(icon);
  tray.setToolTip('Job-auto 智能求职助手 App');
  const menu = Menu.buildFromTemplate([
    { label: '打开 Job-auto App', click: () => showWindow('/review') },
    { label: '查看消息通知中心', click: () => showWindow('/review#inbox') },
    { label: '偏好与账号设置', click: () => showWindow('/review#settings') },
    { label: '打开开发进度看板 (浏览器)', click: () => shell.openExternal(`${BASE_URL}/progress`) },
    { type: 'separator' },
    { label: '启动带插件采集浏览器 (9222)', click: () => launchCollectorBrowser() },
    {
      label: '检查 GitHub Releases 新版',
      click: async () => {
        const info = await checkGitHubLatestRelease();
        if (Notification.isSupported()) {
          new Notification({
            title: 'Job-auto GitHub Release 检查',
            body: info.ok && info.latest_tag
              ? `当前 ${info.current_version}，仓库最新标签：${info.latest_tag}`
              : `当前版本 ${info.current_version}（暂未发布或网络不可达，点击前往 Releases）`,
          }).show();
        }
        if (info.html_url) shell.openExternal(info.html_url);
      },
    },
    { type: 'separator' },
    {
      label: '退出 Job-auto',
      click: () => {
        isQuitting = true;
        if (notifyTimer) clearInterval(notifyTimer);
        stopSidecar();
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(menu);
  tray.on('double-click', () => showWindow('/review'));
}

async function pollNotifications() {
  try {
    const res = await httpRequest(`${BASE_URL}/api/notifications?unread_only=true&limit=5`, 'GET', 2000);
    if (res.status < 200 || res.status >= 300) return;
    const data = JSON.parse(res.body || '{}');
    const unread = Number(data.unread_count || 0);
    if (tray) {
      tray.setToolTip(unread > 0 ? `Job-auto App（${unread} 条新求职提醒）` : 'Job-auto 智能求职助手 App');
    }
    const items = Array.isArray(data.items) ? data.items : [];
    syncOptimisticCache();
    const newest = items[0];
    if (newest && Number(newest.id) > lastNotifiedId) {
      lastNotifiedId = Number(newest.id);
      if (Notification.isSupported()) {
        const toast = new Notification({
          title: newest.title || 'Job-auto 求职提醒',
          body: newest.body || '',
        });
        toast.on('click', () => {
          const tab = newest.action_tab || 'inbox';
          showWindow(`/review#${tab}`);
        });
        toast.show();
      }
    }
  } catch {
    // Ignore transient startup/polling errors
  }
}

async function createWindow(initialPath = '/review') {
  const icon = loadAppIcon();
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 980,
    minHeight: 680,
    title: 'Job-auto 智能求职助手 App',
    icon,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://127.0.0.1:') || url.startsWith('http://localhost:')) {
      return { action: 'allow' };
    }
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting && tray) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  const splashFile = path.join(__dirname, 'splash.html');
  if (fs.existsSync(splashFile)) {
    await mainWindow.loadFile(splashFile);
  } else {
    await mainWindow.loadURL(buildLoadingHtml());
  }
  const ready = await ensureSidecarRunning();
  if (ready && mainWindow && !mainWindow.isDestroyed()) {
    await mainWindow.loadURL(`${BASE_URL}${initialPath}`);
    syncOptimisticCache();
  } else if (mainWindow && !mainWindow.isDestroyed()) {
    if (fs.existsSync(splashFile)) {
      mainWindow.webContents.send('sidecar:status', {
        state: 'error',
        message: '本地 Python 后端未能在 25 秒内就绪。',
      });
    } else {
      await mainWindow.loadURL(buildLoadingHtml('本地 Python 后端未能在 25 秒内就绪。'));
    }
  }
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', async () => {
    await ensureSidecarRunning();
    showWindow('/review');
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.reloadIgnoringCache();
    }
  });

  app.whenReady().then(async () => {
    registerIpcHandlers();
    createTray();
    await createWindow('/review');
    await pollNotifications();
    notifyTimer = setInterval(pollNotifications, 20000);
  });

  app.on('before-quit', () => {
    isQuitting = true;
    if (notifyTimer) clearInterval(notifyTimer);
    stopSidecar();
  });

  app.on('window-all-closed', () => {
    if (isQuitting || process.platform !== 'darwin') {
      if (isQuitting) {
        app.quit();
      }
    }
  });
}
