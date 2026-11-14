"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { conquistas, conquistasUi, RAIO_CONQUISTA, SINAL } from "@/content/conquistas";
import { explorar } from "@/content/explorar";
import { alvos, marca } from "@/content/landing";
import { clampDec, deltaRa, fmtDataUtc, fmtDec, validarCoordenadas, wrapRa } from "@/lib/coords";
import { buscarSequencia, carregarExemplo } from "@/lib/sequence";
import { SequenceError, type Sequence, type SequenceErrorKind } from "@/types/sequence";
import BarraTempo from "./BarraTempo";
import CardConquista from "./CardConquista";
import Palco from "./Palco";
import Visor, { type Status } from "./Visor";
import s from "./explorar.module.css";

const ALVO_PADRAO = "barnard";
const INTERVALO_PLAY = 700;
const TOLERANCIA = 0.05; // graus
const CHAVE_CONQUISTAS = "oxentech:conquistas";

const reduzMovimento = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const fmtCampo = (v: number) => String(Math.round(v * 10000) / 10000);

// ícones das abas (estilo da referência)
const ICONE_ABA: Record<string, React.ReactNode> = {
  barnard: (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="10" />
      <circle cx="16" cy="16" r="3" className="cheio" />
      <path d="M16 2v6M16 24v6M2 16h6M24 16h6" />
    </svg>
  ),
  wise0855: (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 3c1 8 4.5 11.5 13 13-8.5 1.5-12 5-13 13-1-8-4.5-11.5-13-13 8.5-1.5 12-5 13-13Z" />
    </svg>
  ),
  "eps-indi-b": (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <ellipse cx="16" cy="16" rx="13" ry="6" transform="rotate(-25 16 16)" />
      <circle cx="12" cy="17" r="3.2" className="cheio" />
      <circle cx="20" cy="15" r="2.6" className="cheio" />
    </svg>
  ),
  "rw-aur": (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="4.5" className="cheio" />
      <path d="M16 4v4M16 24v4M4 16h4M24 16h4M7.5 7.5l2.8 2.8M21.7 21.7l2.8 2.8M7.5 24.5l2.8-2.8M21.7 10.3l2.8-2.8" />
    </svg>
  ),
  "r-dra": (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M2 18c3-6 6-6 9 0s6 6 9 0 6-6 10 0" />
      <path d="M6 11c2-3 4-3 6 0" />
      <circle cx="25" cy="9" r="1.6" className="cheio" />
    </svg>
  ),
};

