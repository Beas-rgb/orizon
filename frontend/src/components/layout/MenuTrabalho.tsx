import { useNavigate } from "react-router-dom";
import { ACCENT, glassStyle } from "../../lib/theme";

type Item = { id: string; label: string };

/** Coluna esquerda do trabalho. O primeiro item sempre volta para a home. */
export function MenuTrabalho({
  itens,
  ativo,
  onEscolher,
}: {
  itens: Item[];
  ativo: string;
  onEscolher: (id: string) => void;
}) {
  const navigate = useNavigate();
  return (
    <aside
      className="w-[11.5rem] shrink-0 rounded-3xl p-2 flex flex-col gap-1 self-start"
      style={glassStyle}
    >
      <button
        type="button"
        onClick={() => navigate("/inicio")}
        className="text-left rounded-2xl px-3 py-2.5 text-[12px] font-bold text-white"
        style={{ background: ACCENT }}
      >
        ← Home
      </button>
      {itens.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onEscolher(item.id)}
          className="text-left rounded-2xl px-3 py-2 text-[12px]"
          style={{
            fontWeight: ativo === item.id ? 700 : 500,
            background: ativo === item.id ? "rgba(29,95,175,0.12)" : "transparent",
            color: ativo === item.id ? ACCENT : "#4b5563",
          }}
        >
          {item.label}
        </button>
      ))}
    </aside>
  );
}
