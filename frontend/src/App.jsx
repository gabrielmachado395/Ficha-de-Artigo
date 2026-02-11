import React, { useMemo, useState, useEffect } from "react";
import OrdersTable from "./components/orders/OrdersTable";
import OrderDetailsPanel from "./components/orderDetails/OrderDetailsPanel";
import LoadingOverlay from "./components/common/LoadingOverlay";
import { Plus, Search } from "lucide-react";
import { requestPrint } from "./lib/printService";
import { dividirArtigoCor } from "./lib/rules";
import { apiFetch, getApiBaseUrl } from "./lib/api";

// Adicione antes de mapApiOrderToTable:
function formatVolumeNoDecimals(value) {
  let str = String(value ?? "").trim();
  // Se tem vírgula, assume formato brasileiro (milhar: ponto, decimal: vírgula)
  if (str.includes(",")) {
    str = str.replace(/\./g, "").replace(/,/g, ".");
  }
  // Se não tem vírgula, mas tem ponto, assume ponto como decimal
  const num = Number(str);
  if (!Number.isFinite(num)) return String(value ?? "");
  return Math.trunc(num).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}


function splitSkuArtigoCor(sku) {
  // Mantém a mesma regra do interface.py para separar Artigo/Cor
  // (ex: "Barra 12 mm Branco Enfestado" => Artigo: "Barra 12 mm" | Cor: "Branco Enfestado").
  return dividirArtigoCor(sku);
}

