export default function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg shadow-subtle p-6 animate-pulse">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-neutral-100 rounded-full" />
          <div className="flex-1 space-y-2">
            <div className="h-6 bg-neutral-100 rounded w-48" />
            <div className="h-4 bg-neutral-100 rounded w-32" />
          </div>
        </div>

        {/* Content lines */}
        <div className="space-y-3 pt-4">
          <div className="h-4 bg-neutral-100 rounded w-full" />
          <div className="h-4 bg-neutral-100 rounded w-5/6" />
          <div className="h-4 bg-neutral-100 rounded w-4/6" />
        </div>

        {/* Footer */}
        <div className="pt-4 flex gap-3">
          <div className="h-9 bg-neutral-100 rounded w-24" />
          <div className="h-9 bg-neutral-100 rounded w-24" />
        </div>
      </div>
    </div>
  );
}
