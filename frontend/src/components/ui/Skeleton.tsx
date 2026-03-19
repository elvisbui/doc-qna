interface SkeletonProps {
  /** Additional CSS classes for sizing the skeleton element */
  className?: string;
}

/** Animated pulse placeholder block used as a loading skeleton. */
export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${className}`}
    />
  );
}

/** Loading skeleton matching the DocumentList layout with 3 placeholder rows. */
export function DocumentListSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <ul className="divide-y divide-gray-200 dark:divide-gray-700">
        {[1, 2, 3].map((i) => (
          <li key={i} className="flex items-center justify-between px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <div className="mt-1 flex items-center gap-3">
                <Skeleton className="h-3 w-10" />
                <Skeleton className="h-3 w-14" />
              </div>
            </div>
            <div className="ml-4">
              <Skeleton className="h-6 w-6 rounded" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
