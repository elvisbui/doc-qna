interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200/70 dark:bg-white/10 ${className}`}
    />
  );
}

export function DocumentListSkeleton() {
  return (
    <ul className="divide-y divide-gray-200 dark:divide-white/10 border-t border-gray-200 dark:border-white/10">
      {[1, 2, 3].map((i) => (
        <li key={i} className="flex items-center justify-between py-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-14" />
            </div>
            <div className="mt-1.5 flex items-center gap-3">
              <Skeleton className="h-3 w-10" />
              <Skeleton className="h-3 w-14" />
            </div>
          </div>
          <Skeleton className="h-6 w-6 rounded" />
        </li>
      ))}
    </ul>
  );
}
