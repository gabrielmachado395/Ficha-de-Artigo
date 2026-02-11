const fs = require("fs");
const path = require("path");
const pngToIco = require("png-to-ico");
const sharp = require("sharp");

async function main() {
  const projectRoot = path.join(__dirname, "..");
  const srcPng = path.join(projectRoot, "public", "logo.png");
  const outDir = path.join(projectRoot, "build");
  const outIco = path.join(outDir, "icon.ico");
  const outIcoElectron = path.join(projectRoot, "electron", "icon.ico");

  if (!fs.existsSync(srcPng)) {
    throw new Error(`Logo não encontrado em: ${srcPng}`);
  }

  fs.mkdirSync(outDir, { recursive: true });

  // Gera um .ico multi-resolução (melhor para o Windows) e
  // tenta remover bordas transparentes para evitar ícone "miúdo".
  const sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256];

  const base = sharp(srcPng)
    .ensureAlpha()
    .trim()
    .resize(1024, 1024, {
      fit: "contain",
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    });

  const pngBuffers = await Promise.all(
    sizes.map((s) =>
      base
        .clone()
        .resize(s, s, {
          fit: "contain",
          background: { r: 0, g: 0, b: 0, alpha: 0 },
        })
        .png()
        .toBuffer()
    )
  );

  const buf = await pngToIco(pngBuffers);
  fs.writeFileSync(outIco, buf);
  fs.writeFileSync(outIcoElectron, buf);

  console.log(`OK: icon.ico gerado em ${outIco}`);
  console.log(`OK: icon.ico gerado em ${outIcoElectron}`);
}

main().catch((e) => {
  console.error(String(e?.stack || e));
  process.exit(1);
});
