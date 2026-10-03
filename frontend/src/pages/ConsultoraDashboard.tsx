import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { InicioConsultoraNovo } from "../components/dashboard/InicioConsultoraNovo";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";

type Projeto = {
  id: string;
  estado: string;
  rotulo: string;
  vinculo_titulo?: string | null;
  nome_fantasia?: string | null;
  razao_social?: string | null;
};

export function ConsultoraDashboard() {
  const { usuario } = useAuth();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Projeto[]>("/projetos")
      .then(setProjetos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  return (
    <AppShell>
      <InicioConsultoraNovo
        nome={usuario?.nome || "Consultora"}
        projetos={projetos}
        erro={erro}
      />
    </AppShell>
  );
}
