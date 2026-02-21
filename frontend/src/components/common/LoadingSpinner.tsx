interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingSpinner({ size = 'md' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div className="flex justify-center items-center">
      <span
        className={`${sizeClasses[size]} font-mono text-stone-400 animate-pulse tracking-widest`}
      >
        Loading...
      </span>
    </div>
  );
}
