export function releases(realExample?: { name: string; slug: string }) {
  return [
    {
      area: "01 / INTERFACE",
      title: "Primeiro voo",
      description: "Landing navegável e exercício simulado para testar alternância, reprodução e teclado.",
      action: { href: "/explorar/?exemplo=prototipo", label: "Testar o protótipo" },
    },
    {
      area: "02 / OBSERVAÇÕES",
      title: "Primeiros recortes",
      description: realExample
        ? `Duas exposições de ${realExample.name} processadas na mesma grade celeste. O exemplo abre sem depender da API.`
        : "O exemplo real será liberado após a validação do par de exposições.",
      action: realExample && { href: `/explorar/?exemplo=${realExample.slug}`, label: "Abrir dados reais" },
    },
    {
      area: "03 / INTEGRAÇÃO",
      title: "Linha do tempo",
      description: "Explore as datas e os horários de Epsilon Indi B no catálogo salvo. Com a API ativa, busque outros campos e abra os recortes no visor.",
      action: { href: "/explorar/?exemplo=eps-indi-b&modo=epocas", label: "Abrir épocas de Epsilon Indi B" },
    },
    {
      area: "04 / PUBLICAÇÃO",
      title: "Versão pública",
      description: "Configuração preparada para Cloudflare Pages e Render. A validação da hospedagem pública ainda está pendente.",
    },
  ];
}
