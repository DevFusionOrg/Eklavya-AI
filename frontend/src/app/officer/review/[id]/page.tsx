import ReviewWorkspace from "../../../../components/review-workspace";

export default function OfficerReviewPage({ params }: { params: { id: string } }) {
  return <ReviewWorkspace applicationId={params.id} />;
}
