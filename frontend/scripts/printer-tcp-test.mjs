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

function escposTestPayload() {
  const lines = [
    "TESTE TCP/9100",
    `Data: ${new Date().toLocaleString("pt-BR")}`,
    "Se voce leu isso, a rede OK.",
    "",
  ];

  const text = lines.join("\n") + "\n\n\n";
  const encoder = new TextEncoder();

  // ESC @ (init)
  const init = new Uint8Array([0x1b, 0x40]);
  // Text
  const body = encoder.encode(text);
  // GS V 1 (partial cut) — nem toda impressora corta; se não suportar, só ignora.
  const cut = new Uint8Array([0x1d, 0x56, 0x01]);

  const bytes = new Uint8Array(init.length + body.length + cut.length);
  bytes.set(init, 0);
  bytes.set(body, init.length);
  bytes.set(cut, init.length + body.length);
  return bytes;
}

function usage(exitCode = 0) {
  // eslint-disable-next-line no-console
  console.log(
    [
      "Uso:",
      "  node scripts/printer-tcp-test.mjs [host] [port]",
      "",
      "Se host/port nao forem informados, usa VITE_PRINTER_HOST/VITE_PRINTER_PORT do .env.android.",
      "",
      "Exemplos:",
      "  node scripts/printer-tcp-test.mjs 168.190.30.227 9100",
      "  npm run printer:test",
    ].join("\n")
  );
  process.exit(exitCode);
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes("-h") || args.includes("--help")) usage(0);

  const envAndroid = await loadEnvAndroid();

  const host = String(args[0] ?? process.env.VITE_PRINTER_HOST ?? envAndroid.VITE_PRINTER_HOST ?? "").trim();
  const portRaw = String(args[1] ?? process.env.VITE_PRINTER_PORT ?? envAndroid.VITE_PRINTER_PORT ?? "").trim();
  const explicitPort = portRaw ? Number(portRaw) || null : null;
  const candidatePorts = explicitPort ? [explicitPort] : [9100, 9101, 9102];

  if (!host) {
    // eslint-disable-next-line no-console
    console.error(
      "Host nao informado. Passe como argumento ou configure VITE_PRINTER_HOST no .env.android."
    );
    usage(2);
  }

  const timeoutMs = 4000;
  const bytes = escposTestPayload();

  let lastErr = null;
  for (const port of candidatePorts) {
    // eslint-disable-next-line no-console
    console.log(`Conectando em ${host}:${port} (timeout ${timeoutMs}ms)...`);

    try {
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve, reject) => {
        const socket = new net.Socket();
        let finished = false;

        const doneOk = () => {
          if (finished) return;
          finished = true;
          try {
            socket.destroy();
          } catch {
            // ignore
          }
          resolve();
        };

        const doneErr = (err) => {
          if (finished) return;
          finished = true;
          try {
            socket.destroy();
          } catch {
            // ignore
          }
          reject(err);
        };

        socket.setTimeout(timeoutMs, () => doneErr(new Error("timeout")));
        socket.once("error", doneErr);

        socket.connect(port, host, () => {
          try {
            socket.write(bytes, (err) => {
              if (err) return doneErr(err);
              setTimeout(doneOk, 250);
            });
          } catch (e) {
            doneErr(e);
          }
        });
      });

      // eslint-disable-next-line no-console
      console.log("OK: enviado para a impressora.");
      return;
    } catch (e) {
      lastErr = e;
      // eslint-disable-next-line no-console
      console.log(`Falhou na porta ${port}: ${e?.message ? String(e.message) : String(e)}`);
    }
  }

  throw lastErr ?? new Error("Falha ao conectar em todas as portas tentadas");

  // eslint-disable-next-line no-console
  console.log(
    "(Se nao imprimiu, a impressora pode estar recusando RAW/9100 ou usando outra porta/mode.)"
  );
}

main().catch((e) => {
  const msg = e?.message ? String(e.message) : String(e);
  // eslint-disable-next-line no-console
  console.error("FALHA:", msg);
  process.exit(1);
});
