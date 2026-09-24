import { Shell } from "../../components/shell";

export default function ApplicantLayout({ children }: { children: React.ReactNode }) {
  return <Shell kind="applicant">{children}</Shell>;
}
