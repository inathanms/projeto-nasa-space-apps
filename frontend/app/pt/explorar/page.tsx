import Page from "../../_shared/explore";
import { metadataFor } from "../../../content/routes";

export const metadata = metadataFor("pt", "explorar");

export default function Route() {
  return <Page locale="pt" />;
}
