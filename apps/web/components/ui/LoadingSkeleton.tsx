"use client";

export interface LoadingSkeletonProps {
  variant?: 'card' | 'table' | 'list' | 'stats';
}

export default function LoadingSkeleton({ variant = 'card' }: LoadingSkeletonProps) {
  if (variant === 'card') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded shadow-sm p-6 animate-pulse">
            <div className="h-4 bg-neutral-100 rounded w-3/4 mb-4"></div>
            <div className="h-8 bg-neutral-100 rounded w-1/2 mb-3"></div>
            <div className="h-3 bg-neutral-100 rounded w-full mb-2"></div>
            <div className="h-3 bg-neutral-100 rounded w-5/6"></div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className="bg-white rounded shadow-sm overflow-hidden">
        <div className="p-4 border-b border-neutral-200 animate-pulse">
          <div className="h-4 bg-neutral-100 rounded w-48"></div>
        </div>
        <div className="divide-y divide-neutral-200">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="p-4 animate-pulse">
              <div className="flex items-center space-x-4">
                <div className="h-4 bg-neutral-100 rounded w-1/4"></div>
                <div className="h-4 bg-neutral-100 rounded w-1/3"></div>
                <div className="h-4 bg-neutral-100 rounded w-1/6"></div>
                <div className="h-4 bg-neutral-100 rounded w-1/5"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div className="bg-white rounded shadow-sm divide-y divide-neutral-200">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="p-4 animate-pulse">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 bg-neutral-100 rounded"></div>
              <div className="flex-1">
                <div className="h-4 bg-neutral-100 rounded w-1/3 mb-2"></div>
                <div className="h-3 bg-neutral-100 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'stats') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded shadow-sm p-6 animate-pulse">
            <div className="flex items-center justify-between mb-4">
              <div className="h-4 bg-neutral-100 rounded w-1/2"></div>
              <div className="h-8 w-8 bg-neutral-100 rounded"></div>
            </div>
            <div className="h-8 bg-neutral-100 rounded w-2/3 mb-2"></div>
            <div className="h-3 bg-neutral-100 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    );
  }

  return null;
}
