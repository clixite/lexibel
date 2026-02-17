export default function SkeletonDetailPage(): JSX.Element {
  return (
    <div className="animate-pulse">
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <div className="h-10 w-10 rounded-full bg-neutral-100" />
        <div className="h-8 w-48 bg-neutral-100 rounded" />
        <div className="h-6 w-20 bg-neutral-100 rounded" />
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-4 border-b">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-10 w-24 bg-neutral-100 rounded-t" />
        ))}
      </div>

      {/* Content */}
      <div className="rounded-lg border bg-white p-6">
        <div className="h-6 w-32 bg-neutral-100 rounded mb-4" />
        <div className="space-y-3">
          <div className="h-4 w-full bg-neutral-100 rounded" />
          <div className="h-4 w-5/6 bg-neutral-100 rounded" />
          <div className="h-4 w-4/6 bg-neutral-100 rounded" />
        </div>
      </div>
    </div>
  );
}
