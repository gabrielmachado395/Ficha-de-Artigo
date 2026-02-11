import { buildEscPosTickets } from "./escpos";
import { sendRawTcp } from "./rawTcpPrinter";

function parseOptionalPort(envValue) {
  const raw = String(envValue ?? "").trim();
  if (!raw) return null;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

function getCandidatePorts(explicitPort) {
  // Elgin/i8 e a maioria das POS em modo RAW usam 9100.
  // Algumas firmwares expõem 9101/9102 (multi-queue) — tentamos em ordem.
  if (explicitPort) return [explicitPort];
  return [9100, 9101, 9102];
}

// Implementação de impressão para APK (Capacitor).
// OBS: impressão direta em Elgin i8 via TCP/9100 (ESC/POS) será implementada aqui,
// mantendo o desktop intacto.
export async function requestPrintApk(payload) {
  const printerHost = String(import.meta.env.VITE_PRINTER_HOST ?? "").trim();
  const explicitPort = parseOptionalPort(import.meta.env.VITE_PRINTER_PORT);
  const candidatePorts = getCandidatePorts(explicitPort);

  const copiesRaw = Number.parseInt(String(payload?.tambores ?? "1"), 10);
  const copies = Number.isFinite(copiesRaw) && copiesRaw > 0 ? copiesRaw : 1;

  // Impressão direta (tablet Wi-Fi -> impressora RJ45) via TCP/9100.
  if (!printerHost) {
    throw new Error(
      "Impressora não configurada. Defina VITE_PRINTER_HOST (ex.: 192.168.0.227) e gere o APK novamente."
    );
  }

  try {
    const bytes = buildEscPosTickets(payload ?? {}, copies);

    const errors = [];
    for (const port of candidatePorts) {
      try {
        await sendRawTcp({ host: printerHost, port, bytes, timeoutMs: 7000 });
        return { ok: true, via: "tcp", host: printerHost, port, copies };
      } catch (e) {
        errors.push({ port, message: e?.message ? String(e.message) : String(e) });
      }
    }

    const portsText = candidatePorts.join(", ");
    const detail = errors.map((x) => `${x.port}: ${x.message}`).join(" | ");
    throw new Error(
      `Falha ao imprimir via TCP (${printerHost}). Portas tentadas: ${portsText}. ` +
        "Confirme qual porta RAW a impressora está usando e se há rota Wi‑Fi→cabo (sem isolamento/VLAN). " +
        `Detalhe: ${detail}`
    );
  } catch (e) {
    const msg = e?.message ? String(e.message) : "erro desconhecido";
    throw new Error(msg);
  }
}
