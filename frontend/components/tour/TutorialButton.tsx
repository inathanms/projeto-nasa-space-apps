"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { TUTORIAL_KEY, tutorialSteps } from "../../content/tutorial";
import SpotlightTour, { samePath } from "./SpotlightTour";

/** Botão "? Tutorial" do cabeçalho. Só aparece nas telas de ferramenta e abre sozinho na primeira visita. */
export default function TutorialButton() {
  const pathname = usePathname();
  const [start, setStart] = useState<number | null>(null);
  const firstStepHere = tutorialSteps.findIndex((step) => step.route && samePath(step.route, pathname));
  const isTool = firstStepHere >= 0;

  useEffect(() => {
    if (!isTool || start !== null) return;
    try {
      if (window.localStorage.getItem(TUTORIAL_KEY)) return;
    } catch {
      return; // Sem armazenamento: não abre sozinho para não repetir a cada visita.
    }
    setStart(firstStepHere);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só ao chegar numa tela de ferramenta
  }, [isTool]);

  const close = useCallback(() => {
    setStart(null);
    try {
      window.localStorage.setItem(TUTORIAL_KEY, "visto");
    } catch { /* O tutorial continua disponível pelo botão. */ }
  }, []);

  return (
    <>
      {isTool && (
        <button type="button" className="tour-help" data-tour="tour-help" onClick={() => setStart(firstStepHere)}>
          <span aria-hidden="true">?</span> Tutorial
        </button>
      )}
      {start !== null && <SpotlightTour steps={tutorialSteps} start={start} onClose={close} />}
    </>
  );
}
