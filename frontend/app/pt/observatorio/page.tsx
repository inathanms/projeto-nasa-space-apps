import Page from "../../_shared/observatory";
import { metadataFor } from "../../../content/routes";

export const metadata = metadataFor("pt", "observatorio");

export default function Route() {
  return <Page locale="pt" />;
}
