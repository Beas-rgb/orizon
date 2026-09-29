import { gravarDesignTela, useDesignTela, type DesignTela } from "../../lib/designTela";

export function InterruptorDesign() {
  const [valor] = useDesignTela();

  function escolher(opcao: DesignTela) {
    gravarDesignTela(opcao);
  }

  return (
    <div
      className="fixed z-[80] right-3 bottom-[5.25rem] min-[900px]:bottom-4 flex rounded-full bg-white p-1 shadow-lg ring-1 ring-black/10"
      role="group"
      aria-label="Design da tela"
    >
      {(["atual", "novo"] as const).map((opcao) => (
        <button
          key={opcao}
          type="button"
          aria-pressed={valor === opcao}
          onClick={() => escolher(opcao)}
          className={`rounded-full px-3 py-1.5 text-[12px] font-semibold capitalize ${
            valor === opcao ? "bg-[#171717] text-white" : "text-[#5c5c5c]"
          }`}
        >
          {opcao}
        </button>
      ))}
    </div>
  );
}
