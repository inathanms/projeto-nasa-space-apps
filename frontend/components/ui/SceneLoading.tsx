"use client";

import { useLocale } from "./LocaleProvider";

export default function SceneLoading() {
  const { t } = useLocale();
  return <div className="scene-loading" role="status">{t("Carregando a cena 3D…")}</div>;
}
