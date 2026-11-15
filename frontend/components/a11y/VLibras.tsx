"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";

declare global {
  interface Window { VLibras?: { Widget: new (url: string) => unknown } }
}

const PLUGIN = "https://vlibras.gov.br/app/vlibras-plugin.js";
let started = false;

/**
 * VLibras, o tradutor de Libras do governo federal (vlibras.gov.br). Só é carregado quando a
 * pessoa liga a opção. A marcação abaixo é a do snippet oficial; o script monta o botão e o avatar.
 */
export default function VLibras({ enabled }: { enabled: boolean }) {
  useEffect(() => {
    if (started) return;
    started = true;
    const start = () => window.VLibras && new window.VLibras.Widget("https://vlibras.gov.br/app");
    if (window.VLibras) {
      start();
      return;
    }
    const script = document.createElement("script");
    script.src = PLUGIN;
    script.async = true;
    script.onload = start;
    document.body.appendChild(script);
  }, []);

  return createPortal(
    // Desligar só esconde: o script do VLibras não sabe se montar de novo numa marcação recriada.
    <div {...{ vw: "" }} className="enabled" style={enabled ? undefined : { display: "none" }}>
      <div {...{ "vw-access-button": "" }} className="active" />
      <div {...{ "vw-plugin-wrapper": "" }}>
        <div className="vw-plugin-top-wrapper" />
      </div>
    </div>,
    document.body,
  );
}
