import "server-only";

import lock from "../package-lock.json";
import python from "./backend-licenses.json";

export type PackageLicense = {
  name: string;
  version: string;
  license: string;
  dev: boolean;
  optional?: boolean;
  href: string;
};

type NpmEntry = Pick<PackageLicense, "version" | "license" | "optional"> & { dev?: boolean };

export const frontendLicenses: PackageLicense[] = Object.entries(lock.packages)
  .filter(([path]) => path.startsWith("node_modules/"))
  .map(([path, entry]) => {
    const name = path.split("node_modules/").at(-1) ?? path;
    const { version, license, dev = false, optional } = entry as NpmEntry;
    return { name, version, license, dev, optional, href: `https://www.npmjs.com/package/${name}/v/${version}` };
  });

export const backendLicenses: PackageLicense[] = python.map((entry) => ({
  ...entry,
  href: `https://pypi.org/project/${entry.name}/${entry.version}/#files`,
}));

export const fontLicenses = [
  { name: "Geist", license: "OFL-1.1", href: "https://github.com/vercel/geist-font/blob/main/OFL.txt" },
  { name: "Atkinson Hyperlegible", license: "OFL-1.1", href: "https://github.com/google/fonts/blob/main/ofl/atkinsonhyperlegible/OFL.txt" },
];

export const runtimeLicenses = [
  { name: "Node.js", license: "MIT", href: "https://github.com/nodejs/node/blob/main/LICENSE" },
  { name: "CPython 3.12", license: "PSF-2.0", href: "https://docs.python.org/3.12/license.html" },
  { name: "uv", license: "MIT OR Apache-2.0", href: "https://github.com/astral-sh/uv#license" },
];

export const externalCredits = [
  { name: "SPHEREx DR1 · NASA/JPL-Caltech/IPAC · IRSA", href: "https://www.ipac.caltech.edu/doi/10.26131/IRSA678" },
  { name: "SPHEREx QR3 · NASA/JPL-Caltech/IPAC · IRSA", href: "https://www.ipac.caltech.edu/doi/10.26131/IRSA662" },
  { name: "Blue Marble · NASA Earth Observatory", href: "https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/" },
  { name: "NASA Eyes", href: "https://eyes.nasa.gov/" },
  { name: "VLibras Widget · Governo Digital", href: "https://vlibras.gov.br/doc/widget/installation/webpageintegration.html" },
];
