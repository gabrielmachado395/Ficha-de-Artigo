const { app, BrowserWindow, shell, dialog, Menu, ipcMain } = require("electron");
const { spawn } = require("child_process");
const net = require("net");
const fs = require("fs");
const path = require("path");
const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

function getBackendUrl() {
  return process.env.BACKEND_URL || "http://168.190.90.2:5000";
}

function startLocalServer() {
  return new Promise((resolve, reject) => {
    const serverApp = express();

    // Proxy /api -> backend (remove /api do path)
    serverApp.use(
      "/api",
      createProxyMiddleware({
        target: getBackendUrl(),
        changeOrigin: true,
        ws: true,
        logLevel: "warn",
        pathRewrite: { "^/api": "" },
      })
    );

    // Serve o build do React
    const distPath = app.isPackaged
      ? path.join(process.resourcesPath, "dist-web")
      : path.join(__dirname, "..", "dist-web");

    serverApp.use(express.static(distPath));
    serverApp.get(/.*/, (req, res) => {
        res.sendFile(path.join(distPath, "index.html"));
        });

    const server = serverApp.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ server, port });
    });

    server.on("error", reject);
  });
}

function getPrintCliPath() {
  const base = app.isPackaged ? process.resourcesPath : path.join(__dirname, "..");
  const candidates = [
    // onedir (preferido: inicia muito mais rápido)
    path.join(base, "print-bin", "print_cli", "print_cli.exe"),
    // onefile (fallback)
    path.join(base, "print-bin", "print_cli.exe"),
  ];

  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  // Retorna o primeiro candidato para manter mensagem de erro útil
  return candidates[0];
}

function runPrintCli(payload) {
  return new Promise((resolve, reject) => {
    const exePath = getPrintCliPath();
    if (!fs.existsSync(exePath)) {
      reject(new Error(`print_cli.exe não encontrado em: ${exePath}`));
      return;
    }

    const child = spawn(exePath, [], {
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      cwd: path.dirname(exePath),
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (d) => {
      stdout += d.toString("utf8");
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString("utf8");
    });

    child.on("error", (err) => reject(err));
    child.on("close", (code) => {
      if (code === 0) {
        try {
          const text = String(stdout || "").trim();
          resolve(text ? JSON.parse(text) : { ok: true });
        } catch {
          resolve({ ok: true });
        }
        return;
      }

      const msg = String(stderr || "").trim();
      reject(new Error(msg || `Falha ao imprimir (exit ${code})`));
    });

    try {
      child.stdin.write(JSON.stringify(payload ?? {}), "utf8");
      child.stdin.end();
    } catch (err) {
      reject(err);
    }
  });
}

function parseIpv4(host) {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(String(host || "").trim());
  if (!m) return null;
  const parts = m.slice(1).map((n) => Number(n));
  if (parts.some((p) => !Number.isFinite(p) || p < 0 || p > 255)) return null;
  return parts;
}

function isPrivateIpv4(parts) {
  const [a, b] = parts;
  if (a === 10) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 169 && b === 254) return true; // link-local
  return false;
}

function splitHostPort(rawHost, fallbackPort) {
  const s = String(rawHost || "").trim();
  if (!s) return { host: "", port: fallbackPort };

  // Permite colar um URL completo (ex: http://192.168.0.50:9100)
  if (s.includes("://")) {
    try {
      const u = new URL(s);
      const p = u.port ? Number(u.port) : fallbackPort;
      return { host: u.hostname, port: Number.isFinite(p) && p ? p : fallbackPort };
    } catch {
      // cai para parser simples
    }
  }

  // Permite colar host:porta (ex: 192.168.0.50:9100)
  const m = /^([^\s:]+):(\d{1,5})$/.exec(s);
  if (m) {
    const p = Number(m[2]);
    return { host: m[1], port: Number.isFinite(p) && p ? p : fallbackPort };
  }

  return { host: s, port: fallbackPort };
}

function validateTcpTarget(host, port) {
  const split = splitHostPort(host, Number(port) || 9100);
  const parts = parseIpv4(split.host);
  if (!parts) {
    throw new Error(
      "Host deve ser um IPv4 valido (ex: 192.168.0.50). " +
        "Dica: nao inclua espacos; voce pode colar 'IP:PORTA' (ex: 192.168.0.50:9100)."
    );
  }
  const p = Number(split.port);
  if (!Number.isFinite(p) || p <= 0 || p > 65535) {
    throw new Error("Porta TCP invalida");
  }
  return { host: parts.join("."), port: p };
}

