import { Capacitor, registerPlugin } from "@capacitor/core";

const RawTcpPrinter = registerPlugin("RawTcpPrinter");

function toBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

export async function sendRawTcp({ host, port = 9100, bytes, timeoutMs = 5000 }) {
  if (!Capacitor?.isNativePlatform?.()) {
    throw new Error("sendRawTcp só funciona no APK (Capacitor)");
  }

  const dataBase64 = toBase64(bytes);
  return RawTcpPrinter.send({
    host,
    port: Number(port) || 9100,
    dataBase64,
    timeoutMs: Number(timeoutMs) || 5000,
  });
}

export async function probeRawTcp({ host, port = 9100, timeoutMs = 5000 }) {
  if (!Capacitor?.isNativePlatform?.()) {
    throw new Error("probeRawTcp só funciona no APK (Capacitor)");
  }

  return RawTcpPrinter.probe({
    host,
    port: Number(port) || 9100,
    timeoutMs: Number(timeoutMs) || 5000,
  });
}
