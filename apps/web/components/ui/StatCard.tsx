"use client";

import { TrendingUp, TrendingDown } from 'lucide-react';

export interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: number;
    label: string;
  };
  color?: 'accent' | 'success' | 'warning' | 'error';
}

export default function StatCard({ title, value, icon, trend, color = 'accent' }: StatCardProps) {
  const colorClasses = {
    accent: 'bg-accent-100 text-accent-600',
    success: 'bg-success-100 text-success-600',
    warning: 'bg-warning-100 text-warning-600',
    error: 'bg-error-100 text-error-600',
  };

  const trendColorClasses = {
    positive: 'text-success-600',
    negative: 'text-error-600',
  };

  const isPositive = trend && trend.value >= 0;

  return (
    <div className="bg-white rounded-lg shadow-subtle p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-neutral-700">{title}</h3>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
      <div className="mb-2">
        <p className="text-3xl font-bold text-neutral-900">{value}</p>
      </div>
      {trend && (
        <div className="flex items-center space-x-1">
          {isPositive ? (
            <TrendingUp className="h-4 w-4 text-success-600" />
          ) : (
            <TrendingDown className="h-4 w-4 text-error-600" />
          )}
          <span className={`text-sm font-medium ${isPositive ? trendColorClasses.positive : trendColorClasses.negative}`}>
            {Math.abs(trend.value)}%
          </span>
          <span className="text-sm text-neutral-600">{trend.label}</span>
        </div>
      )}
    </div>
  );
}
