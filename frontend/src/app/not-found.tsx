import type { Metadata } from "next";
import { ErrorPage } from "@/components/common/error-screen";

export const metadata: Metadata = { title: "404" };

export default function NotFound() {
  return <ErrorPage variant="notFound" />;
}
