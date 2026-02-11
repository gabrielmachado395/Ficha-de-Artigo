import React from "react";

/**
 * Overlay de carregamento (tela inteira).
 *
 * Usado para bloquear a UI durante operações longas (ex.: buscar dados/imprimir)
 * e dar feedback visual ao usuário.
 */
export default function LoadingOverlay({ open, label }) {
  // Se não estiver aberto, não renderiza nada.
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-6 py-5 text-white shadow-2xl shadow-black/40">
        <div
          className="h-10 w-10 animate-spin rounded-full border-4 border-white/30 border-t-white"
          aria-hidden="true"
        />
        <div className="text-sm font-semibold tracking-wide">
          {label || "Carregando..."}
        </div>
      </div>
    </div>
  );
}
