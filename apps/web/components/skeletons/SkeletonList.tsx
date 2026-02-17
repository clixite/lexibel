export default function SkeletonList() {
  return (
    <div className="space-y-3">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="bg-white rounded-lg shadow-subtle border border-neutral-100 p-5 animate-pulse"
        >
          <div className="flex items-start gap-4">
            {/* Icon placeholder */}
            <div className="w-10 h-10 bg-neutral-100 rounded-lg flex-shrink-0" />

            {/* Content */}
            <div className="flex-1 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-neutral-100 rounded w-3/4" />
                  <div className="h-3 bg-neutral-100 rounded w-1/2" />
                </div>
                <div className="h-3 bg-neutral-100 rounded w-16" />
              </div>

              {/* Body */}
              <div className="space-y-2">
                <div className="h-3 bg-neutral-100 rounded w-full" />
                <div className="h-3 bg-neutral-100 rounded w-5/6" />
              </div>

              {/* Footer */}
              <div className="flex items-center gap-2 pt-2">
                <div className="h-2 bg-neutral-100 rounded flex-1 max-w-[200px]" />
                <div className="h-4 bg-neutral-100 rounded w-12" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
