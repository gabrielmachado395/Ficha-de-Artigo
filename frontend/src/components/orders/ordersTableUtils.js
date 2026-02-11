/**
 * Remove acentos e normaliza o texto para facilitar busca.
 *
 * Ex.: "Falcão" -> "falcao".
 */
export function normalizeForSearch(value) {
  return (value ?? "")
    .toString()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}