function sendRawTcpEscPos({ host, port = 9100, rawEscPosBase64, timeoutMs = 7000 }) {
  const target = validateTcpTarget(host, port);
  const b64 = String(rawEscPosBase64 || "");
  if (!b64.trim()) {
    return Promise.reject(new Error("rawEscPosBase64 obrigatorio"));
  }

  const buf = Buffer.from(b64, "base64");
  if (!buf.length) {
    return Promise.reject(new Error("rawEscPosBase64 vazio ou invalido"));
  }

  const MAX_BYTES = 4 * 1024 * 1024;
  if (buf.length > MAX_BYTES) {
    return Promise.reject(new Error("Payload grande demais"));
  }

  const t = Math.max(1000, Math.min(60000, Number(timeoutMs) || 7000));

  return new Promise((resolve, reject) => {
    const socket = new net.Socket();
    let done = false;

    const finish = (err) => {
      if (done) return;
      done = true;
      try {
        socket.destroy();
      } catch {
        // ignore
      }
      if (err) reject(err);
      else resolve({ ok: true, via: "tcp", host: target.host, port: target.port });
    };

    socket.setTimeout(t);
    socket.on("timeout", () => finish(new Error("Timeout ao conectar/enviar (TCP)")));
    socket.on("error", (err) => finish(err));
    socket.on("close", () => {
      if (!done) finish();
    });

    socket.connect(target.port, target.host, () => {
      socket.write(buf, (err) => {
        if (err) return finish(err);
        socket.end();
      });
    });
  });
}

function createWindow(loadUrl) {
  // No Windows, usar .ico multi-res melhora bastante o ícone na barra da janela.
  // Mantemos um fallback para logo.png caso o .ico ainda não exista (ex: primeiro run em dev).
  const icoPath = path.join(__dirname, "icon.ico");
  const pngFallback = app.isPackaged
    ? path.join(process.resourcesPath, "dist-web", "logo.png")
    : path.join(__dirname, "..", "public", "logo.png");
  const iconPath = require("fs").existsSync(icoPath) ? icoPath : pngFallback;

  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    backgroundColor: "#0b1b33",
    title: "Ficha de Artigo",
    icon: iconPath,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  // Remove a toolbar/menubar padrão
  win.setMenuBarVisibility(false);
  win.setAutoHideMenuBar(true);
  win.removeMenu();

  // Evita que o título da página sobrescreva o título da janela
  win.on("page-title-updated", (e) => {
    e.preventDefault();
  });
  win.setTitle("Ficha de Artigo");

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.loadURL(loadUrl);
}

app.whenReady().then(async () => {
  const isDev = process.argv.includes("--dev");

  ipcMain.handle("print:order", async (_ev, payload) => {
    return runPrintCli(payload);
  });

  ipcMain.handle("print:tcp", async (_ev, payload) => {
    if (payload == null || typeof payload !== "object") {
      throw new Error("Payload invalido");
    }

    const host = String(payload.host || "").trim();
    const port = Number(payload.port || 9100) || 9100;
    const rawEscPosBase64 = String(payload.rawEscPosBase64 || "");
    const timeoutMs = Number(payload.timeoutMs || 7000) || 7000;

    // Limite simples para evitar DoS acidental.
    const size = Buffer.byteLength(rawEscPosBase64, "utf8");
    if (size > 6 * 1024 * 1024) {
      throw new Error("Payload grande demais");
    }

    return sendRawTcpEscPos({ host, port, rawEscPosBase64, timeoutMs });
  });

  // Garante que não exista menu de aplicação (Windows)
  Menu.setApplicationMenu(null);

  // Nome do app (exibição em alguns locais)
  app.setName("Ficha de Artigo");

  if (isDev) {
    createWindow("http://localhost:5173");
    return;
  }

  try {
    const { port } = await startLocalServer();
    createWindow(`http://127.0.0.1:${port}`);
  } catch (err) {
    dialog.showErrorBox("Falha ao iniciar", String(err?.stack || err));
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});