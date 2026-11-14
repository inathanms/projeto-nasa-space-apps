"use client";

import type { KeyboardEvent } from "react";
import { explorar } from "@/content/explorar";
import { fmtDataUtc, fmtEpoca } from "@/lib/coords";
import type { Sequence, SequenceErrorKind } from "@/types/sequence";
import s from "./explorar.module.css";

export type Status = "vazio" | "carregando" | "pronto" | "erro";

type Props = {
  status: Status;
  seq: Sequence | null;
  idx: number;
  erro: SequenceErrorKind | null;
  lento: boolean;
  marcar: boolean;
  pendente: boolean;
  onTecla: (e: KeyboardEvent<HTMLDivElement>) => void;
  onAbrirExemplo: () => void;
  onBuscarAqui: () => void;
};

const nf = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

export default function Visor({ status, seq, idx, erro, lento, marcar, pendente, onTecla, onAbrirExemplo, onBuscarAqui }: Props) {
  const t = explorar.visor;
  const frame = status === "pronto" ? seq?.frames[idx] : undefined;

  return (
    <div className={s.visor} role="group" aria-label={t.rotulo} aria-busy={status === "carregando"} tabIndex={0} onKeyDown={onTecla}>
      <div className={s.visorTopo}>
        <span className={s.visorTitulo}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8" />
            <circle cx="12" cy="12" r="2.5" />
            <path d="M12 1v4M12 19v4M1 12h4M19 12h4" />
          </svg>
          {t.titulo}
        </span>
        <strong aria-live="polite">{frame ? fmtEpoca(frame.observed_at_utc) : "—"}</strong>
      </div>

      <div className={`${s.visorImg} ${pendente && status === "pronto" ? s.visorFora : ""}`}>
        {status === "pronto" && seq && (
          <>
            {seq.frames.map((f, i) => (
              <img
                key={f.frame_id}
                src={f.image_src}
                alt={i === idx ? `Recorte do céu observado em ${fmtDataUtc(f.observed_at_utc)}` : ""}
                className={s.quadro}
                style={{ opacity: i === idx ? 1 : 0 }}
                draggable={false}
              />
            ))}
            {marcar && frame?.marker && (
              <span className={s.marcador} style={{ left: `${frame.marker.x * 100}%`, top: `${frame.marker.y * 100}%` }} aria-hidden="true" />
            )}
            <span className={s.fovSelo}>{t.fov(seq.fov_arcmin)}</span>
            {seq.is_synthetic && <p className={s.sintetico}>{t.sintetico}</p>}
          </>
        )}

        {status === "vazio" && (
          <div className={s.visorMsg}>
            <p className={s.visorMsgTitulo}>{t.vazioTitulo}</p>
            <p>{t.vazioTexto}</p>
          </div>
        )}

        {status === "carregando" && (
          <div className={s.visorMsg} role="status">
            <span className={s.radar} aria-hidden="true" />
            <p>{t.carregando}</p>
            {lento && <p className={s.visorMsgSub}>{t.carregandoLento}</p>}
          </div>
        )}

        {status === "erro" && erro && (
          <div className={s.visorMsg} role="alert">
            <p className={s.visorMsgTitulo}>{explorar.erros[erro].titulo}</p>
            <p>{explorar.erros[erro].texto}</p>
            {erro !== "coordenada_invalida" && (
              <button type="button" className={s.btnSecundario} onClick={onAbrirExemplo}>
                {explorar.erros.abrirExemplo}
              </button>
            )}
          </div>
        )}

        {pendente && status !== "carregando" && (
          <div className={s.foraMira}>
            <span>{t.foraDeMira}</span>
            <button type="button" className={s.btnPrimario} onClick={onBuscarAqui}>
              {t.buscarAqui}
            </button>
          </div>
        )}
      </div>

      <div className={s.visorBase}>
        {frame ? (
          <>
            <span>
              λ {nf.format(frame.wavelength_um)} µm · {t.detector} {frame.detector}
            </span>
            {frame.source_url ? (
              <a href={frame.source_url} target="_blank" rel="noopener noreferrer">
                {t.fonte} ↗
              </a>
            ) : (
              <span className={s.semFonte}>{t.semFonte}</span>
            )}
          </>
        ) : (
          <span>&nbsp;</span>
        )}
      </div>
    </div>
  );
}
