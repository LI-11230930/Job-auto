const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jobAutoDesktop', {
  isDesktopApp: true,
  platform: process.platform,
  electronVersion: process.versions.electron || null,
  getCachedSnapshot: () => ipcRenderer.invoke('desktop:get-cached-snapshot'),
  retrySidecar: () => ipcRenderer.invoke('desktop:retry-sidecar'),
  openLogs: () => ipcRenderer.invoke('desktop:open-logs'),
  openOfflineProgress: () => ipcRenderer.invoke('desktop:open-offline-progress'),
  checkUpdates: () => ipcRenderer.invoke('desktop:check-updates'),
  onSidecarStatus: (handler) => {
    if (typeof handler !== 'function') return;
    ipcRenderer.on('sidecar:status', (_event, payload) => handler(payload));
  },
});
