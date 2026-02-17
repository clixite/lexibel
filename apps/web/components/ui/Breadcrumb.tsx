"use client";

import { ChevronRight, Home } from "lucide-react";
import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  actions?: React.ReactNode;
}

export default function Breadcrumb({ items, actions }: BreadcrumbProps) {
  return (
    <div className="flex items-center justify-between py-4 px-6 bg-white border-b border-neutral-200">
      <nav className="flex items-center gap-2 text-sm">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            {index > 0 && <ChevronRight className="w-4 h-4 text-neutral-400" />}
            {item.href ? (
              <Link
                href={item.href}
                className="flex items-center gap-1.5 text-neutral-600 hover:text-primary transition-colors duration-150"
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            ) : (
              <div className="flex items-center gap-1.5 text-neutral-900 font-medium">
                {item.icon}
                <span>{item.label}</span>
              </div>
            )}
          </div>
        ))}
      </nav>

      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
