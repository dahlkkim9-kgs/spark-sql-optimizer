const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow = null;
let backendProcess = null;

function getBackendPath() {
    // 获取后端可执行文件路径
    if (app.isPackaged) {
        // 打包后的路径 - 使用 embedded Python 后端 EXE
        return path.join(process.resourcesPath, 'backend', 'spark-sql-backend.exe');
    } else {
        // 开发环境 - 返回 backend 目录，使用 -m 模块方式运行
        return path.join(__dirname, '../backend');
    }
}

function getBackendExecutable() {
    if (app.isPackaged) {
        // 打包后直接返回 EXE 路径
        return getBackendPath();
    } else {
        // 开发环境使用 Python
        return process.env.PYTHON_PATH || 'python';
    }
}

function getBackendArgs() {
    if (app.isPackaged) {
        // EXE 不需要参数
        return [];
    } else {
        // 使用 -m 模块方式运行 api.main
        // 需要切换到 backend 目录，然后运行 python -m api.main
        return ['-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8889'];
    }
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    // 加载前端 - 无论打包与否，前端都在 app.asar 内部的相对路径
    const indexPath = path.join(__dirname, '../frontend/build/index.html');

    mainWindow.loadFile(indexPath);

    // 打开 DevTools 用于调试格式化问题
    mainWindow.webContents.openDevTools();

    // 监听加载失败
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
        console.error('Failed to load:', errorCode, errorDescription, validatedURL);
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
        if (backendProcess) {
            backendProcess.kill();
        }
        app.quit();
    });
}

function startBackend() {
    const backendExe = getBackendExecutable();
    const backendArgs = getBackendArgs();

    console.log('Starting backend...');
    console.log('Backend executable:', backendExe);
    console.log('Backend args:', backendArgs);

    // 检查后端目录/文件是否存在
    const pathToCheck = app.isPackaged ? backendExe : getBackendPath();
    if (!fs.existsSync(pathToCheck)) {
        console.error('Backend path not found:', pathToCheck);
        // 显示错误对话框
        if (mainWindow) {
            mainWindow.webContents.executeJavaScript(`
                alert('后端程序未找到，请确保应用正确安装。');
            `);
        }
        return;
    }

    // 设置 spawn 选项
    const spawnOptions = {
        windowsHide: true  // 隐藏后端控制台窗口
    };

    // 在开发环境下，需要设置工作目录为 backend 目录
    if (!app.isPackaged) {
        spawnOptions.cwd = getBackendPath();
    }

    backendProcess = spawn(backendExe, backendArgs, spawnOptions);

    backendProcess.stdout.on('data', (data) => {
        console.log('Backend:', data.toString());
    });

    backendProcess.stderr.on('data', (data) => {
        console.error('Backend Error:', data.toString());
    });

    backendProcess.on('error', (error) => {
        console.error('Failed to start backend:', error);
        if (mainWindow) {
            mainWindow.webContents.executeJavaScript(`
                console.error('后端启动失败:', ${JSON.stringify(error.message)});
            `);
        }
    });

    backendProcess.on('exit', (code) => {
        console.log(`Backend process exited with code ${code}`);
        if (code !== 0 && mainWindow) {
            mainWindow.webContents.executeJavaScript(`
                console.error('后端进程异常退出，退出代码: ${code}');
            `);
        }
    });
}

app.whenReady().then(() => {
    createWindow();

    // 等待窗口加载完成后再启动后端
    setTimeout(() => {
        startBackend();
    }, 2000);
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});
