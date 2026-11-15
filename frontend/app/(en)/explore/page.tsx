import Page from "../../_shared/explore";
import { metadataFor } from "../../../content/routes";

export const metadata = metadataFor("en", "explorar");

export default function Route() {
  return <Page locale="en" />;
}
