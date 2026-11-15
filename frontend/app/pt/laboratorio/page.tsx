import Page from "../../_shared/lab";
import { metadataFor } from "../../../content/routes";

export const metadata = metadataFor("pt", "laboratorio");

export default function Route() {
  return <Page locale="pt" />;
}
