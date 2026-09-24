import { Shell } from "../../components/shell";

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  return <Shell kind="officer">{children}</Shell>;
}
