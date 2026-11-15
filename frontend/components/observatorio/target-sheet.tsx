"use client";

import { useEffect, useRef } from "react";
import { targetInfo } from "../../content/target-info";
import { useLocale } from "../ui/LocaleProvider";

/** Ficha do astro: contexto histórico, descoberta e o que observar. Abre como modal. */
export default function TargetSheet({ target, onClose }: { target: { slug: string; name: string } | null; onClose: () => void }) {
  const { locale, t } = useLocale();
  const dialog = useRef<HTMLDialogElement>(null);
  const info = target ? targetInfo[locale][target.slug] : undefined;

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (target && info && !element.open) element.showModal();
    if (!target && element.open) element.close();
  }, [target, info]);

  return (
    <dialog ref={dialog} className="target-sheet" aria-labelledby="target-sheet-title" onClose={onClose}
      onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}>
      {target && info && (
        <div className="target-sheet-body">
          <header className="target-sheet-head">
            <div>
              <p className="target-sheet-kicker">{info.tipo}</p>
              <h2 id="target-sheet-title">{target.name}</h2>
            </div>
            <button type="button" className="target-sheet-close" aria-label={t("Fechar ficha")} onClick={() => dialog.current?.close()}>×</button>
          </header>

          <dl className="target-sheet-facts">
            <div><dt>{t("Constelação")}</dt><dd>{info.constelacao}</dd></div>
            {info.distancia && <div><dt>{t("Distância")}</dt><dd>{info.distancia}</dd></div>}
            {info.descoberta && <div><dt>{t("Descoberta")}</dt><dd>{info.descoberta.quem} · {info.descoberta.quando}</dd></div>}
          </dl>

          {info.descoberta && <section>
            <h3>{t("Como foi descoberto")}</h3>
            <p>{info.descoberta.como}</p>
          </section>}
          <section>
            <h3>{t("Contexto histórico")}</h3>
            <p>{info.historia}</p>
          </section>
          {info.curiosidade && <section>
            <h3>{t("Curiosidade")}</h3>
            <p>{info.curiosidade}</p>
          </section>}
          <p className="target-sheet-look"><strong>{t("O que observar nas imagens:")}</strong> {info.oQueVer}</p>
        </div>
      )}
    </dialog>
  );
}
