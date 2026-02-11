# Ficha de Artigo (Tablet/Web)

Este projeto gera uma PWA (web app instalável) no tablet.

## 1) Configurar a URL do servidor (API)

No tablet, o build precisa saber onde está o backend (o PC/servidor que responde os endpoints como `/consulta/tinturariaDados`).

- Copie `.env.example` para `.env.local`
- Preencha a URL, exemplo:
	- `VITE_API_BASE_URL=http://168.190.90.2:5000`

## 1.1) Configurar IP/porta da impressora (Desktop e APK)

A impressão direta via TCP/9100 usa:

- `VITE_PRINTER_HOST=192.168.0.50`
- `VITE_PRINTER_PORT=9100`

Onde colocar:

- Desktop (Electron): use `.env.local` (baseado em `.env.example`) e gere o instalador.
- APK (Capacitor): edite `.env.android` e gere o APK.

Observação: em modo DEV, o Vite continua usando o proxy `/api` definido no `vite.config.js`.

## 2) Gerar a versão para tablet (PWA)

Comandos:

- `npm run build`

Saída:

- A pasta `dist-web/` (no próprio `frontend/`) contém o app pronto (HTML/CSS/JS + `manifest.webmanifest` + `sw.js`).

## 3) Abrir no tablet

Você precisa servir a pasta `dist-web/` por HTTP/HTTPS (não dá para “abrir o index.html” direto e ter tudo funcionando).

Opção A (mais simples para testar):

- `npm run preview:host`
- No tablet (mesma rede), abra: `http://IP_DO_PC:4173`

Opção A2 (recomendado para tablet na rede, com proxy /api embutido):

- `npm run build`
- `BACKEND_URL=http://168.190.90.2:5000 npm run serve:tablet`
- No tablet (mesma rede), abra: `http://IP_DO_PC:8080`

Opção B (produção):

- Servir `dist-web/` via Nginx/Apache/Caddy (recomendado HTTPS para instalar como PWA)

## 4) Instalar como app (PWA)

No Android (Chrome/Edge):

- Abra o site no tablet
- Menu ⋮ → **Adicionar à tela inicial** (ou **Instalar app** se aparecer)

## Dica (impressão)

No APK (tablet), a impressão é direta via TCP/9100 usando `VITE_PRINTER_HOST`/`VITE_PRINTER_PORT`.

Wi-Fi x cabo (tablet no Wi‑Fi e impressora no cabo):

- Isso só funciona se o Wi‑Fi tiver rota até a rede cabeada (sem isolamento de Wi‑Fi / sem VLAN bloqueando).
- Se não houver rota, o app não consegue alcançar a impressora por IP.

Separação de código:

- Desktop: `src/lib/printService.desktop.js`
- APK: `src/lib/printService.apk.js`

O app importa sempre `src/lib/printService.js`, que decide qual implementação usar.

## Gerar APK (Android) via Capacitor

Use este caminho se você precisa de um arquivo `.apk` para enviar por Bluetooth.

Pré-requisitos (Windows):

- Android Studio instalado (inclui o Java `jbr` e facilita instalar o Android SDK)
- Android SDK instalado pelo SDK Manager

Diagnóstico rápido:

- `npm run android:doctor`

Gerar APK debug:

- `npm run android:apk:debug`

Quando terminar com sucesso, o APK fica em:

- `frontend/android/app/build/outputs/apk/debug/app-debug.apk`