export default function Explorador() {
  const params = useSearchParams();
  const t = explorar;

  const inicial = alvos.find((a) => a.slug === ALVO_PADRAO)!;
  const [ra, setRa] = useState(inicial.raDeg ?? 0);
  const [dec, setDec] = useState(inicial.decDeg ?? 0);
  const [raTxt, setRaTxt] = useState(fmtCampo(ra));
  const [decTxt, setDecTxt] = useState(fmtCampo(dec));
  const [erroCampo, setErroCampo] = useState<"ra_deg" | "dec_deg" | null>(null);

  const [alvoSel, setAlvoSel] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("vazio");
  const [seq, setSeq] = useState<Sequence | null>(null);
  const [erro, setErro] = useState<SequenceErrorKind | null>(null);
  const [lento, setLento] = useState(false);

  const [idx, setIdx] = useState(0);
  const [tocando, setTocando] = useState(false);
  const [marcar, setMarcar] = useState(true);
  const [modoTempo, setModoTempo] = useState<"data" | "mjd">("data");
  const [configAberta, setConfigAberta] = useState(false);

  const busca = useRef<AbortController | null>(null);
  const anim = useRef(0);
  const [girando, setGirando] = useState(false);
  const raRef = useRef(ra);
  const decRef = useRef(dec);
  const configRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    raRef.current = ra;
    decRef.current = dec;
    setRaTxt(fmtCampo(ra));
    setDecTxt(fmtCampo(dec));
  }, [ra, dec]);

  const pararGiro = () => {
    cancelAnimationFrame(anim.current);
    setGirando(false);
  };

  // ---------- conquistas ----------
  // true quando a RA/Dec mudou pela mão da pessoa (arrastar, slider, teclado, formulário)
  const movidoPelaPessoa = useRef(false);
  const zonaAnterior = useRef<string | null>(null);
  const [achados, setAchados] = useState<string[]>([]);
  const [conquistaAberta, setConquistaAberta] = useState<{ slug: string; nova: boolean } | null>(null);
  const [anuncio, setAnuncio] = useState("");

  // progresso salvo só neste navegador (conveniência; a tela funciona sem)
  useEffect(() => {
    try {
      const v: unknown = JSON.parse(localStorage.getItem(CHAVE_CONQUISTAS) ?? "[]");
      if (Array.isArray(v)) setAchados(v.filter((x): x is string => typeof x === "string" && x in conquistas));
    } catch {
      /* sem armazenamento: segue sem progresso salvo */
    }
  }, []);

  // alvo mais próximo do ponto atual (distância angular em graus)
  const maisPerto = useMemo(() => {
    let melhor: { slug: string; dist: number } | null = null;
    for (const a of alvos) {
      if (a.raDeg === null || a.decDeg === null) continue;
      const dRa = deltaRa(ra, a.raDeg) * Math.cos((dec * Math.PI) / 180);
      const dist = Math.hypot(dRa, dec - a.decDeg);
      if (!melhor || dist < melhor.dist) melhor = { slug: a.slug, dist };
    }
    return melhor;
  }, [ra, dec]);

  const zona = maisPerto && maisPerto.dist < RAIO_CONQUISTA ? maisPerto.slug : null;

  // entrou na zona de um alvo movendo a Terra/satélite → conquista (mesmo sem "Buscar")
  useEffect(() => {
    if (zona === zonaAnterior.current) return;
    zonaAnterior.current = zona;
    if (!zona || !movidoPelaPessoa.current) return;
    const nova = !achados.includes(zona);
    setConquistaAberta({ slug: zona, nova });
    const nome = alvos.find((a) => a.slug === zona)?.nome ?? zona;
    setAnuncio(conquistasUi.anuncio(nome));
    if (nova) {
      const lista = [...achados, zona];
      setAchados(lista);
      try {
        localStorage.setItem(CHAVE_CONQUISTAS, JSON.stringify(lista));
      } catch {
        /* ignora */
      }
    }
  }, [zona, achados]);

  const nivelSinal =
    !zona && maisPerto && movidoPelaPessoa.current
      ? maisPerto.dist < SINAL.forte
        ? "forte"
        : maisPerto.dist < SINAL.medio
          ? "medio"
          : maisPerto.dist < SINAL.fraco
            ? "fraco"
            : null
      : null;

  // ---------- satélite gira suavemente até um alvo ----------
  const apontarPara = useCallback((raAlvo: number, decAlvo: number) => {
    cancelAnimationFrame(anim.current);
    if (reduzMovimento()) {
      setGirando(false);
      setRa(raAlvo);
      setDec(decAlvo);
      return;
    }
    const raIni = raRef.current;
    const decIni = decRef.current;
    const dRa = deltaRa(raAlvo, raIni);
    const inicio = performance.now();
    const dur = 1100;
    setGirando(true);
    const passo = (agora: number) => {
      const p = Math.min(1, (agora - inicio) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      setRa(wrapRa(raIni + dRa * e));
      setDec(decIni + (decAlvo - decIni) * e);
      if (p < 1) anim.current = requestAnimationFrame(passo);
      else setGirando(false);
    };
    anim.current = requestAnimationFrame(passo);
  }, []);

  // ---------- carregamento ----------
  const executar = useCallback(async (tarefa: (sinal: AbortSignal) => Promise<Sequence>) => {
    busca.current?.abort();
    const ctrl = new AbortController();
    busca.current = ctrl;
    setStatus("carregando");
    setErro(null);
    setLento(false);
    setTocando(false);
    const lentoTimer = window.setTimeout(() => setLento(true), 4000);
    try {
      const nova = await tarefa(ctrl.signal);
      if (ctrl.signal.aborted) return;
      setSeq(nova);
      setIdx(0);
      setStatus("pronto");
      setTocando(nova.frames.length > 1 && !reduzMovimento());
    } catch (e) {
      if (ctrl.signal.aborted) return;
      if (e instanceof SequenceError && e.field) setErroCampo(e.field);
      setSeq(null);
      setIdx(0);
      setErro(e instanceof SequenceError ? e.kind : "rede");
      setStatus("erro");
    } finally {
      clearTimeout(lentoTimer);
    }
  }, []);

  const selecionarAlvo = useCallback(
    (slug: string, pelaAba = true) => {
      const a = alvos.find((x) => x.slug === slug);
      if (!a) return;
      // ir pela aba/URL não conta como "achar"; digitar as coordenadas conta
      if (pelaAba) movidoPelaPessoa.current = false;
      setAlvoSel(slug);
      setErroCampo(null);
      if (a.raDeg !== null && a.decDeg !== null) apontarPara(a.raDeg, a.decDeg);
      void executar((sinal) => carregarExemplo(slug, sinal));
    },
    [apontarPara, executar],
  );

  const buscarPonto = useCallback(
    (raB: number, decB: number) => {
      const perto = alvos.find(
        (a) =>
          a.raDeg !== null &&
          a.decDeg !== null &&
          Math.abs(deltaRa(a.raDeg, raB)) < TOLERANCIA &&
          Math.abs(a.decDeg - decB) < TOLERANCIA,
      );
      if (perto) return selecionarAlvo(perto.slug, false);
      setAlvoSel(null);
      void executar((sinal) => buscarSequencia(raB, decB, sinal));
    },
    [executar, selecionarAlvo],
  );

  // Depende do TEXTO de ?alvo= (não do objeto params, que pode mudar de identidade a cada
  // renderização no modo dev e causar laço de atualizações).
  const alvoUrl = params.get("alvo");
  useEffect(() => {
    selecionarAlvo(alvoUrl && alvos.some((a) => a.slug === alvoUrl) ? alvoUrl : ALVO_PADRAO);
  }, [alvoUrl, selecionarAlvo]);

  // limpeza só ao sair da tela
  useEffect(
    () => () => {
      busca.current?.abort();
      cancelAnimationFrame(anim.current);
    },
    [],
  );

  // ---------- play ----------
  const total = seq?.frames.length ?? 0;
  useEffect(() => {
    if (!tocando || total < 2) return;
    const id = window.setInterval(() => setIdx((i) => (i + 1) % total), INTERVALO_PLAY);
    return () => clearInterval(id);
  }, [tocando, total]);

  const trocar = (passo: number) => {
    if (total < 2) return;
    setTocando(false);
    setIdx((i) => (i + passo + total) % total);
  };

  function teclaVisor(e: KeyboardEvent<HTMLDivElement>) {
    if (e.target !== e.currentTarget) return;
    if (e.key === " ") {
      e.preventDefault();
      if (total > 1) setTocando((v) => !v);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      trocar(-1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      trocar(1);
    }
  }

  // ---------- configurações (popover) ----------
  useEffect(() => {
    if (!configAberta) return;
    const fora = (e: MouseEvent) => {
      if (configRef.current && !configRef.current.contains(e.target as Node)) setConfigAberta(false);
    };
    const esc = (e: globalThis.KeyboardEvent) => e.key === "Escape" && setConfigAberta(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [configAberta]);

  function enviar(e: FormEvent) {
    e.preventDefault();
    const v = validarCoordenadas(raTxt, decTxt);
    if (!v.ok) {
      setErroCampo(v.field);
      return;
    }
    setErroCampo(null);
    pararGiro();
    movidoPelaPessoa.current = true;
    setRa(v.ra);
    setDec(v.dec);
    setConfigAberta(false);
    buscarPonto(v.ra, v.dec);
  }

  const moverRa = (v: number) => {
    pararGiro();
    movidoPelaPessoa.current = true;
    setRa(v);
  };
  const moverDec = (v: number) => {
    pararGiro();
    movidoPelaPessoa.current = true;
    setDec(clampDec(v));
  };

  const pendente =
    status !== "carregando" &&
    !girando &&
    (!seq || Math.abs(deltaRa(ra, seq.ra_deg)) > TOLERANCIA || Math.abs(dec - seq.dec_deg) > TOLERANCIA);

  const frame = status === "pronto" ? seq?.frames[idx] : undefined;
  const pctDec = ((dec + 90) / 180) * 100;

  return (
    <div className={`${s.app} bg-universo`}>
      <h1 className="sr-only">{t.tituloSr}</h1>

      {/* ---------- topo ---------- */}
      <header className={s.topo}>
        <Link href="/" className={s.marca} aria-label={t.voltarRotulo}>
          <img src={marca.logoMark} alt="" width={52} height={52} />
          <span>
            <strong>
              {marca.nome}
              <em>{marca.nomeDestaque}</em>
            </strong>
            <small>{t.marcaSub}</small>
          </span>
        </Link>

        <nav className={s.abas} aria-label={t.abasRotulo}>
          {alvos.map((a) => (
            <button
              key={a.slug}
              type="button"
              className={`${s.aba} ${alvoSel === a.slug ? s.abaAtiva : ""}`}
              aria-pressed={alvoSel === a.slug}
              onClick={() => selecionarAlvo(a.slug)}
              title={a.texto}
            >
              {ICONE_ABA[a.slug]}
              <span>{t.nomeCurto[a.slug] ?? a.nome}</span>
              {achados.includes(a.slug) && (
                <span className={s.abaSelo} title={conquistasUi.abaConquistada}>
                  <svg viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
                  </svg>
                  <span className="sr-only">{conquistasUi.abaConquistada}</span>
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className={s.configWrap} ref={configRef}>
          <p className={s.placar} aria-label={conquistasUi.contadorRotulo(achados.length, alvos.length)}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 4h10v4a5 5 0 0 1-10 0V4Z" />
              <path d="M7 6H4.5a2.5 2.5 0 0 0 2.6 3.6M17 6h2.5a2.5 2.5 0 0 1-2.6 3.6" />
              <path d="M12 13v3.5M8.5 20h7" />
            </svg>
            <span aria-hidden="true">{conquistasUi.contador(achados.length, alvos.length)}</span>
          </p>
          <button
            type="button"
            className={s.btnConfig}
            aria-label={t.config.abrir}
            aria-expanded={configAberta}
            aria-controls="painel-config"
            onClick={() => setConfigAberta((v) => !v)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="3.2" />
              <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
            </svg>
          </button>
          {configAberta && (
            <div id="painel-config" className={s.config} role="dialog" aria-label={t.config.titulo}>
              <h2>{t.config.titulo}</h2>
              <label className={s.check}>
                <input type="checkbox" checked={marcar} onChange={(e) => setMarcar(e.target.checked)} />
                {t.config.marcar}
              </label>
              <form onSubmit={enviar} noValidate>
                <h3>{t.config.coordTitulo}</h3>
                <div className={s.campos}>
                  <label className={s.campo}>
                    <span>{t.config.raRotulo}</span>
                    <input
                      inputMode="decimal"
                      value={raTxt}
                      onChange={(e) => setRaTxt(e.target.value)}
                      aria-invalid={erroCampo === "ra_deg"}
                      aria-describedby="ra-ajuda"
                    />
                    <small id="ra-ajuda">{erroCampo === "ra_deg" ? t.config.erroRa : t.config.raAjuda}</small>
                  </label>
                  <label className={s.campo}>
                    <span>{t.config.decRotulo}</span>
                    <input
                      inputMode="decimal"
                      value={decTxt}
                      onChange={(e) => setDecTxt(e.target.value)}
                      aria-invalid={erroCampo === "dec_deg"}
                      aria-describedby="dec-ajuda"
                    />
                    <small id="dec-ajuda">{erroCampo === "dec_deg" ? t.config.erroDec : t.config.decAjuda}</small>
                  </label>
                </div>
                <button type="submit" className={s.btnPrimario}>
                  {t.config.buscar}
                </button>
              </form>
              <p className={s.atalhos}>{t.config.atalhos}</p>
            </div>
          )}
        </div>
      </header>

      {/* ---------- palco: Terra + satélite ---------- */}
      <main className={s.palcoWrap}>
        <Palco ra={ra} dec={dec} onRa={moverRa} onDec={moverDec} />

        {nivelSinal && !conquistaAberta && (
          <p className={`${s.sinal} ${s[`sinal_${nivelSinal}`]}`}>
            <span className={s.sinalBarras} aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            {conquistasUi.sinal.rotulo}: <strong>{conquistasUi.sinal[nivelSinal]}</strong>
            <span className={s.sinalDica}>{conquistasUi.sinal.dica}</span>
          </p>
        )}

        {conquistaAberta && conquistas[conquistaAberta.slug] && (
          <CardConquista
            conquista={conquistas[conquistaAberta.slug]}
            nova={conquistaAberta.nova}
            onVerNoVisor={() => {
              const slug = conquistaAberta.slug;
              setConquistaAberta(null);
              selecionarAlvo(slug, false);
            }}
            onFechar={() => setConquistaAberta(null)}
          />
        )}
        <p className="sr-only" aria-live="polite">
          {anuncio}
        </p>
      </main>

      {/* ---------- coluna direita: visor + inclinação + detalhes ---------- */}
      <aside className={s.lateral}>
        <Visor
          status={status}
          seq={seq}
          idx={idx}
          erro={erro}
          lento={lento}
          marcar={marcar}
          pendente={pendente}
          onTecla={teclaVisor}
          onAbrirExemplo={() => selecionarAlvo(ALVO_PADRAO)}
          onBuscarAqui={() => buscarPonto(ra, dec)}
        />

        <section className={`${s.painel} ${s.inclinacao}`} aria-labelledby="incl-titulo">
          <div className={s.inclTopo}>
            <svg viewBox="0 0 24 24" aria-hidden="true" className={s.inclIcone}>
              <path d="M3 20h18M3 20 15 6" />
              <path d="M9 20a7 7 0 0 0-2-4.8" />
            </svg>
            <h2 id="incl-titulo">
              {t.inclinacao.titulo} <small>{t.inclinacao.sub}</small>
            </h2>
            <output className={s.inclValor} htmlFor="incl-range">
              {fmtDec(dec, 1)}
            </output>
          </div>
          <input
            id="incl-range"
            type="range"
            min={-90}
            max={90}
            step={0.1}
            value={Math.round(dec * 10) / 10}
            onChange={(e) => moverDec(Number(e.target.value))}
            aria-label={t.inclinacao.rotulo}
            aria-valuetext={`Dec ${fmtDec(dec, 1)}`}
            className={s.range}
            style={{ ["--p" as string]: `${pctDec}%` }}
          />
          <div className={s.inclEscala} aria-hidden="true">
            <span>−90°</span>
            <span>0°</span>
            <span>+90°</span>
          </div>
        </section>

        {frame && seq && (
          <details className={`${s.painel} ${s.detalhes}`}>
            <summary>{t.detalhes.titulo}</summary>
            <dl>
              <dt>{t.detalhes.colecao}</dt>
              <dd>{frame.collection}</dd>
              <dt>{t.detalhes.quadro}</dt>
              <dd className={s.mono}>{frame.frame_id}</dd>
              <dt>{t.detalhes.observado}</dt>
              <dd>{fmtDataUtc(frame.observed_at_utc)}</dd>
              <dt>{t.detalhes.comprimento}</dt>
              <dd>{frame.wavelength_um} µm</dd>
              <dt>{t.detalhes.largura}</dt>
              <dd>{frame.bandwidth_um} µm</dd>
              <dt>{t.detalhes.detector}</dt>
              <dd>{frame.detector}</dd>
              <dt>{t.detalhes.cobertura}</dt>
              <dd>{Math.round(frame.valid_fraction * 100)}%</dd>
              <dt>{t.detalhes.calibracao}</dt>
              <dd>{frame.calibration_version}</dd>
              <dt>{t.detalhes.processamento}</dt>
              <dd>{seq.processing_version}</dd>
              <dt>{t.detalhes.obtido}</dt>
              <dd>{fmtDataUtc(seq.fetched_at_utc)}</dd>
            </dl>
            {(frame.source_url || frame.cutout_url) && (
              <p className={s.links}>
                {frame.source_url && (
                  <a href={frame.source_url} target="_blank" rel="noopener noreferrer">
                    {t.detalhes.original}
                  </a>
                )}
                {frame.cutout_url && (
                  <a href={frame.cutout_url} target="_blank" rel="noopener noreferrer">
                    {t.detalhes.recorte}
                  </a>
                )}
              </p>
            )}
          </details>
        )}
      </aside>

      {/* ---------- barra de tempo ---------- */}
      <div className={s.rodape}>
        <BarraTempo
          seq={status === "pronto" ? seq : null}
          idx={idx}
          tocando={tocando}
          modo={modoTempo}
          onModo={setModoTempo}
          onIdx={(i) => {
            setTocando(false);
            setIdx(i);
          }}
          onPasso={trocar}
          onTocar={() => setTocando((v) => !v)}
        />
        <p className={s.creditos}>{t.creditos}</p>
      </div>
    </div>
  );
}
