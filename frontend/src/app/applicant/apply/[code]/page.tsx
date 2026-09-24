import ApplicationWizard from "../../../../components/application-wizard";

export default function ApplyPage({ params }: { params: { code: string } }) {
  return <ApplicationWizard code={params.code} />;
}
