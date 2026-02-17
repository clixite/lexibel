"use client";

import { useEffect, useRef, useState } from "react";

export interface ContextMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: "default" | "danger";
  separator?: boolean;
}

interface ContextMenuProps {
  items: ContextMenuItem[];
  children: React.ReactNode;
}

export default function ContextMenu({ items, children }: ContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const menuRef = useRef<HTMLDivElement>(null);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setPosition({ x: e.clientX, y: e.clientY });
    setIsOpen(true);
  };

  useEffect(() => {
    const handleClick = () => setIsOpen(false);
    const handleScroll = () => setIsOpen(false);

    if (isOpen) {
      document.addEventListener("click", handleClick);
      document.addEventListener("scroll", handleScroll, true);
    }

    return () => {
      document.removeEventListener("click", handleClick);
      document.removeEventListener("scroll", handleScroll, true);
    };
  }, [isOpen]);

  return (
    <>
      <div onContextMenu={handleContextMenu}>{children}</div>

      {isOpen && (
        <div
          ref={menuRef}
          className="fixed z-50 bg-white rounded-lg shadow-lg border border-neutral-200 py-1 min-w-48 animate-in fade-in zoom-in-95 duration-100"
          style={{ top: position.y, left: position.x }}
        >
          {items.map((item, index) => (
            <div key={index}>
              {item.separator ? (
                <div className="h-px bg-neutral-200 my-1" />
              ) : (
                <button
                  onClick={() => {
                    item.onClick();
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors duration-150 ${
                    item.variant === "danger"
                      ? "text-danger-600 hover:bg-danger-50"
                      : "text-neutral-700 hover:bg-neutral-50"
                  }`}
                >
                  {item.icon && <span className="w-4 h-4">{item.icon}</span>}
                  <span>{item.label}</span>
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
