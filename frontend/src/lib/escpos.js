function stripDiacritics(input) {
  try {
    return String(input ?? "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "");
  } catch {
    return String(input ?? "");
  }
}

function upper(input) {
  return String(input ?? "").toUpperCase();
}

function wrapWords(text, maxLen) {
  const s = String(text ?? "").replace(/\s+/g, " ").trim();
  if (!s) return [""];
  const max = Math.max(10, Number(maxLen) || 42);
  const words = s.split(" ");
  const lines = [];
  let cur = "";
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (next.length <= max) {
      cur = next;
    } else {
      if (cur) lines.push(cur);
      cur = w;
    }
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [""];
}

function normalizeCaixa(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return "Sem padrão de caixa";
  if (raw === "0" || raw === "0.0" || raw === "0.00") return "Sem padrão de caixa";
  const lower = raw.toLowerCase();
  if (lower === "sem padrão" || lower === "sem padrao") return "Sem padrão de caixa";
  return raw;
}

function formatLabelValueLines(label, value, opts = {}) {
  const width = Math.max(32, Number(opts.width) || 48);
  const labelWidth = Math.max(10, Math.min(22, Number(opts.labelWidth) || 16));

  const l = String(label ?? "").trim();
  const v = String(value ?? "").trim();
  const valueWidth = Math.max(10, width - labelWidth - 2);
  const pad = " ".repeat(labelWidth);

  const firstPrefix = `${l}:`.padEnd(labelWidth);
  const wrapped = wrapWords(v, valueWidth);

  if (!wrapped.length) return [firstPrefix];
  const out = [`${firstPrefix} ${wrapped[0]}`];
  for (const line of wrapped.slice(1)) out.push(`${pad} ${line}`);
  return out;
}

function buildAsciiTableRowLines(label, value, opts = {}) {
  const tableWidth = Math.max(32, Number(opts.tableWidth) || 48);
  const labelColWidth = Math.max(8, Math.min(22, Number(opts.labelColWidth) || 14));
  const valueColWidth = Math.max(10, tableWidth - labelColWidth - 7);

  const l = String(label ?? "").trim();
  const v = String(value ?? "").trim();

  const valueLines = wrapWords(v, valueColWidth);
  const out = [];
  for (let i = 0; i < valueLines.length; i += 1) {
    const labelText = i === 0 ? l : "";
    const left = (labelText.length > labelColWidth
      ? labelText.slice(0, labelColWidth)
      : labelText
    ).padEnd(labelColWidth);
    const right = String(valueLines[i] ?? "").padEnd(valueColWidth);
    out.push(`| ${left} | ${right} |`);
  }
  return { out, labelColWidth, valueColWidth, tableWidth };
}

function buildAsciiTableSeparator(labelColWidth, valueColWidth) {
  return `+${"-".repeat(labelColWidth + 2)}+${"-".repeat(valueColWidth + 2)}+`;
}

function toBytesAscii(text) {
  const cleaned = stripDiacritics(text);
  const bytes = new Uint8Array(cleaned.length);
  for (let i = 0; i < cleaned.length; i += 1) {
    bytes[i] = cleaned.charCodeAt(i) & 0xff;
  }
  return bytes;
}

function concatBytes(chunks) {
  const total = chunks.reduce((sum, c) => sum + (c?.length ?? 0), 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  return out;
}

export function escInit() {
  return new Uint8Array([0x1b, 0x40]);
}

export function escAlign(mode) {
  // 0=left, 1=center, 2=right
  const n = mode === "center" ? 1 : mode === "right" ? 2 : 0;
  return new Uint8Array([0x1b, 0x61, n]);
}

export function escBold(enabled) {
  return new Uint8Array([0x1b, 0x45, enabled ? 1 : 0]);
}

export function escTextLine(text) {
  return concatBytes([toBytesAscii(text), new Uint8Array([0x0a])]);
}

export function escFeed(lines = 1) {
  const n = Math.max(0, Math.min(255, Number(lines) || 0));
  // ESC d n
  return new Uint8Array([0x1b, 0x64, n]);
}

export function escCut() {
  // GS V 66 0 (partial cut). Nem todas as térmicas suportam corte.
  return new Uint8Array([0x1d, 0x56, 0x42, 0x00]);
}

export function escQrCode(data, opts = {}) {
  // QR Code (Model 2) - ESC/POS padrão (GS ( k)
  const text = stripDiacritics(data);
  const size = Math.max(1, Math.min(16, Number(opts.size) || 6));
  const ec = String(opts.ec || "M").toUpperCase();
  // L=48, M=49, Q=50, H=51
  const ecLevel = ec === "L" ? 48 : ec === "Q" ? 50 : ec === "H" ? 51 : 49;

  const store = toBytesAscii(text);
  const storeLen = store.length + 3;
  const pL = storeLen & 0xff;
  const pH = (storeLen >> 8) & 0xff;

  return concatBytes([
    // Select model: GS ( k 4 0 49 65 50 0
    new Uint8Array([0x1d, 0x28, 0x6b, 0x04, 0x00, 0x31, 0x41, 0x32, 0x00]),
    // Set size: GS ( k 3 0 49 67 size
    new Uint8Array([0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x43, size]),
    // Set error correction: GS ( k 3 0 49 69 ecLevel
    new Uint8Array([0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x45, ecLevel]),
    // Store data: GS ( k pL pH 49 80 48 <data>
    new Uint8Array([0x1d, 0x28, 0x6b, pL, pH, 0x31, 0x50, 0x30]),
    store,
    // Print: GS ( k 3 0 49 81 48
    new Uint8Array([0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30]),
  ]);
}

export function buildEscPosTicket(payload) {
  const tab = (payload?.tab || "tingimento").toString().trim().toLowerCase();
  const order = payload?.order || {};

  const ordem = order?.ordem ?? "";
  const artigo = order?.artigo ?? "";
  const cor = order?.cor ?? "";
  const cliente = order?.cliente ?? "";
  const volumeProg = order?.volume ?? "";

  const dataProcesso = payload?.dataProcesso ?? "";
  const dataTingimento = payload?.dataTingimento ?? order?.data ?? "";
  const elasticidadeAcab = payload?.elasticidadeAcab ?? "";
  const larguraAcab = payload?.larguraAcab ?? "";
  const mtf = payload?.mtf ?? "";
  const numeroCortes = payload?.numeroCortes ?? "";
  const operador = payload?.operador ?? "";
  const turno = payload?.turno ?? "";
  const tambores = payload?.tambores ?? "";
  const caixa = normalizeCaixa(payload?.caixa);
  const pesoKg = payload?.pesoKg ?? "";
  const metros = payload?.metros ?? "";
  const obs = payload?.observacoes ?? "";

  // Mesmos títulos usados no desktop (print_cli.py)
  const title = tab === "retingimento" ? "Retingimento - Ficha do Artigo" : "Ficha do Artigo";

  // Mesma ordem/labels do desktop (build_order_data em print_cli.py)
  const rows = [];
  if (tab === "retingimento") {
    rows.push(["Artigo", upper(artigo)]);
    rows.push(["Cor", upper(cor)]);
    rows.push(["Volume Prog", upper(volumeProg)]);
    rows.push(["Data Tingimento", upper(dataTingimento)]);
    rows.push(["Elasticidade Acab", upper(elasticidadeAcab)]);
    rows.push(["Largura Acab", upper(larguraAcab)]);
    rows.push(["Cliente", upper(cliente)]);
    rows.push(["MTF", upper(mtf)]);
    rows.push(["Nº Cortes", upper(numeroCortes)]);
    rows.push(["Operador", upper(operador)]);
    rows.push(["Turno", upper(turno)]);
    rows.push(["Tambores", upper(tambores)]);
    rows.push(["Caixa", upper(caixa)]);
    rows.push(["Peso (KG)", upper(pesoKg)]);
    rows.push(["Metros", upper(metros)]);
    rows.push(["Data Retingimento", upper(dataProcesso)]);
    rows.push(["Observações", upper(obs)]);
  } else {
    rows.push(["Ordem", upper(ordem)]);
    rows.push(["Artigo", upper(artigo)]);
    rows.push(["Cor", upper(cor)]);
    rows.push(["Volume Prog", upper(volumeProg)]);
    rows.push(["Data Tingimento", upper(dataProcesso)]);
    rows.push(["Elasticidade Acab", upper(elasticidadeAcab)]);
    rows.push(["Largura Acab", upper(larguraAcab)]);
    rows.push(["Cliente", upper(cliente)]);
    rows.push(["MTF", upper(mtf)]);
    rows.push(["Nº Cortes", upper(numeroCortes)]);
    rows.push(["Operador", upper(operador)]);
    rows.push(["Turno", upper(turno)]);
    rows.push(["Tambores", upper(tambores)]);
    rows.push(["Caixa", upper(caixa)]);
    rows.push(["Peso (KG)", upper(pesoKg)]);
    rows.push(["Metros", upper(metros)]);
    rows.push(["Observações", upper(obs)]);
  }

  // Mesmo payload do QR do desktop (interface.py)
  const qrObj =
    tab === "retingimento"
      ? {
          VolumeProg: stripDiacritics(upper(volumeProg)),
          Artigo: stripDiacritics(upper(artigo)),
          Cor: stripDiacritics(upper(cor)),
          Tambores: stripDiacritics(upper(tambores)),
          Caixa: stripDiacritics(upper(caixa)),
          Peso: stripDiacritics(upper(pesoKg)),
          Metros: stripDiacritics(upper(metros)),
          DataTingimento: String(dataTingimento ?? ""),
          NumCorte: String(numeroCortes ?? ""),
        }
      : {
          Ordem: stripDiacritics(upper(ordem)),
          VolumeProg: stripDiacritics(upper(volumeProg)),
          Artigo: stripDiacritics(upper(artigo)),
          Cor: stripDiacritics(upper(cor)),
          Tambores: stripDiacritics(upper(tambores)),
          Caixa: stripDiacritics(upper(caixa)),
          Peso: stripDiacritics(upper(pesoKg)),
          Metros: stripDiacritics(upper(metros)),
          DataTingimento: String(dataProcesso ?? ""),
          NumCorte: String(numeroCortes ?? ""),
        };

  const qrData = JSON.stringify(qrObj);

  const lines = [];
  lines.push(escInit());
  lines.push(escAlign("center"));
  lines.push(escBold(true));
  lines.push(escTextLine(title));
  lines.push(escBold(false));
  lines.push(escFeed(1));
  lines.push(escAlign("left"));

  // Layout de tabela (largura em caracteres). 48 costuma ficar bom em 80mm.
  const TABLE_WIDTH = 48;
  // Coluna de label mais larga (evita empurrar a divisória em "Data Tingimento", "Elasticidade Acab", etc.)
  const LABEL_COL_WIDTH = 18;
  const VALUE_COL_WIDTH = Math.max(10, TABLE_WIDTH - LABEL_COL_WIDTH - 7);
  const sepLine = buildAsciiTableSeparator(LABEL_COL_WIDTH, VALUE_COL_WIDTH);

  lines.push(escTextLine(sepLine));

  for (const [label, value] of rows) {
    const l = String(label ?? "").trim();
    const v = String(value ?? "").trim();
    if (!l) continue;

    if (l === "Cor") {
      // Aproxima o comportamento do desktop para ENFESTADO/ENFRALDADO:
      // força quebra antes da palavra especial, mas mantendo o layout em tabela.
      const lower = v.toLowerCase();
      const specials = ["enfestado", "enfraldado"];
      const special = specials.find((t) => lower.includes(t));
      if (special) {
        const idx = lower.indexOf(special);
        const before = v.slice(0, idx).trimEnd();
        const after = v.slice(idx).trimStart();

        const first = buildAsciiTableRowLines(l, before, {
          tableWidth: TABLE_WIDTH,
          labelColWidth: LABEL_COL_WIDTH,
        }).out;
        for (const line of first) lines.push(escTextLine(line));

        const cont = buildAsciiTableRowLines("", after, {
          tableWidth: TABLE_WIDTH,
          labelColWidth: LABEL_COL_WIDTH,
        }).out;
        for (const line of cont) lines.push(escTextLine(line));

        lines.push(escTextLine(sepLine));
        continue;
      }
    }

    const tableLines = buildAsciiTableRowLines(l, v, {
      tableWidth: TABLE_WIDTH,
      labelColWidth: LABEL_COL_WIDTH,
    }).out;
    for (const line of tableLines) lines.push(escTextLine(line));
    lines.push(escTextLine(sepLine));
  }

  lines.push(escFeed(1));
  lines.push(escAlign("center"));
  lines.push(escQrCode(qrData, { size: 6, ec: "M" }));
  lines.push(escFeed(3));
  lines.push(escCut());

  return concatBytes(lines);
}

export function buildEscPosTickets(payload, copies = 1) {
  const nRaw = Number.parseInt(String(copies ?? "1"), 10);
  const n = Number.isFinite(nRaw) && nRaw > 0 ? nRaw : 1;

  const MAX_COPIES = 500;
  if (n > MAX_COPIES) {
    throw new Error(
        `Quantidade de copias muito alta (${n}). ` +
          `Limite atual: ${MAX_COPIES}. Divida em mais de uma impressao.`
    );
  }

  if (n === 1) return buildEscPosTicket(payload);

  const chunks = [];
  for (let i = 0; i < n; i += 1) {
    chunks.push(buildEscPosTicket(payload));
  }
  return concatBytes(chunks);
}
