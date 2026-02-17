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
    text: "h-4 rounded",
    circle: "rounded-full",
    rect: "rounded",
  };

  return (
    <div
      className={`bg-neutral-100 animate-pulse ${variantClasses[variant]} ${className}`}
      style={{
        width: width || (variant === "circle" ? height || "40px" : "100%"),
        height: height || (variant === "text" ? "1rem" : "40px"),
      }}
    />
  );
}
