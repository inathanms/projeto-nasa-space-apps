import Tumbleweed from "./Tumbleweed";
import styles from "./landing.module.css";

export default function HeroArt() {
  return (
    <div className={styles.heroArt} aria-hidden="true">
      <svg className={styles.landscape} viewBox="0 510 1440 350" focusable="false" preserveAspectRatio="xMaxYMax slice">
      <path d="M0 770 C200 730 380 740 560 770 S900 800 1100 750 S1360 720 1440 730 L1440 860 L0 860Z" fill="#c75636"/>
      <path d="M0 805 C240 775 420 790 620 810 S1000 825 1200 790 S1400 785 1440 790 L1440 860 L0 860Z" fill="#e0703a"/>
      <path d="M0 835 C300 815 600 830 900 815 S1300 800 1440 810 L1440 860 L0 860Z" fill="#eb8c3e"/>
      <g fill="#2b7a6b" transform="translate(1180,540)">
      <rect x="40" y="0" width="56" height="260" rx="28"/><rect x="0" y="70" width="34" height="110" rx="17"/><rect x="0" y="150" width="60" height="30" rx="15"/>
      <rect x="102" y="40" width="34" height="110" rx="17"/><rect x="80" y="120" width="56" height="30" rx="15"/>
      <g stroke="#0e2e2b" strokeWidth="2" fill="none"><path d="M68 30 V120 L56 132 V230"/><path d="M80 60 V100"/><circle cx="68" cy="30" r="4"/><circle cx="80" cy="60" r="4"/></g>
      </g>
      </svg>
      <Tumbleweed />
    </div>
  );
}
