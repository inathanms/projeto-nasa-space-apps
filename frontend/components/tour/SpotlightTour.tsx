"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { usePathname, useRouter } from "next/navigation";
import type { TourStep } from "../../content/tutorial";
import { localizedHref } from "../../lib/i18n";
import { reducedMotion } from "../../lib/a11y";
import { useLocale } from "../ui/LocaleProvider";

type Rect = { top: number; left: number; width: number; height: number };

const PAD = 8;
const GAP = 12;
const EDGE = 12;
const MAX_TIP = 340;

export const samePath = (a: string, b: string) => a.replace(/\/+$/, "") === b.replace(/\/+$/, "");

/** Tutorial guiado: escurece a tela, destaca o alvo de cada passo e troca de rota quando preciso. */
export default function SpotlightTour({ steps, start = 0, onClose }: { steps: TourStep[]; start?: number; onClose: () => void }) {
  const [index, setIndex] = useState(start);
  const [rect, setRect] = useState<Rect | null>(null);
  const [rectFor, setRectFor] = useState(-1);
  const [tick, setTick] = useState(0);
  const [tip, setTip] = useState({ left: EDGE, top: EDGE, width: MAX_TIP });
  const tipRef = useRef<HTMLDivElement>(null);
  const scrolledFor = useRef(-1);
  const router = useRouter();
  const { locale, t } = useLocale();
  // Rota atual normalizada para o idioma (ex.: /explorar → /explore/ no inglês).
  const pathname = localizedHref(locale, usePathname());

  const step = steps[index];
  const isLast = index === steps.length - 1;
  const onRoute = !step?.route || samePath(pathname, step.route);
  const ready = rectFor === index;

  // Troca de tela quando o passo pertence a outra rota.
  useEffect(() => {
    if (step?.route && !samePath(pathname, step.route)) router.push(step.route);
  }, [index, step?.route, pathname, router]);

  // Localiza o alvo (com novas tentativas: a rota e os componentes carregam de forma assíncrona).
  useEffect(() => {
    if (!step || !onRoute) return;
    if (!step.target) {
      setRect(null);
      setRectFor(index);
      return;
    }
    let cancelled = false;
    let tries = 0;
    let settle: number | undefined;
    const timer = window.setInterval(() => {
      const element = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      if (element) {
        window.clearInterval(timer);
        const firstTime = scrolledFor.current !== index;
        if (firstTime) {
          scrolledFor.current = index;
          element.scrollIntoView({ block: "center", inline: "nearest", behavior: reducedMotion() ? "auto" : "smooth" });
        }
        settle = window.setTimeout(() => {
          if (cancelled) return;
          const box = element.getBoundingClientRect();
          setRect({ top: box.top, left: box.left, width: box.width, height: box.height });
          setRectFor(index);
        }, firstTime ? 380 : 0);
      } else if (++tries > 30) {
        // ~2 s sem achar o alvo: segue com o balão centralizado.
        window.clearInterval(timer);
        setRect(null);
        setRectFor(index);
      }
    }, 60);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(settle);
    };
  }, [index, step, onRoute, tick]);

  // Rolagem, redimensionamento e teclado.
  useEffect(() => {
    const remeasure = () => setTick((value) => value + 1);
    const keys = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      else if (event.key === "ArrowRight") setIndex((value) => Math.min(value + 1, steps.length - 1));
      else if (event.key === "ArrowLeft") setIndex((value) => Math.max(value - 1, 0));
    };
    window.addEventListener("resize", remeasure);
    window.addEventListener("scroll", remeasure, true);
    window.addEventListener("keydown", keys);
    return () => {
      window.removeEventListener("resize", remeasure);
      window.removeEventListener("scroll", remeasure, true);
      window.removeEventListener("keydown", keys);
    };
  }, [onClose, steps.length]);

  // Posiciona o balão abaixo do alvo, ou acima, ou preso na base da tela se nenhum couber.
  useLayoutEffect(() => {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const width = Math.min(MAX_TIP, vw - EDGE * 2);
    const height = tipRef.current?.offsetHeight ?? 200;
    if (!rect) {
      setTip({ width, left: (vw - width) / 2, top: Math.max(EDGE, (vh - height) / 2) });
      return;
    }
    const left = Math.max(EDGE, Math.min(rect.left + rect.width / 2 - width / 2, vw - width - EDGE));
    const below = rect.top + rect.height + PAD + GAP;
    const above = rect.top - PAD - GAP - height;
    const top = below + height <= vh - EDGE ? below : above >= EDGE ? above : vh - height - EDGE;
    setTip({ width, left, top });
  }, [rect, tick, index]);

  // Leva o foco ao balão a cada passo (leitores de tela anunciam o novo conteúdo).
  useEffect(() => {
    if (ready) tipRef.current?.focus({ preventScroll: true });
  }, [ready, index]);

  if (!step) return null;
  const spot = rect && onRoute;

  return createPortal(
    <div className="tour-root">
      {spot
        ? <div className="tour-spot" style={{ top: rect.top - PAD, left: rect.left - PAD, width: rect.width + PAD * 2, height: rect.height + PAD * 2 }} />
        : <div className="tour-dim" />}
      <div ref={tipRef} className="tour-tip" role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-body" tabIndex={-1}
        style={{ left: tip.left, top: tip.top, width: tip.width, opacity: ready ? 1 : 0, pointerEvents: ready ? "auto" : "none" }}>
        <p className="tour-tip-step">{t("Passo {step} de {total}", { step: index + 1, total: steps.length })}</p>
        <h2 id="tour-title" className="tour-tip-title">{step.title}</h2>
        <p id="tour-body" className="tour-tip-body">{step.body}</p>
        <div className="tour-tip-actions">
          <button type="button" className="tour-skip" onClick={onClose}>{t("Pular")}</button>
          <div className="tour-tip-nav">
            {index > 0 && <button type="button" className="button secondary" onClick={() => setIndex((value) => value - 1)}>{t("Voltar")}</button>}
            {isLast
              ? <button type="button" className="button primary" onClick={onClose}>{t("Concluir")}</button>
              : <button type="button" className="button primary" onClick={() => setIndex((value) => value + 1)}>{t("Próximo")}</button>}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
