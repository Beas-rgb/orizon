export function Toggle({ ligado, onMudar, rotulo }: { ligado: boolean; onMudar: (v: boolean) => void; rotulo: string }) {
  return (
    <button type="button" role="switch" aria-checked={ligado} className="v7-toggle" onClick={() => onMudar(!ligado)}>
      <span className="trilho" aria-hidden="true" />
      {rotulo}
    </button>
  );
}
