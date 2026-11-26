const { defineConfig } = require("@playwright/test");
const path = require("path");
const fs = require("fs");

const rootDir = path.resolve(__dirname, "..", "..");
const venvPythonWin = path.join(rootDir, ".venv", "Scripts", "python.exe");
const venvPythonUnix = path.join(rootDir, ".venv", "bin", "python");

let pythonCmd = process.env.PYTHON_BIN || "python";
if (!process.env.PYTHON_BIN) {
  if (process.platform === "win32" && fs.existsSync(venvPythonWin)) {
    pythonCmd = `"${venvPythonWin}"`;
  } else if (fs.existsSync(venvPythonUnix)) {
    pythonCmd = `"${venvPythonUnix}"`;
  }
}

const e2eDbPath = path.join(rootDir, "data", "e2e_test.db");

module.exports = defineConfig({
  testDir: __dirname,
  timeout: 30000,
  workers: 2,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://127.0.0.1:8000",
    headless: true,
  },
  webServer: {
    command: `${pythonCmd} -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`,
    cwd: rootDir,
    url: "http://127.0.0.1:8000/health",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
    env: {
      ...process.env,
      DATABASE_PATH: e2eDbPath,
    },
  },
});
