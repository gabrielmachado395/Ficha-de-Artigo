import { buildEscPosTickets } from "./escpos";

function toBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

export async function requestPrintDesktop(payload) {
  const printerHost = String(import.meta.env.VITE_PRINTER_HOST ?? "").trim();
  const printerPortRaw = String(import.meta.env.VITE_PRINTER_PORT ?? "").trim();
  const explicitPort = printerPortRaw ? Number(printerPortRaw) || null : null;
  const candidatePorts = explicitPort ? [explicitPort] : [9100, 9101, 9102];

  const copiesRaw = Number.parseInt(String(payload?.tambores ?? "1"), 10);
  const copies = Number.isFinite(copiesRaw) && copiesRaw > 0 ? copiesRaw : 1;

  // Desktop (Electron)
  if (typeof window !== "undefined" && window?.electronAPI?.printOrder) {
    // Se estiver configurada impressao via TCP (igual PowerShell), preferir essa rota.
    if (printerHost && typeof window?.electronAPI?.printTcp === "function") {
      const bytes = buildEscPosTickets(payload ?? {}, copies);
      const rawEscPosBase64 = toBase64(bytes);

      let lastError = null;
      for (const port of candidatePorts) {
        try {
          // printTcp escreve ESC/POS bruto; em porta errada falha na conexão sem imprimir.
          // Tentamos 9100/9101/9102 quando VITE_PRINTER_PORT não foi definido.
          // eslint-disable-next-line no-await-in-loop
          return await window.electronAPI.printTcp({
            host: printerHost,
            port,
            rawEscPosBase64,
            timeoutMs: 7000,
            copies,
          });
        } catch (e) {
          lastError = e;
        }
      }
      throw lastError ?? new Error("Falha ao imprimir via TCP");
    }

    // Mantém o MESMO layout do APK: gera ESC/POS e manda para o print_cli.exe imprimir em RAW.
    const bytes = buildEscPosTickets(payload ?? {}, copies);
    const rawEscPosBase64 = toBase64(bytes);
    return window.electronAPI.printOrder({
      ...(payload ?? {}),
      rawEscPosBase64,
      rawEscPosEncoding: "base64",
      copies,
    });
  }

  // Web/PWA não imprime ESC/POS RAW diretamente.
  throw new Error("Impressão disponível apenas no Desktop (Electron) ou no APK (Capacitor).");
}
