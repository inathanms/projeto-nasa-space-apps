"use client";

import { useEffect, useRef } from "react";
import { conquistasUi as t, type Conquista } from "@/content/conquistas";
import s from "./explorar.module.css";

type Props = {
  conquista: Conquista;
  nova: boolean;
  onVerNoVisor: () => void;
  onFechar: () => void;
};

const Trofeu = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M7 4h10v4a5 5 0 0 1-10 0V4Z" />
    <path d="M7 6H4.5a2.5 2.5 0 0 0 2.6 3.6M17 6h2.5a2.5 2.5 0 0 1-2.6 3.6" />
    <path d="M12 13v3.5M8.5 20h7M9.5 20l.6-3.5h3.8l.6 3.5" />
  </svg>
);

export default function CardConquista({ conquista: c, nova, onVerNoVisor, onFechar }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // Esc fecha
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && onFechar();
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [onFechar]);

  const campo = (rotulo: string, valor: string | null) => (
    <div className={s.cqCampo}>
      <dt>{rotulo}</dt>
      <dd className={valor ? "" : s.cqPendente}>{valor ?? t.aConfirmar}</dd>
    </div>
  );

  return (
    <div ref={ref} className={s.conquista} role="dialog" aria-modal="false" aria-labelledby={`cq-${c.slug}`}>
      <button type="button" className={s.cqFechar} onClick={onFechar} aria-label={t.fechar}>
        ×
      </button>
      <div className={s.cqTopo}>
        <span className={s.cqTrofeu}>
          <Trofeu />
        </span>
        <div>
          <p className={s.cqKicker}>{nova ? t.nova : t.denovo}</p>
          <h2 id={`cq-${c.slug}`} className={s.cqTitulo}>
            {c.titulo}
          </h2>
        </div>
      </div>
      <p className={s.cqResumo}>{c.resumo}</p>

      <dl className={s.cqDados}>
        {campo(t.descobridor, c.descobridor)}
        {campo(t.epoca, c.epoca)}
      </dl>

      <h3 className={s.cqSub}>{t.contexto}</h3>
      <p className={s.cqTexto}>{c.contexto}</p>

      <h3 className={s.cqSub}>{t.fatos}</h3>
      <ul className={s.cqFatos}>
        {c.fatos.map((f) => (
          <li key={f}>{f}</li>
        ))}
      </ul>

      <div className={s.cqAcoes}>
        <button type="button" className={s.btnPrimario} onClick={onVerNoVisor}>
          {t.verNoVisor}
        </button>
        <button type="button" className={s.btnSecundario} onClick={onFechar}>
          {t.continuar}
        </button>
      </div>
    </div>
  );
}
