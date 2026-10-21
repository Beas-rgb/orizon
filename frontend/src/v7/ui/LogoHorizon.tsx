/** Logo temporária: arquivo único public/assets/logo/horizon-logo.png. Para trocar, substitua só o arquivo. */
export const LOGO_URL = `${import.meta.env.BASE_URL}assets/logo/horizon-logo.png`;

export function LogoHorizon({ palavra = true, altura }: { palavra?: boolean; altura?: number }) {
  return (
    <span className="logo-horizon">
      <img src={LOGO_URL} alt={palavra ? "" : "Horizon"} style={altura ? { height: altura } : undefined} />
      {palavra ? <span className="palavra">HORIZON</span> : null}
    </span>
  );
}
