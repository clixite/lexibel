interface SkeletonTextProps {
  width?: string;
  height?: string;
  className?: string;
}

export default function SkeletonText({
  width = "w-full",
  height = "h-4",
  className = "",
}: SkeletonTextProps) {
  return (
    <div
      className={`bg-neutral-100 rounded animate-pulse ${width} ${height} ${className}`}
    />
  );
}
