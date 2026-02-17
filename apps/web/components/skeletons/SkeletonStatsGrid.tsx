export default function SkeletonStatsGrid(): JSX.Element {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="rounded-lg border bg-white p-6 animate-pulse">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-full bg-neutral-100" />
            <div className="flex-1">
              <div className="h-7 w-16 bg-neutral-100 rounded mb-2" />
              <div className="h-4 w-24 bg-neutral-100 rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
