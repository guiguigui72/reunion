const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

let mainWindow = null;
let pythonProcess = null;
let backendPort = null;
const PORT_FILE = path.join(os.tmpdir(), 'reunion_port.txt');

function getPythonCommand() {
    return process.platform === 'win32' ? 'python' : 'python3';
}

function startPythonBackend() {
    try { fs.unlinkSync(PORT_FILE); } catch (_) {}

    const backendDir = path.join(__dirname, '..', 'backend');

    pythonProcess = spawn(getPythonCommand(), ['main.py', PORT_FILE], {
        cwd: backendDir,
        stdio: ['pipe', 'pipe', 'pipe'],
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error] ${data.toString().trim()}`);
    });
}

function waitForPort(maxRetries = 30, interval = 1000) {
    return new Promise((resolve, reject) => {
        let retries = 0;
        const check = () => {
            try {
                const port = fs.readFileSync(PORT_FILE, 'utf-8').trim();
                if (port && !isNaN(parseInt(port))) {
                    resolve(parseInt(port));
                    return;
                }
            } catch (_) {}
            retries++;
            if (retries >= maxRetries) {
                reject(new Error('Python backend did not start in time'));
                return;
            }
            setTimeout(check, interval);
        };
        check();
    });
}

async function createWindow() {
    backendPort = await waitForPort();

    mainWindow = new BrowserWindow({
        width: 420,
        height: 720,
        minWidth: 360,
        minHeight: 500,
        title: '重逢',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        backgroundColor: '#faf8f5',
    });

    const isDev = process.argv.includes('--dev');
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
    } else {
        mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'renderer', 'index.html'));
    }
}

ipcMain.handle('get-backend-port', () => backendPort);

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
}).catch((err) => {
    console.error('Failed to start:', err);
    mainWindow = new BrowserWindow({
        width: 420, height: 400,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true, nodeIntegration: false,
        },
        backgroundColor: '#faf8f5',
    });
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(
        '<html><body style="font-family:sans-serif;background:#faf8f5;color:#5c4f3e;text-align:center;padding-top:100px;margin:0"><p style="font-size:16px">无法启动后端服务</p><p style="color:#8c7a6b;font-size:13px">请确认 Python 环境已安装，并执行 pip install -r backend/requirements.txt</p></body></html>'
    ));
    if (pythonProcess) pythonProcess.kill();
});

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill();
    if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
    if (pythonProcess) pythonProcess.kill();
});
