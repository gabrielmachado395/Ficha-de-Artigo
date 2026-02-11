/* eslint-disable no-console */
const fs = require("node:fs");
const path = require("node:path");
const sharp = require("sharp");

const ROOT = path.resolve(process.cwd());
const ANDROID_RES = path.join(ROOT, "android", "app", "src", "main", "res");
const SRC_LOGO = path.join(ROOT, "public", "logo.png");

function envNumber(name, fallback) {
	const raw = process.env[name];
	if (raw == null || raw === "") return fallback;
	const n = Number(raw);
	return Number.isFinite(n) ? n : fallback;
}

// Proporção máxima do logo dentro do quadrado do ícone.
// Diminua/aumente via env sem mexer no código:
// - ANDROID_ICON_LOGO_RATIO=0.55
const LOGO_MAX_RATIO = Math.max(0.3, Math.min(0.9, envNumber("ANDROID_ICON_LOGO_RATIO", 0.58)));

function ensureDir(dir) {
	fs.mkdirSync(dir, { recursive: true });
}

async function renderLogoToSquarePng({ sizePx, background, outPath }) {
	const logo = sharp(SRC_LOGO);
	const meta = await logo.metadata();
	const w = meta.width || sizePx;
	const h = meta.height || sizePx;

	const maxSide = Math.max(1, Math.round(sizePx * LOGO_MAX_RATIO));
	const scale = Math.min(maxSide / w, maxSide / h);
	const targetW = Math.max(1, Math.round(w * scale));
	const targetH = Math.max(1, Math.round(h * scale));

	const left = Math.max(0, Math.floor((sizePx - targetW) / 2));
	const top = Math.max(0, Math.floor((sizePx - targetH) / 2));

	const logoBuf = await logo
		.resize(targetW, targetH, { fit: "contain" })
		.png()
		.toBuffer();

	ensureDir(path.dirname(outPath));
	await sharp({
		create: {
			width: sizePx,
			height: sizePx,
			channels: 4,
			background,
		},
	})
		.composite([{ input: logoBuf, left, top }])
		.png()
		.toFile(outPath);
}

async function main() {
	if (!fs.existsSync(SRC_LOGO)) {
		throw new Error(`Logo não encontrada em ${SRC_LOGO}`);
	}

	const launcher = {
		mdpi: 48,
		hdpi: 72,
		xhdpi: 96,
		xxhdpi: 144,
		xxxhdpi: 192,
	};

	// Adaptive icon layers (foreground em @mipmap/ic_launcher_foreground)
	const adaptive = {
		mdpi: 108,
		hdpi: 162,
		xhdpi: 216,
		xxhdpi: 324,
		xxxhdpi: 432,
	};

	console.log("Gerando ícones Android...");
	console.log(`- Logo: ${SRC_LOGO}`);
	console.log(`- Proporção (ANDROID_ICON_LOGO_RATIO): ${LOGO_MAX_RATIO}`);

	// Ícones legacy + round (fundo branco)
	for (const [density, sizePx] of Object.entries(launcher)) {
		const dir = path.join(ANDROID_RES, `mipmap-${density}`);
		await renderLogoToSquarePng({
			sizePx,
			background: "#FFFFFFFF",
			outPath: path.join(dir, "ic_launcher.png"),
		});
		await renderLogoToSquarePng({
			sizePx,
			background: "#FFFFFFFF",
			outPath: path.join(dir, "ic_launcher_round.png"),
		});
	}

	// Foreground do adaptive icon (fundo transparente)
	for (const [density, sizePx] of Object.entries(adaptive)) {
		const dir = path.join(ANDROID_RES, `mipmap-${density}`);
		await renderLogoToSquarePng({
			sizePx,
			background: "#00000000",
			outPath: path.join(dir, "ic_launcher_foreground.png"),
		});
	}

	console.log("OK: ícones gerados em android/app/src/main/res/*");
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});

