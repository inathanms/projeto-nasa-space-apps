import { backendLicenses, externalCredits, fontLicenses, frontendLicenses, runtimeLicenses, type PackageLicense } from "../../content/licenses";
import { translators, type Locale } from "../../lib/i18n";
import "./licenses.css";

function PackageTable({ packages, locale, label }: { packages: PackageLicense[]; locale: Locale; label: string }) {
  const t = translators[locale];
  return (
    <table className="license-table">
      <caption className="sr-only">{label}</caption>
      <thead>
        <tr>
          <th scope="col">{t("Pacote")}</th>
          <th scope="col">{t("Versão")}</th>
          <th scope="col">{t("Licença declarada")}</th>
        </tr>
      </thead>
      <tbody>
        {packages.map(({ name, version, license, dev, optional, href }) => (
          <tr key={href}>
            <th scope="row">
              <a href={href}>{name}</a>
              {dev && <small>{t("Desenvolvimento")}</small>}
              {optional && <small>{t("Opcional")}</small>}
            </th>
            <td>{version}</td>
            <td>{license}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function LicensesPage({ locale }: { locale: Locale }) {
  const t = translators[locale];
  const frontend = t("Frontend e ferramentas de build");
  const backend = t("Backend e ferramentas de desenvolvimento");
  return (
    <main id="conteudo" className="shell licenses-page" tabIndex={-1}>
      <header>
        <h1>{t("Licenças de código aberto")}</h1>
        <p>{t("Licenças, avisos e créditos dos componentes de terceiros usados pelo SPHEREye.")}</p>
        <a className="button secondary" href="/licenses/third-party-notices.txt" download>
          {t("Baixar avisos de terceiros")}
        </a>
      </header>

      <section aria-labelledby="licenses-fonts">
        <h2 id="licenses-fonts">{t("Fontes tipográficas")}</h2>
        <ul className="license-credits">
          {fontLicenses.map(({ name, license, href }) => (
            <li key={name}><a href={href}>{name}</a><span>{license}</span></li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="licenses-dependencies">
        <h2 id="licenses-dependencies">{t("Dependências")}</h2>
        <p>{t("As versões vêm dos arquivos de dependências do projeto. Os links levam à distribuição correspondente, onde ficam os avisos de componentes empacotados e variações de plataforma.")}</p>
        <details className="license-dependencies">
          <summary>{frontend} <span>({frontendLicenses.length})</span></summary>
          <PackageTable packages={frontendLicenses} locale={locale} label={frontend} />
        </details>
        <details className="license-dependencies">
          <summary>{backend} <span>({backendLicenses.length})</span></summary>
          <p>{t("Ambiente de referência: Python 3.12 no Linux, conforme o build do backend.")}</p>
          <PackageTable packages={backendLicenses} locale={locale} label={backend} />
        </details>
      </section>

      <section aria-labelledby="licenses-runtime">
        <h2 id="licenses-runtime">{t("Ambiente de execução e build")}</h2>
        <ul className="license-credits">
          {runtimeLicenses.map(({ name, license, href }) => (
            <li key={name}><a href={href}>{name}</a><span>{license}</span></li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="licenses-credits">
        <h2 id="licenses-credits">{t("Dados, imagens e serviços externos")}</h2>
        <ul className="license-credits">
          {externalCredits.map(({ name, href }) => <li key={name}><a href={href}>{name}</a></li>)}
          <li><a href="https://github.com/spbgovbr-vlibras/vlibras-web-browsers">VLibras Web Browsers</a><span>LGPL-3.0</span></li>
        </ul>
      </section>
    </main>
  );
}
