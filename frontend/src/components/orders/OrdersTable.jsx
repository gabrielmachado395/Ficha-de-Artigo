import React, { useMemo } from "react";
import { normalizeForSearch } from "./ordersTableUtils";

/**
 * Tabela de ordens com filtro por texto.
 *
 * A busca é "contains" em campos relevantes (ordem, volume, artigo, cor, data, cliente)
 * com normalização para ignorar acentos.
 */
export default function OrdersTable({
  rows = [],
  searchTerm = "",
  selectedKey = null,
  onSelect,
}) {
  const query = normalizeForSearch(searchTerm).trim();

  const filteredRows = useMemo(() => {
    if (!query) return rows;
    return rows.filter((o) => {
      const haystack = normalizeForSearch(
        `${o.ordem} ${o.volume} ${o.artigo} ${o.cor} ${o.data} ${o.cliente}`
      );
      return haystack.includes(query);
    });
  }, [rows, query]);

  const thBase =
    "px-4 py-3 font-semibold text-left sticky top-0 z-10 " +
    "bg-slate-100 text-slate-700 border-b border-slate-200 whitespace-nowrap";

  const tdBase = "px-4 py-2 align-top";
  const tdSep = "border-l border-slate-200 first:border-l-0";

  return (
    <div className="w-full overflow-hidden rounded-2xl bg-white border border-slate-200 shadow-lg shadow-slate-900/10">
      <div className="scrollbar-min max-h-[50rem] overflow-x-auto overflow-y-auto">
        <table className="min-w-full w-full text-[length:var(--font-input)] text-slate-800 border-separate border-spacing-0">
          <thead>
            <tr className="h-14">
              <th className={thBase}>Ordem</th>
              <th className={thBase + " text-right tabular-nums"}>Volume</th>
              <th className={thBase}>Artigo</th>
              <th className={thBase}>Cor</th>
              <th className={thBase}>Data</th>
              <th className={thBase}>Cliente</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-200">
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                  {query
                    ? `Nenhum resultado para “${searchTerm}”.`
                    : "Nenhuma ordem para exibir."}
                </td>
              </tr>
            ) : (
              filteredRows.map((order, idx) => {
                const key = `${order.ordem}-${idx}`;
                const selected = selectedKey === key;

                return (
                  <tr
                    key={key}
                    tabIndex={0}
                    onClick={() => onSelect?.(order, key, { open: false })}
                    onDoubleClick={() => onSelect?.(order, key, { open: true })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") onSelect?.(order, key, { open: true });
                    }}
                    className={[
                      "outline-none transition-colors",
                      "odd:bg-white even:bg-slate-200/60",
                      "hover:bg-slate-100/70",
                      selected ? "bg-sky-100/60" : "",
                      "focus-visible:ring-2 focus-visible:ring-sky-400/40",
                    ].join(" ")}
                  >
                    <td className={`${tdBase}`}>{order.ordem}</td>

                    <td className={`${tdBase} ${tdSep} text-right tabular-nums whitespace-nowrap`}>
                      {order.volume}
                    </td>

                    <td
                      className={`${tdBase} ${tdSep} max-w-[220px] truncate`}
                      title={order.artigo || ""}
                    >
                      {order.artigo}
                    </td>

                    <td
                      className={`${tdBase} ${tdSep} max-w-[180px] truncate`}
                      title={order.cor || ""}
                    >
                      {order.cor}
                    </td>

                    <td className={`${tdBase} ${tdSep} tabular-nums whitespace-nowrap`}>
                      {order.data}
                    </td>

                    <td
                      className={`${tdBase} ${tdSep} max-w-[260px] truncate`}
                      title={order.cliente || ""}
                    >
                      {order.cliente}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
