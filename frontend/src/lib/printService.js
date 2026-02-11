import { requestPrintApk } from "./printService.apk";
import { requestPrintDesktop } from "./printService.desktop";

export async function requestPrint(payload) {
  // O APK é gerado via `vite build --mode android`, então `MODE === 'android'`.
  // Separar aqui evita quebrar o desktop ao evoluir a impressão do tablet.
  if (import.meta.env.MODE === "android") {
    return requestPrintApk(payload);
  }

  return requestPrintDesktop(payload);
}
