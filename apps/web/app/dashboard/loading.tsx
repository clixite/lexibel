import SkeletonStatsGrid from "@/components/skeletons/SkeletonStatsGrid";

export default function DashboardLoading() {
  return (
    <div>
      {/* Welcome header skeleton */}
      <div className="mb-8">
        <div className="h-8 w-64 bg-neutral-100 rounded mb-2 animate-pulse" />
        <div className="h-4 w-40 bg-neutral-100 rounded animate-pulse" />
      </div>

      {/* Stats Grid */}
      <div className="mb-8">
        <SkeletonStatsGrid />
      </div>

      {/* Three-column grid skeletons */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="card">
            <div className="h-6 w-32 bg-neutral-100 rounded mb-5 animate-pulse" />
            <div className="space-y-4">
              {[1, 2, 3, 4].map((j) => (
                <div key={j} className="flex items-start gap-3">
                  <div className="h-2.5 w-2.5 rounded-full bg-neutral-100 mt-1.5 flex-shrink-0 animate-pulse" />
                  <div className="flex-1">
                    <div className="h-4 w-full bg-neutral-100 rounded mb-2 animate-pulse" />
                    <div className="h-3 w-24 bg-neutral-100 rounded animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
