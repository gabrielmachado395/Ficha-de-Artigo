import fs from "node:fs/promises";
import net from "node:net";
import path from "node:path";

function parseDotEnv(text) {
  const out = {};
  const lines = String(text ?? "").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx <= 0) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

async function loadEnvAndroid() {
  const file = path.resolve(process.cwd(), ".env.android");
  try {
    const text = await fs.readFile(file, "utf8");
    return parseDotEnv(text);
  } catch {
    return {};
  }
}

function parsePortsArg(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return [];

  const out = new Set();
  for (const part of raw.split(",")) {
    const p = part.trim();
    if (!p) continue;

    if (p.includes("-")) {
      const [a, b] = p.split("-").map((x) => x.trim());
      const start = Number(a);
      const end = Number(b);
      if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
      const lo = Math.max(1, Math.min(start, end));
      const hi = Math.min(65535, Math.max(start, end));
      for (let port = lo; port <= hi; port += 1) out.add(port);
    } else {
      const port = Number(p);
      if (Number.isFinite(port) && port > 0 && port <= 65535) out.add(port);
    }
  }

  return Array.from(out);
}

function defaultPorts() {
  // Portas comuns para impressoras/POS (nem todas imprimem ESC/POS RAW):
  // - RAW/JetDirect: 9100 (e às vezes 9101/9102/9103...)
  // - LPR/LPD: 515
  // - IPP: 631
  // - Web UI: 80/443/8080 (não imprime RAW)
  const ports = [
    9100, 9101, 9102, 9103, 9104, 9105, 9106, 9107, 9108, 9109,
    515,
    631,
    80,
    443,
    8080,
  ];
  return ports;
}

function usage(exitCode = 0) {
  // eslint-disable-next-line no-console
  console.log(
    [
      "Uso:",
      "  node scripts/printer-port-scan.mjs [host] [--ports 9100,9101,515] [--range 1-2000] [--timeout 250] [--concurrency 200]",
      "",
      "Se host nao for informado, usa VITE_PRINTER_HOST do .env.android.",
      "",
      "Exemplos:",
      "  npm run printer:scan",
      "  npm run printer:scan -- 168.190.30.227",
      "  npm run printer:scan -- 168.190.30.227 --ports 9100,9101,9102,515,631",
      "  npm run printer:scan -- 168.190.30.227 --range 9000-9200 --timeout 200 --concurrency 400",
    ].join("\n")
  );
  process.exit(exitCode);
}

function pickArg(args, name) {
  const idx = args.indexOf(name);
  if (idx === -1) return null;
  return args[idx + 1] ?? null;
}

function tcpProbe(host, port, timeoutMs) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let done = false;

    const finish = (ok) => {
      if (done) return;
      done = true;
      try {
        socket.destroy();
      } catch {
        // ignore
      }
      resolve(ok);
    };

    socket.setTimeout(timeoutMs, () => finish(false));
    socket.once("error", () => finish(false));
    socket.connect(port, host, () => finish(true));
  });
}

async function scanPorts({ host, ports, timeoutMs, concurrency }) {
  const open = [];
  const queue = ports.slice();

  let inFlight = 0;

  return await new Promise((resolve) => {
    const pump = () => {
      while (inFlight < concurrency && queue.length > 0) {
        const port = queue.shift();
        inFlight += 1;
        tcpProbe(host, port, timeoutMs)
          .then((ok) => {
            if (ok) open.push(port);
          })
          .finally(() => {
            inFlight -= 1;
            if (queue.length === 0 && inFlight === 0) resolve(open.sort((a, b) => a - b));
            else pump();
          });
      }
      if (queue.length === 0 && inFlight === 0) resolve(open.sort((a, b) => a - b));
    };

    pump();
  });
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes("-h") || args.includes("--help")) usage(0);

  const envAndroid = await loadEnvAndroid();
  const host = String(args[0] ?? process.env.VITE_PRINTER_HOST ?? envAndroid.VITE_PRINTER_HOST ?? "").trim();
  if (!host) {
    // eslint-disable-next-line no-console
    console.error("Host nao informado. Configure VITE_PRINTER_HOST no .env.android ou passe como argumento.");
    usage(2);
  }

  const timeoutMs = Math.max(50, Number(pickArg(args, "--timeout") ?? "250") || 250);
  const concurrency = Math.max(1, Math.min(2000, Number(pickArg(args, "--concurrency") ?? "200") || 200));

  const portsArg = pickArg(args, "--ports");
  const rangeArg = pickArg(args, "--range");

  let ports = [];
  if (portsArg) ports = ports.concat(parsePortsArg(portsArg));
  if (rangeArg) ports = ports.concat(parsePortsArg(rangeArg));

  if (ports.length === 0) ports = defaultPorts();
  ports = Array.from(new Set(ports)).filter((p) => p >= 1 && p <= 65535);

  // eslint-disable-next-line no-console
  console.log(`Scan TCP em ${host} (ports=${ports.length}, timeout=${timeoutMs}ms, conc=${concurrency})...`);

  const open = await scanPorts({ host, ports, timeoutMs, concurrency });

  if (open.length === 0) {
    // eslint-disable-next-line no-console
    console.log("Nenhuma porta respondeu no scan.");
    process.exit(1);
  }

  // eslint-disable-next-line no-console
  console.log("Portas abertas:", open.join(", "));

  // Dica prática
  const rawCandidates = open.filter((p) => String(p).startsWith("910"));
  if (rawCandidates.length > 0) {
    // eslint-disable-next-line no-console
    console.log(
      "Dica: tente primeiro uma porta 910x (RAW). Ex.: VITE_PRINTER_PORT=" + rawCandidates[0]
    );
  } else if (open.includes(515)) {
    // eslint-disable-next-line no-console
    console.log("Dica: 515 (LPR) aberta. ESC/POS RAW via socket pode nao funcionar; precisaria falar LPR.");
  } else if (open.includes(631)) {
    // eslint-disable-next-line no-console
    console.log("Dica: 631 (IPP) aberta. ESC/POS RAW via socket pode nao funcionar; precisaria falar IPP.");
  }
}

main().catch((e) => {
  const msg = e?.message ? String(e.message) : String(e);
  // eslint-disable-next-line no-console
  console.error("FALHA:", msg);
  process.exit(2);
});
