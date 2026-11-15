import Page from "../_shared/home";
import { metadataFor } from "../../content/routes";

export const metadata = metadataFor("pt", "home");

export default function Route() {
  return <Page locale="pt" />;
}
