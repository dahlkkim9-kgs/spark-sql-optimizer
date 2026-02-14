/**
 * Electron预加载脚本
 * 在渲染进程中暴露安全的API
 */
const { contextBridge, ipcRenderer } = require('electron');

// 暴露API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
    getVersions: () => ({
        node: process.versions.node,
        chrome: process.versions.chrome,
        electron: process.versions.electron
    }),

    getPlatform: () => process.platform,

    // 文件操作API
    readFile: (filePath) => {
        return ipcRenderer.invoke('read-file', filePath);
    },

    writeFile: (filePath, content) => {
        return ipcRenderer.invoke('write-file', filePath, content);
    },

    selectFile: () => {
        return ipcRenderer.invoke('select-file');
    },

    selectFolder: () => {
        return ipcRenderer.invoke('select-folder');
    }
});

console.log('Preload script loaded');
