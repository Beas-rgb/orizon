import { useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import { ACCENT } from "../../lib/theme";
import type { PreviaImportacao } from "./tipos";

const MODELO_CSV = [
  "nome,email,cargo,setor,superior_email",
  "Ana Silva,ana@orgao.gov.br,Presidente,Gabinete,",
  "Bruno Costa,bruno@orgao.gov.br,Diretor,RH,ana@orgao.gov.br",
  "Carla Dias,carla@orgao.gov.br,Analista,RH,bruno@orgao.gov.br",
].join("\n");

export function ImportacaoEquipe({
  projetoId,
  onImportado,
  onErro,
}: {
  projetoId: string;
  onImportado: (criados: number) => void;
  onErro: (msg: string) => void;
}) {
  const [previa, setPrevia] = useState<PreviaImportacao | null>(null);
  const [importando, setImportando] = useState(false);
  const [arquivoNome, setArquivoNome] = useState("");

  function baixarModelo() {
    const blob = new Blob([MODELO_CSV], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "modelo-equipe.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    onErro("");
    const form = evento.currentTarget;
    const arquivo = (form.elements.namedItem("arquivo") as HTMLInputElement).files?.[0];
    if (!arquivo) {
      onErro("Escolha um arquivo CSV ou XLSX.");
      return;
    }
    setArquivoNome(arquivo.name);
    const dados = new FormData();
    dados.append("arquivo", arquivo);
    try {
      const resp = await api<PreviaImportacao>(`/projetos/${projetoId}/importar/previa`, {
        method: "POST",
        formData: dados,
      });
      setPrevia(resp);
    } catch (exc) {
      onErro(exc instanceof Error ? exc.message : "Erro na importação");
    }
  }

  async function confirmar() {
    if (!previa) return;
    setImportando(true);
    onErro("");
    try {
      const resp = await api<{ criados: number; total: number }>(
        `/projetos/${projetoId}/importar/confirmar`,
        { method: "POST", json: { linhas: previa.linhas } },
      );
      setPrevia(null);
      setArquivoNome("");
      onImportado(resp.criados);
    } catch (exc) {
      onErro(exc instanceof Error ? exc.message : "Erro ao confirmar");
    } finally {
      setImportando(false);
    }
  }

  const field =
    "mt-1 w-full rounded-xl px-3 py-2.5 outline-none bg-white/70 border border-white/80 text-[13px]";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[13px] font-semibold text-gray-800">Importar equipe</p>
        <button
          type="button"
          onClick={baixarModelo}
          className="text-[12px] font-bold underline"
          style={{ color: ACCENT }}
        >
          Baixar modelo CSV
        </button>
      </div>
      <form onSubmit={enviar} className="grid sm:grid-cols-3 gap-2 items-end">
        <label className="text-[12px] font-semibold text-gray-600 sm:col-span-2">
          Arquivo CSV ou XLSX
          <input name="arquivo" type="file" accept=".csv,.xlsx" required className={field} />
        </label>
        <button
          type="submit"
          className="rounded-xl py-2.5 text-white text-[13px] font-bold"
          style={{ background: ACCENT }}
        >
          Ver prévia
        </button>
      </form>
      {arquivoNome && !previa ? (
        <p className="text-[11px] text-gray-500">Selecionado: {arquivoNome}</p>
      ) : null}
      {previa ? (
        <div className="rounded-2xl p-4" style={{ background: "rgba(29,95,175,0.06)" }}>
          <p className="text-[13px] font-bold text-gray-800 mb-2">
            Prévia{arquivoNome ? ` · ${arquivoNome}` : ""}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[12px] text-gray-600 mb-3">
            <span>Total: {previa.total}</span>
            <span>Válidos: {previa.validos}</span>
            <span>Inválidos: {previa.invalidos}</span>
            <span>Setores: {previa.setores}</span>
            <span>Cargos: {previa.cargos}</span>
            <span>Níveis: {previa.niveis}</span>
            <span>Duplicados: {previa.duplicados}</span>
            <span>Superior ausente: {previa.superiores_inexistentes}</span>
          </div>
          <div className="max-h-56 overflow-y-auto mb-3">
            <table className="w-full text-[11px] text-left">
              <thead>
                <tr className="text-gray-500 border-b border-white/60">
                  <th className="py-1 pr-2">Nome</th>
                  <th className="py-1 pr-2">E-mail</th>
                  <th className="py-1 pr-2">Cargo</th>
                  <th className="py-1 pr-2">Setor</th>
                  <th className="py-1">Erros</th>
                </tr>
              </thead>
              <tbody>
                {previa.linhas.map((l, i) => (
                  <tr
                    key={`${l.email}-${i}`}
                    className="border-b border-white/40"
                    style={{
                      background: l.erros.length ? "rgba(160,40,40,0.06)" : "transparent",
                    }}
                  >
                    <td className="py-1 pr-2">{l.nome}</td>
                    <td className="py-1 pr-2">{l.email}</td>
                    <td className="py-1 pr-2">{l.cargo}</td>
                    <td className="py-1 pr-2">{l.setor}</td>
                    <td className="py-1 text-[#A02828]">{l.erros.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              disabled={importando || previa.validos === 0}
              onClick={() => void confirmar()}
              className="rounded-xl px-4 py-2 text-white text-[13px] font-bold disabled:opacity-60"
              style={{ background: "#1E7A4A" }}
            >
              {importando ? "Importando…" : `Confirmar ${previa.validos} válidos`}
            </button>
            <button
              type="button"
              onClick={() => {
                setPrevia(null);
                setArquivoNome("");
              }}
              className="rounded-xl px-4 py-2 text-[13px] text-gray-600"
            >
              Cancelar
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