function mapApiOrderToTable(row) {
  const sku = row.SKU || row.ArtigoCompleto || row.Artigo || "";
  const split = splitSkuArtigoCor(sku);

  const corApi = String(row.Cor ?? "").trim();
  const corFinal = corApi || split.cor || "";
  const artigoApi = String(row.Artigo ?? "").trim();
  const artigoFinal = !corApi && split.cor ? (split.artigo || artigoApi || sku || "") : (artigoApi || split.artigo || sku || "");

  return {
    ordem: row.NrOrdem || row.Ordem || "",
    artigo: artigoFinal,
    cor: corFinal,
    cliente: row.Cliente || "",
    volume: formatVolumeNoDecimals(row.Quantity_Display || row.Quantity || row.Qtd || ""),
    data: row.DtOrdem || row.DtPedido || "",
    caixa: row.Caixa ?? row.Cx ?? row.CX ?? "0",
    gramatura: row.Gramatura ?? row.gramatura ?? row.Grm ?? "0.00",
  };
}
function App() {
  const [tab, setTab] = useState("tingimento");
  const [search, setSearch] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedKey, setSelectedKey] = useState(null);
  const [panelOpen, setPanelOpen] = useState(false);

  function makeNewOrderForTab(nextTab) {
    return {
      __new: true,
      ordem: "",
      artigo: "",
      cor: "",
      cliente: nextTab === "retingimento" ? "RETINGIMENTO" : "",
      volume: "0",
      caixa: "0",
      gramatura: "0.00",
    };
  }

  // Estado para dados reais
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [printError, setPrintError] = useState(null);
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    setLoading(true);
    setErro(null);
    apiFetch("/consulta/tinturariaDados")
      .then(r => {
        if (!r.ok) throw new Error("Erro ao buscar ordens");
        return r.json();
      })
      .then(data => {
        // Se vier DataFrame (pandas), pode ser um array de objetos ou objeto com .data
        let arr = Array.isArray(data) ? data : (data?.data || []);
        // Se vier DataFrame serializado, pode ser {data: [...], columns: [...]}
        if (!Array.isArray(arr) && typeof arr === "object") arr = Object.values(arr);
        setOrders(arr.map(mapApiOrderToTable));
      })
      .catch(e => {
        const base = getApiBaseUrl();
        const msg = e?.message ? String(e.message) : "Falha ao conectar na API";
        setErro(`${msg} | API: ${base}`);
      })
      .finally(() => setLoading(false));
  }, []);

  const tabs = useMemo(
    () => [
      { key: "tingimento", label: "Tingimento" },
      { key: "retingimento", label: "Retingimento" },
    ],
    []
  );

  const activeIndex = tabs.findIndex((t) => t.key === tab);

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 bg-gradient-to-b from-[#9bacc1] via-[#677993] to-[#1a2c44] flex flex-col items-center">
      <LoadingOverlay
        open={loading || printing}
        label={printing ? "Imprimindo..." : "Iniciando..."}
      />
      <div className="w-full max-w-7xl flex flex-col mb-8">
        {/* Top bar alinhada com o conteúdo */}
        <div className="flex flex-col gap-3 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:items-center">
          <div className="flex flex-wrap items-center gap-3">
            <button
                type="button"
                onClick={() => {
                  setSelectedOrder(makeNewOrderForTab(tab));
                  setSelectedKey("__new");
                  setPanelOpen(true);
                }}
                className={[
                  "inline-flex items-center gap-2 rounded-2xl border px-4 py-2 font-semibold",
                  "shadow-lg transition-all duration-200 ease-out",
                  "hover:-translate-y-0.5 hover:scale-[1.01] active:translate-y-0 active:scale-[0.98]",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--focus-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--ring-offset)]",
                  "border-[color:var(--input-border)] bg-[color:var(--input-bg)] hover:bg-[color:var(--input-bg-focus)]",
                  "text-[color:var(--text)] text-[length:var(--font-input)]",
                ].join(" ")}
                title="Adicionar Ordem"
              >
                <Plus className="h-5 w-5" />
                Adicionar Ordem
              </button>
          </div>

          {/* Tabs ao centro */}
          <div
            role="tablist"
            aria-label="Tipo de processo"
            className={[
              "relative inline-flex w-full justify-between items-center gap-1 overflow-hidden rounded-2xl border p-1 shadow-lg lg:w-auto",
              "border-[color:var(--input-border)] bg-[color:var(--surface-bg)]",
            ].join(" ")}
          >
            <span
              aria-hidden="true"
              className="absolute rounded-xl bg-[color:var(--input-bg)] shadow-md transition-transform duration-300 ease-out"
              style={{
                left: "0.25rem",
                top: "0.25rem",
                bottom: "0.25rem",
                width: `calc((100% - 0.5rem) / ${tabs.length})`,
                transform: `translateX(${Math.max(activeIndex, 0) * 100}%)`,
              }}
            />
            {tabs.map((t) => {
              const active = tab === t.key;
              return (
                <button
                  key={t.key}
                  role="tab"
                  aria-selected={active}
                  onClick={() => {
                    const nextTab = t.key;
                    setTab(nextTab);

                    // Se entrar em Retingimento sem uma ordem real selecionada,
                    // abre uma ficha nova (mesmo fluxo do "Adicionar Ordem"),
                    // com cliente fixo como RETINGIMENTO.
                    if (nextTab === "retingimento") {
                      if (!selectedOrder || selectedOrder.__new) {
                        setSelectedOrder(makeNewOrderForTab(nextTab));
                        setSelectedKey("__new");
                        setPanelOpen(true);
                      }
                      return;
                    }

                    // Ao sair do Retingimento para Tingimento, se estiver em ficha nova,
                    // remove o cliente fixo para permitir preenchimento manual.
                    if (nextTab === "tingimento" && selectedOrder?.__new) {
                      setSelectedOrder(makeNewOrderForTab(nextTab));
                      setSelectedKey("__new");
                    }
                  }}
                  className={[
                    "relative z-10 rounded-xl px-5 py-2 font-semibold transition-colors duration-200",
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--focus-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--ring-offset)]",
                    "flex-1 lg:flex-none",
                    "text-[length:var(--font-input)]",
                    active
                      ? "text-[color:var(--text)]"
                      : "text-[color:var(--muted)] hover:text-[color:var(--text)]",
                  ].join(" ")}
                >
                  {t.label}
                </button>
              );
            })}
          </div>

          {/* Busca no canto superior direito */}
          <div className="flex justify-end">
            <div className="flex items-center gap-2 w-full lg:max-w-[420px] ">

              <div className="relative w-full flex items-center">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 z-10 text-[color:var(--muted)]">
                  <Search className="w-5 h-5" />
                </div>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Pesquisar ..."
                  className={[
                    "w-full rounded-2xl border py-2 pl-10 pr-10 outline-none transition shadow-lg",
                    "border-[color:var(--input-border)] bg-[color:var(--input-bg)]",
                    "text-[color:var(--text)] placeholder:text-[color:var(--placeholder)]",
                    "focus:border-[color:var(--input-border-focus)] focus:bg-[color:var(--input-bg-focus)]",
                    "text-[length:var(--font-input)]",
                  ].join(" ")}
                />
                {search ? (
                  <button
                    type="button"
                    onClick={() => setSearch("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl px-2 py-1 transition z-10 text-[color:var(--muted)] hover:bg-black/5 hover:text-[color:var(--text)]"
                    aria-label="Limpar pesquisa"
                    title="Limpar"
                  >
                    ✕
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        {printError ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {printError}
          </div>
        ) : null}

        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_minmax(320px,380px)] lg:grid-cols-[minmax(0,1fr)_420px]">
          <div>
            {loading ? (
              <div className="rounded-xl bg-white/10 text-white/70 p-8 text-center">Carregando ordens...</div>
            ) : erro ? (
              <div className="rounded-xl bg-red-100 text-red-700 p-8 text-center">{erro}</div>
            ) : (
              <OrdersTable
                rows={orders}
                searchTerm={search}
                selectedKey={selectedKey}
                onSelect={(order, key, opts) => {
                  setSelectedOrder(order);
                  setSelectedKey(key);
                  if (opts?.open) setPanelOpen(true);
                }}
              />
            )}
            <div className="mt-3 text-[length:var(--font-label)] text-[color:var(--muted)]">
              Dica: clique seleciona; duplo clique abre o painel.
            </div>
          </div>

          <div className={panelOpen ? "block" : "hidden md:block"}>
            <OrderDetailsPanel
              open={panelOpen}
              tab={tab}
              order={selectedOrder}
              printing={printing}
              onClose={() => setPanelOpen(false)}
              onPrint={async (payload) => {
                try {
                  setPrinting(true);
                  setPrintError(null);
                  await requestPrint(payload);
                } catch (e) {
                  const msg = e?.message ? String(e.message) : "Falha ao imprimir";
                  setPrintError(msg);
                  console.error(e);
                } finally {
                  setPrinting(false);
                }
              }}
            />

            {!panelOpen ? (
              <div className="hidden md:flex h-full items-center justify-center rounded-2xl border border-white/15 bg-white/5 p-8 text-center text-sm text-white/60">
                Selecione uma ordem e dê duplo clique para abrir.
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;