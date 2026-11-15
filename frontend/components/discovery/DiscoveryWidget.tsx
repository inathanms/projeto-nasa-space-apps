"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { discoveryCopy, type DiscoveryCopy } from "../../content/discovery";
import {
  decDMS, MPC_EMAIL, MPC_OBSCODE_URL, MPC_PSV_URL, MPCHECKER_URL, mpcheckerUrl, mpcReport, raHMS, simbadUrl, useDiscoveryField, VSX_URL,
  type DiscoveryField, type ReportHeader,
} from "../../lib/discovery";
import { localizedHref } from "../../lib/i18n";
import { reducedMotion } from "../../lib/a11y";
import { useLocale } from "../ui/LocaleProvider";

type Step = "intro" | "how" | "kind" | "unsure" | "check" | "known" | "bright" | "unknown" | "form" | "report" | "done";
type Entry = { step: Step; answer?: string };
type Option = { label: keyof DiscoveryCopy; next: Step };

const OPTIONS: Partial<Record<Step, Option[]>> = {
  intro: [{ label: "introYes", next: "kind" }, { label: "introHow", next: "how" }],
  how: [{ label: "howNext", next: "kind" }],
  kind: [
    { label: "kindMove", next: "check" },
    { label: "kindNew", next: "check" },
    { label: "kindBright", next: "bright" },
    { label: "kindUnsure", next: "unsure" },
  ],
  unsure: [{ label: "unsureNext", next: "kind" }],
  check: [{ label: "checkKnown", next: "known" }, { label: "checkUnknown", next: "unknown" }],
  known: [{ label: "knownAgain", next: "kind" }],
  bright: [{ label: "knownAgain", next: "kind" }],
  unknown: [{ label: "unknownNext", next: "form" }],
  report: [{ label: "reportDone", next: "done" }],
};

const TOOL_ROUTES = ["/explorar/", "/observatorio/"];
const EMPTY_HEADER: ReportHeader = { code: "XXX", contact: "", observers: "", measurer: "", telescope: "" };

function CopyButton({ text, copy }: { text: string; copy: DiscoveryCopy }) {
  const [done, setDone] = useState(false);
  return (
    <button type="button" className="discovery-copy" onClick={() => {
      void navigator.clipboard?.writeText(text).then(() => {
        setDone(true);
        window.setTimeout(() => setDone(false), 1500);
      });
    }}>{done ? copy.copied : copy.copy}</button>
  );
}

/** Cartão com os dados do campo atual, no formato que o MPChecker e o SIMBAD pedem. */
function FieldCard({ field, copy }: { field: DiscoveryField | null; copy: DiscoveryCopy }) {
  if (!field) return <p className="discovery-muted">{copy.noField}</p>;
  const rows: [string, string][] = [
    ...(field.name ? [[copy.fieldName, field.name] as [string, string]] : []),
    ...field.times.map((iso) => [copy.fieldDate, iso.slice(0, 19).replace("T", " ")] as [string, string]),
    ["RA", raHMS(field.ra, 1)],
    ["Dec", decDMS(field.dec, 0)],
  ];
  return (
    <dl className="discovery-field">
      {rows.map(([label, value], index) => (
        <div key={`${label}-${index}`}>
          <dt>{label}</dt>
          <dd><span>{value}</span><CopyButton text={value} copy={copy} /></dd>
        </div>
      ))}
    </dl>
  );
}

/** SIMBAD pelo espelho de Harvard, com o servidor principal (França) como alternativa. */
function SimbadLinks({ field, copy }: { field: DiscoveryField; copy: DiscoveryCopy }) {
  return (
    <div className="discovery-links">
      <a className="discovery-link" href={simbadUrl(field, "harvard")} target="_blank" rel="noreferrer">{copy.simbadOpen}</a>
      <a className="discovery-link subtle" href={simbadUrl(field, "cds")} target="_blank" rel="noreferrer">{copy.simbadMirror}</a>
    </div>
  );
}

