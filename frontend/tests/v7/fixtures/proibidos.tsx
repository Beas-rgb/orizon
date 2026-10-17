export function ruim(acao: (dados: { segredo: boolean }) => void) {
  eval("1");
  const criar = new Function("return 1");
  localStorage.setItem("a", "b");
  axios.get("/x");
  navigator.serviceWorker.register("/sw.js");
  const empurrar = PushManager;
  const manifesto = "manifest.webmanifest";
  console.log(acao({ segredo: true }));
  return { criar, empurrar, manifesto };
}

export function Marcado() {
  return <div dangerouslySetInnerHTML={{ __html: "<b>x</b>" }} />;
}
