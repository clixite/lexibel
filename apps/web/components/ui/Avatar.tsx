"use client";

import { ReactNode } from "react";

export interface AvatarProps {
  src?: string;
  alt?: string;
  fallback: string;
  size?: "sm" | "md" | "lg" | "xl";
  status?: "online" | "offline" | "busy";
}

export default function Avatar({
  src,
  alt,
  fallback,
  size = "md",
  status,
}: AvatarProps) {
  const sizeClasses = {
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-12 h-12 text-base",
    xl: "w-16 h-16 text-lg",
  };

  const statusSizeClasses = {
    sm: "w-2 h-2 border",
    md: "w-2.5 h-2.5 border-2",
    lg: "w-3 h-3 border-2",
    xl: "w-4 h-4 border-2",
  };

  const statusColorClasses = {
    online: "bg-success-500",
    offline: "bg-neutral-400",
    busy: "bg-danger-500",
  };

  return (
    <div className="relative inline-flex">
      <div
        className={`${sizeClasses[size]} rounded-full overflow-hidden flex items-center justify-center font-medium`}
      >
        {src ? (
          <img
            src={src}
            alt={alt || fallback}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-primary text-white flex items-center justify-center">
            {fallback}
          </div>
        )}
      </div>

      {status && (
        <span
          className={`absolute bottom-0 right-0 rounded-full border-white ${statusSizeClasses[size]} ${statusColorClasses[status]}`}
        />
      )}
    </div>
  );
}
