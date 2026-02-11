export const PESO_LABEL = "Peso (KG)";
export const TAMBORES_LABEL = "Tambores";

export function todayBR() {
  return new Date().toLocaleDateString("pt-BR");
}

// === Regras portadas do interface.py ===

export function maskDateBR(input) {
  // Replica mascara_data(): mantém dd/mm/aaaa e valida data; se inválida com 10 chars, volta para dd/mm/
  const digits = String(input ?? "").replace(/\D/g, "");
  let out = digits;

  if (out.length > 2) out = `${out.slice(0, 2)}/${out.slice(2)}`;
  if (out.length > 5) out = `${out.slice(0, 5)}/${out.slice(5)}`;
  out = out.slice(0, 10);

  if (out.length === 10) {
    const [dd, mm, yyyy] = out.split("/").map((v) => Number(v));
    const dt = new Date(yyyy, (mm || 1) - 1, dd || 1);
    const valid =
      yyyy >= 1900 &&
      yyyy <= 3000 &&
      dt.getFullYear() === yyyy &&
      dt.getMonth() === (mm || 1) - 1 &&
      dt.getDate() === (dd || 1);

    if (!valid) out = out.slice(0, 6);
  }

  return out;
}

export function formatDecimalInput(value) {
  // Replica formatar_decimal_input(): permite ponto/vírgula, mantém PONTO no display e limita 3 casas
  let text = String(value ?? "").replace(/,/g, ".");

  let cleaned = "";
  let dotFound = false;
  for (const ch of text) {
    if (ch >= "0" && ch <= "9") cleaned += ch;
    else if (ch === "." && !dotFound) {
      cleaned += ch;
      dotFound = true;
    }
  }

  if (cleaned.includes(".")) {
    const parts = cleaned.split(".");
    if (parts.length > 2) {
      cleaned = parts[0] + "." + parts.slice(1).join("");
    }

    const [a, b = ""] = cleaned.split(".");
    if (b.length > 3) cleaned = a + "." + b.slice(0, 3);
  }

  return cleaned;
}

export function formatPesoOutput(value) {
  // Replica formatar_peso_output(): força 3 casas decimais com ponto; inválido vira 0.000
  const text = String(value ?? "");
  const num = Number(text.replace(/,/g, "."));
  if (!Number.isFinite(num)) return "0.000";
  return num.toFixed(3);
}

export function formatIntegerInput(value) {
  // Replica formatar_inteiro(): só dígitos; remove zeros à esquerda; limita a 2 dígitos; vazio permitido
  let text = String(value ?? "").replace(/\D/g, "");
  if (!text) return "";

  if (text.startsWith("0") && text.length > 1) {
    text = text.replace(/^0+/, "");
    if (!text) text = "0";
  }

  if (text.length > 2) text = text.slice(0, 2);
  return text;
}

export function calcularMetros(pesoStr, gramaturaValor) {
  // Replica calcular_metros(): (peso*1000)/gramatura; retorna inteiro com separador de milhar '.'
  let peso = Number(String(pesoStr ?? "").replace(/,/g, "."));
  if (!Number.isFinite(peso)) peso = 0.0;

  let gramatura = Number(String(gramaturaValor ?? "").replace(/,/g, "."));
  if (!Number.isFinite(gramatura)) gramatura = 0.0;

  if (peso > 0 && gramatura > 0) {
    try {
      const metrosFloat = (peso * 1000) / gramatura;
      const metrosInt = Math.trunc(metrosFloat);
      // Em Python: f"{metros_int:,}" -> usa ',' para milhar, depois replace(',', '.')
      return metrosInt.toLocaleString("en-US").replace(/,/g, ".");
    } catch {
      return "0";
    }
  }

  return "0.00";
}

export function calcularDistribuicao(metrosStr, caixaStr) {
  // Replica calcular_distribuicao(): float(metros) / int(caixa) com 2 casas
  let metros = Number(String(metrosStr ?? "").replace(/,/g, "."));
  if (!Number.isFinite(metros)) metros = 0.0;

  const caixa = parseInt(String(caixaStr ?? "").trim(), 10);
  const caixaNum = Number.isFinite(caixa) ? caixa : 0;

  if (metros > 0 && caixaNum > 0) {
    return (metros / caixaNum).toFixed(2);
  }

  return "0.00";
}

export function getTurnoSP(date = new Date()) {
  // Replica get_turno() em America/Sao_Paulo
  const dtf = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    hour12: false,
  });
  const hour = Number(dtf.format(date));

  if (hour >= 6 && hour < 14) return "A";
  if (hour >= 14 && hour < 22) return "B";
  return "C";
}

