"use client";

export interface SkeletonProps {
  variant?: "text" | "circle" | "rect";
  width?: string;
  height?: string;
  className?: string;
}

export default function Skeleton({
  variant = "rect",
  width,
  height,
  className = "",
}: SkeletonProps) {
  const variantClasses = {
    text: "h-4 rounded-md",
    circle: "rounded-full",
    rect: "rounded-lg",
  };

  const shimmerStyle = {
    backgroundImage:
      "linear-gradient(90deg, #f5f5f4 0px, #e7e5e4 40px, #f5f5f4 80px)",
    backgroundSize: "1000px 100%",
  };

  return (
    <div
      className={`bg-neutral-200 animate-shimmer ${variantClasses[variant]} ${className}`}
      style={{
        width: width || (variant === "circle" ? height || "40px" : "100%"),
        height: height || (variant === "text" ? "1rem" : "40px"),
        ...shimmerStyle,
      }}
    />
  );
}
