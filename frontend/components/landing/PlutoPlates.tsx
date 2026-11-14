import Image from "next/image";
import { hero } from "../../content/landing";
import styles from "./landing.module.css";

type Plate = typeof hero.fotos.foto1 | typeof hero.fotos.foto2;
type Point = Plate["plutao"];

const position = ({ x, y }: Point) => ({ left: `${x * 100}%`, top: `${y * 100}%` });

function DiscoveryPlate({ plate, previous }: { plate: Plate; previous?: Point }) {
  return (
    <div className={styles.plate} data-discovery={Boolean(previous)}>
      <span className={styles.plateDate}>{plate.titulo}</span>
      <div className={styles.exposure}>
        <Image src={plate.src} alt={plate.alt} width={720} height={720} loading="eager" />
        {previous && <span className={styles.previousPosition} style={position(previous)} aria-hidden="true" />}
        <span className={styles.plutoPosition} style={position(plate.plutao)} aria-hidden="true">
          {previous && <span className={styles.plutoLabel}>{hero.fotos.achou}</span>}
        </span>
      </div>
    </div>
  );
}

export default function PlutoPlates() {
  const { foto1, foto2, credito, creditoHref } = hero.fotos;

  return (
    <figure className={styles.discovery}>
      <div className={styles.plates}>
        <DiscoveryPlate plate={foto1} />
        <svg className={styles.plateArrow} viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M4 8h15l-3-3M20 16H5l3 3" />
        </svg>
        <DiscoveryPlate plate={foto2} previous={foto1.plutao} />
      </div>
      <figcaption>
        <a href={creditoHref}>{credito}</a>
      </figcaption>
    </figure>
  );
}
