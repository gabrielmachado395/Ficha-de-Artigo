const fs = require("fs");
const path = require("path");

function copyFile(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function copyDirRecursive(srcDir, destDir) {
  fs.mkdirSync(destDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const src = path.join(srcDir, entry.name);
    const dest = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      copyDirRecursive(src, dest);
    } else if (entry.isFile()) {
      copyFile(src, dest);
    }
  }
}

function rmIfExists(p) {
  if (!fs.existsSync(p)) return;
  fs.rmSync(p, { recursive: true, force: true });
}

function main() {
  const srcOneDirExe = path.resolve(
    __dirname,
    "..",
    "..",
    "print",
    "dist",
    "print_cli",
    "print_cli.exe"
  );
  const srcOneDirFolder = path.dirname(srcOneDirExe);
  const srcOneFileExe = path.resolve(
    __dirname,
    "..",
    "..",
    "print",
    "dist",
    "print_cli.exe"
  );

  const destBinDir = path.resolve(__dirname, "..", "print-bin");
  const destOneDirFolder = path.join(destBinDir, "print_cli");
  const destOneFileExe = path.join(destBinDir, "print_cli.exe");

  // Preferir onedir (muito mais rápido para iniciar em cada impressão)
  if (fs.existsSync(srcOneDirExe)) {
    rmIfExists(destOneFileExe);
    rmIfExists(destOneDirFolder);
    copyDirRecursive(srcOneDirFolder, destOneDirFolder);
    console.log(`OK: print_cli (onedir) pronto em ${destOneDirFolder}`);
    return;
  }

  // Fallback: onefile
  const src = fs.existsSync(srcOneFileExe)
    ? srcOneFileExe
    : path.resolve(__dirname, "..", "print-bin", "print_cli.exe");

  if (!fs.existsSync(src)) {
    console.error(`print_cli.exe não encontrado em: ${src}`);
    process.exit(1);
  }

  rmIfExists(destOneDirFolder);
  copyFile(src, destOneFileExe);
  console.log(`OK: print_cli.exe (onefile) pronto em ${destOneFileExe}`);
}

main();
