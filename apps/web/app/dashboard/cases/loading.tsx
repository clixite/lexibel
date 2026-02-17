import SkeletonTable from "@/components/skeletons/SkeletonTable";

export default function CasesLoading() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-neutral-900">Dossiers</h1>
        </div>
      </div>
      <SkeletonTable />
    </div>
  );
}
