import type { Metadata } from "next";
import AnimateClient from "./AnimateClient";

export const metadata: Metadata = {
  title: "Animer vos photos — Flashback Restore",
  description: "Donnez vie à vos souvenirs avec des micro-expressions naturelles.",
};

export default function Page() {
  return <AnimateClient />;
}
