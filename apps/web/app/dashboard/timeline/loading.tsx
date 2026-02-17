import SkeletonList from "@/components/skeletons/SkeletonList";

export default function TimelineLoading() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Chronologie</h1>
      </div>
      <SkeletonList />
    </div>
  );
}
