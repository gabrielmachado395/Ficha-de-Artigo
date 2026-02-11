import React, { useEffect, useMemo, useRef, useState } from "react";
import { Capacitor } from "@capacitor/core";
import {
  calcularDistribuicao,
  calcularMetros,
  dividirArtigoCor,
  formatDecimalInput,
  formatIntegerInput,
  formatPesoOutput,
  getTurnoSP,
  maskDateBR,
  todayBR,
} from "../../lib/rules";
import { apiFetch } from "../../lib/api";
import { Field, Input } from "./OrderDetailsFields";
import { isPreto2, isZeroNumeric } from "./orderDetailsUtils";

/**
 * Painel lateral com a ficha (Tingimento/Retingimento).
 *
 * Este arquivo concentra o fluxo principal e delega peças menores para:
 * - OrderDetailsFields.jsx (componentes visuais Field/Input)
 * - orderDetailsUtils.js (regras utilitárias de validação)
 */
export default function OrderDetailsPanel({
  open,
  tab,
  order,
  onClose,
  onPrint,
  printing,
}) {
  const title = useMemo(
    () => (tab === "retingimento" ? "Retingimento" : "Tingimento"),
    [tab]
  );

  const isNew = Boolean(order?.__new);
  const manualFicha = isNew || tab === "retingimento";

  const prevTabRef = useRef(tab);
  const prevOrderRef = useRef(order);

  const [form, setForm] = useState({
    ordem: "",
    artigoCompleto: "",
    corSelecionada: "",
    clienteNome: "",
    volumeProg: "0",
    dataProcesso: "",
    elasticidadeAcab: "",
    larguraAcab: "",
    mtf: "",
    numeroCortes: "",
    operador: "",
    turno: "B",
    tambores: "",
    caixa: "0",
    pesoKg: "",
    metros: "0.00",
    distribuicao: "0.00",
    observacoes: "",
  });

  const [formError, setFormError] = useState("");
  const [operadorOk, setOperadorOk] = useState(false);

  const printerHost = String(import.meta.env.VITE_PRINTER_HOST ?? "").trim();

  // Detecta se está rodando em plataforma nativa (Capacitor).
  const isNative = (() => {
    try {
      const viaImport = Capacitor?.isNativePlatform?.();
      const viaWindow =
        typeof window !== "undefined" && window?.Capacitor?.isNativePlatform?.();
      return Boolean(viaImport || viaWindow);
    } catch {
      return false;
    }
  })();

  const operadorRef = useRef(null);
  const operadoresByMatriculaRef = useRef(null);

  const artigosCacheRef = useRef(null);
  const [artigosOptions, setArtigosOptions] = useState([]);
  const [artigoSuggestOpen, setArtigoSuggestOpen] = useState(false);
  const closeSuggestTimerRef = useRef(null);

  useEffect(() => {
    // A lista de artigos é necessária sempre que estivermos no modo manual
    // (Adicionar Ordem ou Retingimento manual).
    if (!open || !manualFicha) return;
    if (artigosCacheRef.current) {
      setArtigosOptions(artigosCacheRef.current);
      return;
    }

    const controller = new AbortController();
    (async () => {
      try {
        // Preferido: mesmo endpoint do Tkinter (lista completa)
        const resp = await apiFetch("/consulta/allArtigos", {
          signal: controller.signal,
        });
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data) && data.length) {
            const map = new Map();
            for (const item of data) {
              const raw = String(item?.Artigo ?? "")
                .replace(/\s+/g, " ")
                .trim();
              if (!raw) continue;

              const value = raw.toUpperCase();
              if (map.has(value)) continue;

              const { artigo, cor } = dividirArtigoCor(value);
              const label = cor?.trim() ? `${artigo} (${cor})` : artigo;
              map.set(value, { value, label });
            }

            const options = Array.from(map.values()).sort((a, b) =>
              a.label.localeCompare(b.label, "pt-BR")
            );
            artigosCacheRef.current = options;
            setArtigosOptions(options);
            return;
          }
        }

        // Fallback: lista parcial via tinturariaDados
        const resp2 = await apiFetch("/consulta/tinturariaDados", {
          signal: controller.signal,
        });
        if (!resp2.ok) return;
        const data2 = await resp2.json();
        let arr = Array.isArray(data2) ? data2 : data2?.data || [];
        if (!Array.isArray(arr) && typeof arr === "object") arr = Object.values(arr);

        const map = new Map();
        for (const row of arr) {
          const sku = row?.SKU || row?.ArtigoCompleto || "";
          const artigo = row?.Artigo || "";
          const cor = row?.Cor || "";

          const raw = String(sku || `${artigo} ${cor}`)
            .replace(/\s+/g, " ")
            .trim();
          if (!raw) continue;

          const value = raw.toUpperCase();
          if (map.has(value)) continue;
          const derived = dividirArtigoCor(value);
          const label = derived.cor?.trim()
            ? `${derived.artigo} (${derived.cor})`
            : derived.artigo;
          map.set(value, { value, label });
        }

        const options = Array.from(map.values()).sort((a, b) =>
          a.label.localeCompare(b.label, "pt-BR")
        );
        artigosCacheRef.current = options;
        setArtigosOptions(options);
      } catch {
        // silencioso
      }
    })();

    return () => controller.abort();
  }, [open, manualFicha]);

  const artigoSuggestions = useMemo(() => {
    if (!manualFicha) return [];
    const q = String(form.artigoCompleto ?? "").trim().toUpperCase();
    if (!q) return [];

    const out = [];
    for (const opt of artigosOptions) {
      const value = String(opt?.value ?? opt ?? "");
      const label = String(opt?.label ?? value);

      if (tab === "retingimento") {
        const split = dividirArtigoCor(value);
        if (!isPreto2(split.cor)) continue;
      }

      const hay = `${value} ${label}`.toUpperCase();
      if (!hay.includes(q)) continue;

      out.push({ value, label });
      if (out.length >= 5) break;
    }
    return out;
  }, [manualFicha, artigosOptions, form.artigoCompleto, tab]);

  useEffect(() => {
    return () => {
      if (closeSuggestTimerRef.current) {
        clearTimeout(closeSuggestTimerRef.current);
        closeSuggestTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!open || !order) return;

    const tabChanged = prevTabRef.current !== tab;
    const orderChanged = prevOrderRef.current !== order;
    prevTabRef.current = tab;
    prevOrderRef.current = order;

    if (tabChanged || orderChanged) {
      setFormError("");
      setOperadorOk(false);
    }

    // Ficha nova: não reseta campos ao trocar de aba (experiência fluida),
    // apenas aplica regra de cliente fixo no retingimento.
    if (isNew) {
      if (orderChanged) {
        setForm({
          ordem: "",
          artigoCompleto: "",
          corSelecionada: "",
          clienteNome: tab === "retingimento" ? "RETINGIMENTO" : "",
          volumeProg: "0",
          dataProcesso: todayBR(),
          elasticidadeAcab: "",
          larguraAcab: "",
          mtf: "",
          numeroCortes: "",
          operador: "",
          turno: getTurnoSP(),
          tambores: "",
          caixa: String(order.caixa ?? "0"),
          pesoKg: "",
          metros: "0.00",
          distribuicao: "0.00",
          observacoes: "",
        });
        return;
      }

      if (tabChanged) {
        setForm((s) => {
          if (tab === "retingimento") {
            if (s.clienteNome === "RETINGIMENTO") return s;
            return { ...s, clienteNome: "RETINGIMENTO" };
          }

          if (s.clienteNome === "RETINGIMENTO") {
            return { ...s, clienteNome: "" };
          }
          return s;
        });
      }
      return;
    }

    // Retingimento com ordem existente selecionada: usa modo manual (igual "Adicionar Ordem").
    // Não puxa ordem/artigo/cor/volume da ordem selecionada; cliente fica fixo.
    if (tab === "retingimento") {
      setForm({
        ordem: "",
        artigoCompleto: "",
        corSelecionada: "",
        clienteNome: "RETINGIMENTO",
        volumeProg: "0",
        dataProcesso: todayBR(),
        elasticidadeAcab: "",
        larguraAcab: "",
        mtf: "",
        numeroCortes: "",
        operador: "",
        turno: getTurnoSP(),
        tambores: "",
        caixa: "0",
        pesoKg: "",
        metros: "0.00",
        distribuicao: "0.00",
        observacoes: "",
      });
      return;
    }

    // Tingimento com ordem existente: reseta para refletir a seleção.
    setForm({
      ordem: String(order.ordem ?? ""),
      artigoCompleto: String(order.artigo ?? ""),
      corSelecionada: String(order.cor ?? ""),
      clienteNome: String(order.cliente ?? ""),
      volumeProg: String(order.volume ?? "0"),
      dataProcesso: todayBR(),
      elasticidadeAcab: "",
      larguraAcab: "",
      mtf: "",
      numeroCortes: "",
      operador: "",
      turno: getTurnoSP(),
      tambores: "",
      caixa: String(order.caixa ?? "0"),
      pesoKg: "",
      metros: "0.00",
      distribuicao: "0.00",
      observacoes: "",
    });
  }, [open, order, tab, isNew]);

  // Mantém o Turno sempre atualizado mesmo com o app aberto por horas.
  // Evita imprimir com turno antigo após virada de turno.
  useEffect(() => {
    if (!open) return;

    const tick = () => {
      const current = getTurnoSP();
      setForm((s) => (s.turno === current ? s : { ...s, turno: current }));
    };

    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, [open]);

  const artigoDerivado = useMemo(() => {
    if (!manualFicha) return { artigo: order?.artigo ?? "", cor: order?.cor ?? "" };
    const split = dividirArtigoCor(form.artigoCompleto);
    const cor = String(form.corSelecionada ?? "").trim() || split.cor;
    return { artigo: split.artigo, cor };
  }, [manualFicha, order, form.artigoCompleto, form.corSelecionada]);

  // Regra do interface.py: Caixa é calculada no backend com base em (ordem + peso).
  useEffect(() => {
    if (!open || !order) return;

    const controller = new AbortController();
    const handle = setTimeout(async () => {
      try {
        const pesoLimpo = String(form.pesoKg ?? "").replace(/,/g, ".").trim();
        const pesoNum = Number(pesoLimpo);

        if (!pesoLimpo || !Number.isFinite(pesoNum) || pesoNum === 0) {
          setForm((s) => ({ ...s, caixa: "0" }));
          return;
        }

        const nrOrdem = isNew
          ? String(form.ordem ?? "").trim()
          : String(order.ordem ?? "").trim();
        if (!nrOrdem) return;

        const resp = await fetch(
          `/api/consulta/tinturariaDados?ordem=${encodeURIComponent(
            nrOrdem
          )}&peso=${encodeURIComponent(pesoLimpo)}`,
          { signal: controller.signal }
        );
        if (!resp.ok) return;

        const data = await resp.json();
        const registro = Array.isArray(data) ? data[0] : null;

        const caixaCalculada =
          registro && registro.Caixa != null ? String(registro.Caixa) : "Sem padrão";

        setForm((s) => ({ ...s, caixa: caixaCalculada }));
      } catch {
        // silencioso
      }
    }, 400);

    return () => {
      clearTimeout(handle);
      controller.abort();
    };
  }, [open, order, isNew, form.ordem, form.pesoKg]);

  // Recalcula metros/distribuição quando peso/caixa/gramatura muda
  useEffect(() => {
    if (!open) return;
    setForm((s) => {
      const metros = calcularMetros(s.pesoKg, order?.gramatura ?? "0.00");
      const distribuicao = calcularDistribuicao(metros, s.caixa);
      if (metros === s.metros && distribuicao === s.distribuicao) return s;
      return { ...s, metros, distribuicao };
    });
  }, [open, order, form.pesoKg, form.caixa]);

  function handleChange(e) {
    const { name, value } = e.target;

    if (name === "operador") {
      setFormError("");
      setOperadorOk(false);
      setForm((s) => ({ ...s, [name]: String(value ?? "").replace(/\D/g, "") }));
      return;
    }

    if (name === "ordem") {
      setForm((s) => ({ ...s, [name]: String(value ?? "").replace(/\D/g, "") }));
      return;
    }

    if (name === "dataProcesso") {
      setForm((s) => ({ ...s, [name]: maskDateBR(value) }));
      return;
    }

    if (name === "pesoKg") {
      setForm((s) => ({ ...s, [name]: formatDecimalInput(value) }));
      return;
    }

    if (name === "elasticidadeAcab" || name === "larguraAcab" || name === "mtf") {
      setForm((s) => ({ ...s, [name]: formatDecimalInput(value) }));
      return;
    }

    if (name === "tambores" || name === "caixa" || name === "numeroCortes") {
      setForm((s) => ({ ...s, [name]: formatIntegerInput(value) }));
      return;
    }

    if (name === "artigoCompleto") {
      setForm((s) => ({ ...s, [name]: value, corSelecionada: "" }));
      return;
    }

    setFormError("");
    setForm((s) => ({ ...s, [name]: value }));
  }

  function handleBlur(e) {
    const { name, value } = e.target;
    if (name === "artigoCompleto") {
      const raw = String(value ?? "").replace(/\s+/g, " ").trim();
      if (!raw) {
        setForm((s) => ({ ...s, artigoCompleto: "", corSelecionada: "" }));
        return;
      }

      const split = dividirArtigoCor(raw.toUpperCase());
      setForm((s) => ({
        ...s,
        artigoCompleto: split.artigo,
        corSelecionada: split.cor?.trim() ? split.cor : s.corSelecionada,
      }));
      return;
    }

    if (name === "pesoKg") {
      setForm((s) => ({ ...s, [name]: formatPesoOutput(value) }));
      return;
    }

    if (
      name === "tambores" ||
      name === "numeroCortes" ||
      name === "elasticidadeAcab" ||
      name === "larguraAcab" ||
      name === "mtf" ||
      name === "ordem"
    ) {
      if (isZeroNumeric(value)) {
        setForm((s) => ({ ...s, [name]: "" }));
      }
    }

    if (name === "operador") {
      const matricula = String(value ?? "").trim();

      if (!matricula) {
        setOperadorOk(false);
        return;
      }

      (async () => {
        try {
          if (!operadoresByMatriculaRef.current) {
            const resp = await apiFetch("/consulta/operador");
            if (!resp.ok) throw new Error("Falha ao buscar lista de operadores");
            const data = await resp.json();
            const map = new Map();
            if (Array.isArray(data)) {
              for (const item of data) {
                const m = String(item?.Matricula ?? "").trim();
                const n = String(item?.Operador ?? "").trim();
                if (m && n) map.set(m, n);
              }
            }
            operadoresByMatriculaRef.current = map;
          }

          const nome = operadoresByMatriculaRef.current.get(matricula);
          if (nome) {
            setForm((s) => ({ ...s, operador: nome }));
            setOperadorOk(true);
            return;
          }

          setForm((s) => ({ ...s, operador: "Operador não encontrado" }));
          setOperadorOk(false);
          setTimeout(() => {
            operadorRef.current?.focus?.();
            operadorRef.current?.select?.();
          }, 0);
        } catch {
          setForm((s) => ({ ...s, operador: "Operador não encontrado" }));
          setOperadorOk(false);
          setTimeout(() => {
            operadorRef.current?.focus?.();
            operadorRef.current?.select?.();
          }, 0);
        }
      })();
    }
  }

  const ordemObrigatoria = tab !== "retingimento";

  const canPrint =
    Boolean(order) &&
    (!manualFicha ||
      !ordemObrigatoria ||
      (form.ordem.trim() && !isZeroNumeric(form.ordem))) &&
    (!manualFicha || artigoDerivado.artigo.trim()) &&
    (!manualFicha || artigoDerivado.cor.trim()) &&
    (!manualFicha || form.clienteNome.trim()) &&
    form.dataProcesso.trim() &&
    form.operador.trim() &&
    operadorOk &&
    form.tambores.trim() &&
    !isZeroNumeric(form.tambores) &&
    form.pesoKg.trim() &&
    !isZeroNumeric(form.pesoKg) &&
    (!form.elasticidadeAcab.trim() ||
      !isZeroNumeric(form.elasticidadeAcab)) &&
    (!form.larguraAcab.trim() || !isZeroNumeric(form.larguraAcab)) &&
    (!form.mtf.trim() || !isZeroNumeric(form.mtf)) &&
    (!form.numeroCortes.trim() || !isZeroNumeric(form.numeroCortes));

  function validateBeforePrint() {
    if (canPrint) {
      setFormError("");
      return true;
    }
    setFormError("Preencha todos os campos");
    return false;
  }

  if (!open) return null;

  return (
    <div className="rounded-2xl border border-[color:var(--surface-border)] bg-[color:var(--surface-bg)] shadow-xl shadow-black/10 backdrop-blur-md">
      <div className="flex items-start justify-between gap-4 border-b border-[color:var(--surface-border)] px-5 py-4">
        <div>
          <div className="text-[length:var(--font-label)] font-semibold tracking-wide text-[color:var(--muted)]">
            Ficha do Artigo
          </div>
          <div className="text-[length:var(--font-title)] font-bold text-[color:var(--text)]">
            {title}
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="rounded-xl px-2 py-1 transition text-[color:var(--muted)] hover:bg-black/5 hover:text-[color:var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--focus-ring)]"
          aria-label="Fechar painel"
          title="Fechar"
        >
          ✕
        </button>
      </div>

      <div className="p-5">
        {!order ? (
          <div className="rounded-2xl border border-[color:var(--surface-border)] bg-[color:var(--input-bg)] p-6 text-center text-[length:var(--font-input)] text-[color:var(--muted)]">
            Selecione uma ordem para ver os detalhes.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {manualFicha ? (
                <Input
                  label={tab === "retingimento" ? "Ordem (opcional)" : "Ordem"}
                  name="ordem"
                  value={form.ordem}
                  onChange={handleChange}
                  placeholder="Digite a ordem"
                  inputMode="numeric"
                />
              ) : (
                <Field label="Ordem" value={order.ordem} />
              )}

              {manualFicha ? (
                <div className="relative">
                  <label className="block space-y-1">
                    <div className="text-[length:var(--font-label)] font-semibold tracking-wide text-[color:var(--muted)]">
                      Artigo
                    </div>
                    <input
                      name="artigoCompleto"
                      value={form.artigoCompleto}
                      onChange={(e) => {
                        if (closeSuggestTimerRef.current) {
                          clearTimeout(closeSuggestTimerRef.current);
                          closeSuggestTimerRef.current = null;
                        }
                        setArtigoSuggestOpen(true);
                        handleChange(e);
                      }}
                      onFocus={() => {
                        if (closeSuggestTimerRef.current) {
                          clearTimeout(closeSuggestTimerRef.current);
                          closeSuggestTimerRef.current = null;
                        }
                        setArtigoSuggestOpen(true);
                      }}
                      onBlur={(e) => {
                        handleBlur(e);
                        closeSuggestTimerRef.current = setTimeout(() => {
                          setArtigoSuggestOpen(false);
                        }, 120);
                      }}
                      placeholder="Ex: KISS 40 MM FALCÃO"
                      autoComplete="off"
                      spellCheck={false}
                      className={[
                        "w-full rounded-xl border px-3 py-2 outline-none transition uppercase",
                        "border-[color:var(--input-border)] bg-[color:var(--input-bg)]",
                        "text-[length:var(--font-input)] text-[color:var(--text)] placeholder:text-[color:var(--placeholder)]",
                        "focus:border-[color:var(--input-border-focus)] focus:bg-[color:var(--input-bg-focus)]",
                      ].join(" ")}
                    />
                  </label>

                  {artigoSuggestOpen && artigoSuggestions.length ? (
                    <div className="absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden rounded-xl border border-[color:var(--input-border)] bg-[color:var(--input-bg)] shadow-2xl shadow-black/20">
                      {artigoSuggestions.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onMouseDown={(ev) => {
                            ev.preventDefault();
                            const split = dividirArtigoCor(
                              String(opt.value ?? "").toUpperCase()
                            );
                            setForm((s) => ({
                              ...s,
                              artigoCompleto: split.artigo,
                              corSelecionada: split.cor,
                            }));
                            setArtigoSuggestOpen(false);
                          }}
                          className="block w-full px-3 py-2 text-left text-[length:var(--font-input)] text-[color:var(--text)] hover:bg-black/5 focus:outline-none focus-visible:bg-black/5"
                          title={opt.label}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : (
                <Field label="Artigo" value={order.artigo} />
              )}

              <Field label="Cor" value={manualFicha ? artigoDerivado.cor : order.cor} />
              <Field label="Volume Prog" value={manualFicha ? form.volumeProg : order.volume} />

              <Input
                label={tab === "retingimento" ? "Data Retingimento" : "Data Tingimento"}
                name="dataProcesso"
                value={form.dataProcesso}
                onChange={handleChange}
                placeholder="dd/mm/aaaa"
                inputMode="numeric"
              />

              <Input
                label="Elasticidade Acab"
                name="elasticidadeAcab"
                value={form.elasticidadeAcab}
                onChange={handleChange}
                placeholder="Digite aqui"
                inputMode="decimal"
              />

              <Input
                label="Largura Acab"
                name="larguraAcab"
                value={form.larguraAcab}
                onChange={handleChange}
                placeholder="Digite aqui"
                inputMode="decimal"
              />

              {tab === "retingimento" ? (
                <Field label="Cliente" value={form.clienteNome || "RETINGIMENTO"} />
              ) : manualFicha ? (
                <Input
                  label="Cliente"
                  name="clienteNome"
                  value={form.clienteNome}
                  onChange={handleChange}
                  placeholder="Digite o cliente"
                />
              ) : (
                <Field label="Cliente" value={order.cliente} />
              )}

              <Input
                label="MTF"
                name="mtf"
                value={form.mtf}
                onChange={handleChange}
                placeholder="Digite aqui"
                inputMode="decimal"
              />

              <Input
                label="Nº Cortes"
                name="numeroCortes"
                value={form.numeroCortes}
                onChange={handleChange}
                placeholder="Digite aqui"
                inputMode="numeric"
              />

              <Input
                label="Operador"
                name="operador"
                value={form.operador}
                onChange={handleChange}
                onBlur={handleBlur}
                inputRef={operadorRef}
                placeholder="Matrícula"
                inputMode="numeric"
              />

              <Field label="Turno" value={form.turno} />

              <Input
                label="Tambores"
                name="tambores"
                value={form.tambores}
                onChange={handleChange}
                placeholder="0"
                inputMode="numeric"
              />

              <Field label="Caixa" value={form.caixa} />

              <Input
                label="Peso (KG)"
                name="pesoKg"
                value={form.pesoKg}
                onChange={handleChange}
                onBlur={handleBlur}
                placeholder="0.000"
                inputMode="decimal"
              />

              <Field label="Metros" value={form.metros} />
            </div>

            <div className="mt-5">
              <div className="mb-2 text-[length:var(--font-label)] font-semibold text-[color:var(--muted)]">
                Observações
              </div>
              <label className="block space-y-1">
                <textarea
                  name="observacoes"
                  value={form.observacoes}
                  onChange={handleChange}
                  placeholder="Digite aqui"
                  rows={3}
                  className="w-full resize-none rounded-xl border px-3 py-2 outline-none transition uppercase border-[color:var(--input-border)] bg-[color:var(--input-bg)] text-[length:var(--font-input)] text-[color:var(--text)] placeholder:text-[color:var(--placeholder)] focus:border-[color:var(--input-border-focus)] focus:bg-[color:var(--input-bg-focus)]"
                />
              </label>
            </div>

            <div className="mt-5 border-t border-[color:var(--surface-border)] pt-4">
              {formError ? (
                <div className="mb-3 rounded-2xl border border-red-200 bg-red-50 p-3 text-[length:var(--font-input)] text-red-700">
                  {formError}
                </div>
              ) : null}

              {isNative && !printerHost ? (
                <div className="mb-3 rounded-2xl border border-[color:var(--surface-border)] bg-[color:var(--input-bg)] p-3 text-[length:var(--font-label)] text-[color:var(--muted)]">
                  Impressão direta não configurada. Defina `VITE_PRINTER_HOST` e gere o APK novamente.
                </div>
              ) : null}

              <button
                type="button"
                onClick={async () => {
                  if (!validateBeforePrint()) return;

                  const safeOrder =
                    tab === "retingimento" && order
                      ? { ...order, cliente: "RETINGIMENTO" }
                      : order;

                  await onPrint?.({
                    tab,
                    order: manualFicha
                      ? {
                          ...safeOrder,
                          ordem: form.ordem.trim(),
                          artigo: artigoDerivado.artigo.trim(),
                          cor: artigoDerivado.cor.trim(),
                          cliente:
                            tab === "retingimento"
                              ? "RETINGIMENTO"
                              : form.clienteNome.trim(),
                          volume: form.volumeProg,
                        }
                      : safeOrder,
                    ...form,
                    // Turno precisa ser recalculado na hora de imprimir.
                    // (o formulário pode ter sido aberto antes da virada de turno)
                    turno: getTurnoSP(),
                    // Compat com interface.py: se caixa vazia, aplica padrão
                    caixa: form.caixa?.trim() ? form.caixa : "Sem padrão",
                  });
                }}
                disabled={Boolean(printing)}
                className={[
                  "w-full rounded-2xl py-3 text-sm font-bold transition-all duration-200 ease-out",
                  canPrint
                    ? "shadow-lg shadow-black/10 hover:shadow-xl hover:-translate-y-0.5 hover:scale-[1.01] active:translate-y-0 active:scale-[0.98]"
                    : "opacity-70",
                  canPrint
                    ? "bg-[color:var(--pill-bg)] text-[color:var(--text)] border border-[color:var(--surface-border)]"
                    : "bg-[color:var(--surface-bg)] text-[color:var(--muted)] border border-[color:var(--surface-border)]",
                  "text-[length:var(--font-input)]",
                ].join(" ")}
              >
                <span className="inline-flex items-center justify-center gap-2">
                  {printing ? (
                    <span
                      className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                      aria-hidden="true"
                    />
                  ) : null}
                  {printing ? "Imprimindo..." : "Imprimir"}
                </span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
