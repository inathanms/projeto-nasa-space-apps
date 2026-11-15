import { Fragment } from "react";
import { dados } from "../../content/landing";
import Icon from "./Icons";
import s from "./landing.module.css";

export default function Dados() {
  return (
    <section id="dados" className={`${s.section} ${s.night2}`} aria-labelledby="dados-titulo" tabIndex={-1}>
      <div className={`wrap ${s.data}`}>
        <div>
          <p className={s.kicker}>{dados.kicker}</p>
          <h2 id="dados-titulo" className={s.h2}>{dados.titulo}</h2>
          <p className={s.lead}>{dados.lead}</p>
          <p className={s.credit}>{dados.credito}</p>
        </div>
        <div className={s.flow} role="list" aria-label={dados.rotuloFluxo}>
          {dados.fluxo.map((f, i) => (
            <Fragment key={f.titulo}>
              {i > 0 && (
                <span className={s.flowArrow} aria-hidden="true">→</span>
              )}
              <div className={s.flowBox} role="listitem">
                <Icon name={f.icone} />
                <strong>{f.titulo}</strong>
                <span>{f.texto}</span>
              </div>
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}
