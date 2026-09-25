export type NoArvore = {
  usuario_id: string;
  nome: string;
  email: string;
  cargo?: string | null;
  setor?: string | null;
  subordinados: NoArvore[];
};

export type LinhaImportacao = {
  nome: string;
  email: string;
  cargo: string;
  setor: string;
  superior_email: string;
  erros: string[];
};

export type PreviaImportacao = {
  total: number;
  validos: number;
  invalidos: number;
  setores: number;
  cargos: number;
  niveis: number;
  duplicados: number;
  superiores_inexistentes: number;
  linhas: LinhaImportacao[];
};
