"use client";

import { ReactNode, useState, useRef, useEffect } from "react";

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
  icon?: ReactNode;
  badge?: number;
}

export interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onTabChange?: (tabId: string) => void;
}

export default function Tabs({ tabs, defaultTab, onTabChange }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const handleTabClick = (tabId: string) => {
    setActiveTab(tabId);
    onTabChange?.(tabId);
  };
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });
  const tabRefs = useRef<{ [key: string]: HTMLButtonElement | null }>({});

  useEffect(() => {
    const activeElement = tabRefs.current[activeTab];
    if (activeElement) {
      setIndicatorStyle({
        left: activeElement.offsetLeft,
        width: activeElement.offsetWidth,
      });
    }
  }, [activeTab]);

  const activeTabData = tabs.find((tab) => tab.id === activeTab);

  return (
    <div className="w-full">
      {/* Tab Headers */}
      <div className="relative border-b border-neutral-200">
        <div className="flex gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              ref={(el) => {
                tabRefs.current[tab.id] = el;
              }}
              onClick={() => handleTabClick(tab.id)}
              className={`
                relative px-4 py-2.5 text-sm font-medium transition-colors duration-normal
                flex items-center gap-2
                ${
                  activeTab === tab.id
                    ? "text-accent"
                    : "text-neutral-600 hover:text-neutral-900"
                }
              `}
            >
              {tab.icon && <span className="inline-flex">{tab.icon}</span>}
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-medium bg-accent-100 text-accent-700 rounded-full">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Animated Indicator */}
        <div
          className="absolute bottom-0 h-0.5 bg-accent transition-all duration-normal"
          style={{
            left: `${indicatorStyle.left}px`,
            width: `${indicatorStyle.width}px`,
          }}
        />
      </div>

      {/* Tab Content */}
      <div className="py-4">
        <div className="animate-fadeIn">
          {activeTabData?.content}
        </div>
      </div>
    </div>
  );
}
