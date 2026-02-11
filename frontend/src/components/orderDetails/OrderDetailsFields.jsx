import React from "react";
import { readOnlyValue } from "./orderDetailsUtils";

/**
 * Campo somente leitura (visual) para exibir dados da ordem.
 */
export function Field({ label, value }) {
  return (
    <div className="space-y-1">
      <div className="text-[length:var(--font-label)] font-semibold tracking-wide text-[color:var(--muted)]">
        {label}
      </div>
      <div className="rounded-xl border border-[color:var(--input-border)] bg-[color:var(--input-bg)] px-3 py-2 text-[length:var(--font-input)] text-[color:var(--text)] shadow-inner shadow-black/5 uppercase">
        {readOnlyValue(value)}
      </div>
    </div>
  );
}

/**
 * Input padrão usado no formulário da ficha.
 *
 * Mantém classes e comportamento em um lugar só, para o painel ficar mais legível.
 */
export function Input({
  label,
  name,
  value,
  onChange,
  onBlur,
  inputRef,
  placeholder,
  type = "text",
  inputMode,
  list,
  autoComplete,
  disabled,
}) {
  return (
    <label className="block space-y-1">
      <div className="text-[length:var(--font-label)] font-semibold tracking-wide text-[color:var(--muted)]">
        {label}
      </div>
      <input
        ref={inputRef}
        name={name}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        placeholder={placeholder}
        type={type}
        inputMode={inputMode}
        list={list}
        autoComplete={autoComplete}
        spellCheck={false}
        disabled={disabled}
        className={[
          "w-full rounded-xl border px-3 py-2 outline-none transition uppercase",
          "border-[color:var(--input-border)] bg-[color:var(--input-bg)]",
          "text-[length:var(--font-input)] text-[color:var(--text)] placeholder:text-[color:var(--placeholder)]",
          "focus:border-[color:var(--input-border-focus)] focus:bg-[color:var(--input-bg-focus)]",
          disabled ? "cursor-not-allowed opacity-60" : "",
        ].join(" ")}
      />
    </label>
  );
}
