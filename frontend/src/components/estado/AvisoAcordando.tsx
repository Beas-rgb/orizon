export function AvisoAcordando({ onTentar }: { onTentar?: () => void }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="mx-auto mb-4 w-full max-w-lg rounded-2xl bg-white px-4 py-3 text-[14px] text-[#1c1c1c] ring-1 ring-black/10"
    >
      <p>Estamos acordando o servidor. Isso pode levar até 1 minuto.</p>
      {onTentar ? (
        <button type="button" className="mt-2 text-[13px] font-semibold underline" onClick={onTentar}>
          Tentar de novo
        </button>
      ) : null}
    </div>
  );
}