export function dividirArtigoCor(textoCompleto) {
  // Aproxima a função dividir_artigo_cor do interface.py
  const raw = String(textoCompleto ?? "").trim().replace(/\s+/g, " ");
  if (!raw) return { artigo: "", cor: "" };

  const lower = raw.toLowerCase();

  // Padrão 1: (.*?) (\d*(mm|cm)) (.+)
  const matchMedida = raw.match(/^(.*?)\s*(\d*\s*(?:mm|cm))\s+(.+)$/i);
  if (matchMedida) {
    return {
      artigo: `${matchMedida[1].trim()} ${matchMedida[2].trim()}`.trim(),
      cor: matchMedida[3].trim(),
    };
  }

  // Regra específica (pedido): quando houver "SEMI ACABADO", isso faz parte da Cor.
  // Caso exista um token "N" antes, ele marca o fim do artigo.
  // Ex: "DAYANE 13 UP N BORR. BCA SEMI ACABADO" =>
  // artigo: "DAYANE 13 UP N" | cor: "BORR. BCA SEMI ACABADO"
  {
    const words = raw.split(" ").filter(Boolean);
    const upperWords = words.map((w) => w.toUpperCase());
    const semiIndex = (() => {
      for (let i = 0; i < upperWords.length; i++) {
        if (upperWords[i] === "SEMIACABADO") return i;
        if (i < upperWords.length - 1 && upperWords[i] === "SEMI" && upperWords[i + 1] === "ACABADO") return i;
      }
      return -1;
    })();

    if (semiIndex !== -1) {
      // Caso especial: token do tipo "30/LUPO".
      // Regra: número fica no Artigo, e "/LUPO" (com o resto, incluindo SEMI ACABADO) fica na Cor.
      // Ex: "PRIME 30/LUPO SEMI ACABADO" => artigo: "PRIME 30" | cor: "/LUPO SEMI ACABADO"
      for (let i = 0; i < upperWords.length; i++) {
        const tok = upperWords[i];
        if (!tok.includes("/")) continue;
        const m = tok.match(/^(\d+)\/(LUPO)$/i);
        if (!m) continue;

        const num = m[1];
        const suffix = m[2].toUpperCase();

        const artigoPrefix = words.slice(0, i).join(" ").trim();
        const artigo = `${artigoPrefix} ${num}`.trim();
        const cor = [`/${suffix}`, ...words.slice(i + 1)].join(" ").trim();
        return { artigo, cor };
      }

      let nIndex = -1;
      for (let i = semiIndex - 1; i >= 0; i--) {
        if (upperWords[i] === "N") {
          nIndex = i;
          break;
        }
      }

      if (nIndex !== -1 && nIndex < words.length - 1) {
        return {
          artigo: words.slice(0, nIndex + 1).join(" ").trim(),
          cor: words.slice(nIndex + 1).join(" ").trim(),
        };
      }

      // Sem "N": inclui marcadores comuns de cor/variação imediatamente antes do "SEMI ACABADO".
      // Exemplos esperados:
      // - "CINTA 180 PTO SEMI ACABADO" => cor: "PTO SEMI ACABADO"
      // - "DAYANE 13 UP BORR. BCA SEMI ACABADO" => cor: "BORR. BCA SEMI ACABADO"
      // - "PRIME 30/LUPO SEMI ACABADO" => cor contém "/LUPO" (ou "30/LUPO")
      const norm = (t) => String(t ?? "").toUpperCase().replace(/[^A-Z0-9/]/g, "");
      const isCorMarker = (t) => {
        const s = norm(t);
        if (!s) return false;
        if (s === "PTO") return true;
        if (s === "BCA") return true;
        if (s.startsWith("BORR")) return true;
        if (s.includes("/LUPO") || s === "/LUPO" || s.endsWith("/LUPO")) return true;
        return false;
      };

      // Inclui uma cadeia contígua de marcadores imediatamente antes do "SEMI ACABADO".
      // Ex: "NUD 11 BORR. BCA SEMI ACABADO" => startIdx aponta para "BORR.".
      let startIdx = semiIndex;
      for (let i = semiIndex - 1; i >= 0; i--) {
        if (!isCorMarker(words[i])) break;
        startIdx = i;
      }

      // Sem "N": pelo menos garante "SEMI ACABADO" como Cor.
      return {
        artigo: words.slice(0, startIdx).join(" ").trim(),
        cor: words.slice(startIdx).join(" ").trim(),
      };
    }
  }

  // Padrão 2: cores comuns
  const cores = [
    "preto",
    "branco",
    "azul",
    "vermelho",
    "verde",
    "amarelo",
    "cinza",
    "rosa",
    "roxo",
    "laranja",
    "marrom",
    "bege",
    "nude",
    "cru",
    "natural",
    "colorido",
    "estampado",
  ];

  for (const corPalavra of cores) {
    const idx = lower.indexOf(corPalavra);
    if (idx !== -1) {
      const before = raw.slice(0, idx).trim();
      const after = raw.slice(idx).trim();
      return { artigo: before, cor: after };
    }
  }

  // Padrão 3: separadores
  // No interface.py, quando encontra " c/" ou " com ", ele volta uma palavra
  // para que a cor pegue o "último token" antes do separador.
  for (const sep of [" c/", " com "]) {
    const idx = lower.indexOf(sep);
    if (idx !== -1) {
      const before = raw.slice(0, idx).trim();
      const words = before.split(" ").filter(Boolean);
      if (words.length) {
        const lastWord = words[words.length - 1];
        const lastPos = raw.slice(0, idx).lastIndexOf(lastWord);
        if (lastPos !== -1) {
          return {
            artigo: raw.slice(0, lastPos).trim(),
            cor: raw.slice(lastPos).trim(),
          };
        }
      }

      // Fallback seguro: se algo der errado, divide no separador.
      const cut = idx + sep.length;
      return { artigo: raw.slice(0, idx).trim(), cor: raw.slice(cut).trim() };
    }
  }

  return { artigo: raw, cor: "" };
}
