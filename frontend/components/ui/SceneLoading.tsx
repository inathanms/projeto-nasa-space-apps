"use client";

import { useLocale } from "./LocaleProvider";
import RocketLoader from "./RocketLoader";

export default function SceneLoading() {
  const { t } = useLocale();
  return <div className="scene-loading" role="status"><RocketLoader label={t("Carregando a cena 3D…")} /></div>;
}
