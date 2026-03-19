interface AvatarProps {
  size?: 'sm' | 'md' | 'lg';
}

const SIZES = {
  sm: { container: 'w-7 h-7', text: 'text-xs' },
  md: { container: 'w-10 h-10', text: 'text-sm' },
  lg: { container: 'w-12 h-12', text: 'text-lg' },
} as const;

/** Application avatar displaying the "Q" brand mark in a dark circle. */
export function AppAvatar({ size = 'md' }: AvatarProps) {
  const s = SIZES[size];
  return (
    <div className={`flex-shrink-0 ${s.container} rounded-full bg-black dark:bg-white flex items-center justify-center`}>
      <span className={`text-white dark:text-black ${s.text} font-semibold`}>Q</span>
    </div>
  );
}

/** User avatar displaying a generic person silhouette icon. */
export function UserAvatar({ size = 'sm' }: AvatarProps) {
  const s = SIZES[size];
  const iconSize = size === 'sm' ? 'h-4 w-4' : size === 'md' ? 'h-5 w-5' : 'h-6 w-6';
  return (
    <div className={`flex-shrink-0 ${s.container} rounded-full bg-gray-600 dark:bg-gray-400 flex items-center justify-center`}>
      <svg className={`${iconSize} text-white dark:text-gray-900`} fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
      </svg>
    </div>
  );
}