/** Widget "Achou algo diferente?": conversa guiada para checar e relatar uma possível descoberta. */
export default function DiscoveryWidget() {
  const { locale } = useLocale();
  const copy = discoveryCopy[locale];
  const pathname = usePathname();
  const field = useDiscoveryField();
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState<Entry[]>([{ step: "intro" }]);
  const [header, setHeader] = useState<ReportHeader>(EMPTY_HEADER);
  const [report, setReport] = useState("");
  const log = useRef<HTMLDivElement>(null);

  const here = localizedHref(locale, pathname);
  const visible = TOOL_ROUTES.some((route) => localizedHref(locale, route) === here);

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight, behavior: reducedMotion() ? "auto" : "smooth" });
  }, [history, open]);

  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [open]);

  if (!visible) return null;

  const current = history[history.length - 1];

  function go(next: Step, answer: string) {
    if (next === "report" && field) setReport(mpcReport(header, field));
    setHistory((entries) => [...entries.slice(0, -1), { ...entries[entries.length - 1], answer }, { step: next }]);
  }

  function message(step: Step): ReactNode {
    switch (step) {
      case "intro": return <p>{copy.intro}</p>;
      case "how": return <p>{copy.how}</p>;
      case "kind": return <p>{copy.kind}</p>;
      case "unsure": return <p>{copy.unsure}</p>;
      case "check": return <>
        <p>{copy.check}</p>
        <FieldCard field={field} copy={copy} />
        {field && field.times.length > 0 ? (
          <div className="discovery-links">
            {field.times.map((iso) => (
              <a key={iso} className="discovery-link" href={mpcheckerUrl(field, iso)} target="_blank" rel="noreferrer">
                {copy.checkOpenDate.replace("{date}", iso.slice(0, 10))}
              </a>
            ))}
            <a className="discovery-link subtle" href={MPCHECKER_URL} target="_blank" rel="noreferrer">{copy.checkOpenBlank}</a>
          </div>
        ) : <a className="discovery-link" href={MPCHECKER_URL} target="_blank" rel="noreferrer">{copy.checkOpenBlank}</a>}
        <p>{copy.checkSimbad}</p>
        {field && <SimbadLinks field={field} copy={copy} />}
        <p><strong>{copy.checkQuestion}</strong></p>
      </>;
      case "known": return <p>{copy.known}</p>;
      case "bright": return <>
        <p>{copy.bright}</p>
        <FieldCard field={field} copy={copy} />
        <a className="discovery-link" href={VSX_URL} target="_blank" rel="noreferrer">{copy.brightOpen}</a>
        {field && <SimbadLinks field={field} copy={copy} />}
      </>;
      case "unknown": return <>
        <p>{copy.unknown}</p>
        <ul className="discovery-rules">{copy.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
      </>;
      case "form": return <>
        <p>{copy.form}</p>
        <form className="discovery-form" onSubmit={(event) => { event.preventDefault(); if (current.step === "form") go("report", copy.formSubmit); }}>
          {([
            ["code", copy.formCode, "XXX"],
            ["contact", copy.formContact, "Ana Souza [ana@exemplo.com]"],
            ["observers", copy.formObservers, "A. Souza"],
            ["measurer", copy.formMeasurer, "A. Souza"],
            ["telescope", copy.formTelescope, "0.20-m f/5.0 reflector + CCD"],
          ] as [keyof ReportHeader, string, string][]).map(([key, label, placeholder]) => (
            <label key={key}>
              <span>{label}</span>
              <input value={header[key]} placeholder={placeholder} maxLength={key === "code" ? 3 : 120}
                disabled={current.step !== "form"}
                onChange={(event) => setHeader((previous) => ({ ...previous, [key]: event.target.value }))} />
            </label>
          ))}
          <a className="discovery-link" href={MPC_OBSCODE_URL} target="_blank" rel="noreferrer">{copy.formCodeHelp}</a>
          {current.step === "form" && <button type="submit" className="discovery-option primary" disabled={!field}>{copy.formSubmit}</button>}
        </form>
        {!field && <p className="discovery-muted">{copy.noField}</p>}
      </>;
      case "report": return <>
        <p>{copy.report}</p>
        <label className="discovery-report">
          <span>{copy.reportLabel}</span>
          <textarea value={report} onChange={(event) => setReport(event.target.value)} spellCheck={false} wrap="off" rows={10} />
        </label>
        <div className="discovery-actions">
          <CopyButton text={report} copy={copy} />
          <a className="discovery-link" href={`mailto:${MPC_EMAIL}?subject=${encodeURIComponent("MPC observations")}`}>{copy.reportEmail}</a>
          <a className="discovery-link" href={MPC_PSV_URL} target="_blank" rel="noreferrer">{copy.reportAdes}</a>
        </div>
        <p className="discovery-muted">{copy.reportNote}</p>
      </>;
      case "done": return <p>{copy.done}</p>;
    }
  }

  return (
    <div className="discovery" data-open={open}>
      {open && (
        <section className="discovery-panel" role="dialog" aria-label={copy.title}>
          <header className="discovery-head">
            <span className="discovery-avatar" aria-hidden="true">✦</span>
            <div>
              <strong>{copy.title}</strong>
              <small>{copy.subtitle}</small>
            </div>
            <button type="button" className="discovery-icon" onClick={() => { setHistory([{ step: "intro" }]); setReport(""); }}
              aria-label={copy.restart} title={copy.restart}>↺</button>
            <button type="button" className="discovery-icon" onClick={() => setOpen(false)} aria-label={copy.close}>×</button>
          </header>
          <div className="discovery-log" ref={log} role="log" aria-live="polite">
            {history.map((entry, index) => (
              <div key={index} className="discovery-turn">
                <div className="discovery-msg bot">{message(entry.step)}</div>
                {entry.answer && <div className="discovery-msg user" aria-label={copy.you}>{entry.answer}</div>}
              </div>
            ))}
          </div>
          {OPTIONS[current.step] && (
            <div className="discovery-options">
              {OPTIONS[current.step]!.map((option) => (
                <button key={option.label} type="button" className="discovery-option" onClick={() => go(option.next, copy[option.label] as string)}>
                  {copy[option.label] as string}
                </button>
              ))}
            </div>
          )}
        </section>
      )}
      <button type="button" className="discovery-bubble" data-tour="discovery-bubble" aria-expanded={open}
        aria-label={open ? copy.close : copy.open} onClick={() => setOpen((value) => !value)}>
        <span className="discovery-bubble-icon" aria-hidden="true">{open ? "×" : "✦"}</span>
        {!open && <span className="discovery-bubble-label">{copy.bubble}</span>}
      </button>
    </div>
  );
}
