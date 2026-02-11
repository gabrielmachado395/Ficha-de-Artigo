/**
 * Retorna um valor "somente leitura" amigável para a UI.
 * - Se vier vazio/nulo: mostra "-".
 */
export function readOnlyValue(value) {
  const v = (value ?? "").toString();
  return v.trim() ? v : "-";
}

/**
 * Regra de negócio: identifica a cor "PRETO 2" (com variações de espaço).
 */
export function isPreto2(text) {
  const s = String(text ?? "")
    .toUpperCase()
    .replace(/\s+/g, " ")
    .trim();
  return /\bPRETO\s*2\b/.test(s);
}

/**
 * Considera "zero" mesmo com formatos BR ("0", "0,00", "0.000").
 *
 * Usado para validar campos onde 0 não é permitido.
 */
export function isZeroNumeric(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return false;
  const normalized = raw.replace(/\./g, "").replace(/,/g, ".");
  const n = Number(normalized);
  return Number.isFinite(n) && n === 0;
}
