"use client";

import { ChevronLeft, ChevronRight, ArrowUp, ArrowDown } from 'lucide-react';
import { useState } from 'react';

export interface Column<T> {
  key: string;
  label: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  editable?: boolean;
  width?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (item: T) => void;
  onCellEdit?: (item: T, key: string, value: any) => Promise<void>;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  getRowId?: (item: T) => string;
  pagination?: {
    page: number;
    perPage: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}

export default function DataTable<T extends Record<string, any>>({
  data,
  columns,
  onRowClick,
  onCellEdit,
  selectable = false,
  selectedIds = new Set(),
  onSelectionChange,
  getRowId = (item) => item.id,
  pagination,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [editingCell, setEditingCell] = useState<{ row: string; field: string } | null>(null);
  const [editValue, setEditValue] = useState<any>("");

  const totalPages = pagination ? Math.ceil(pagination.total / pagination.perPage) : 1;
  const startItem = pagination ? (pagination.page - 1) * pagination.perPage + 1 : 1;
  const endItem = pagination ? Math.min(pagination.page * pagination.perPage, pagination.total) : data.length;

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const sortedData = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const handleCellEdit = async (item: T, key: string, value: any) => {
    if (onCellEdit) {
      await onCellEdit(item, key, value);
    }
    setEditingCell(null);
  };

  const handleSelectAll = () => {
    if (selectedIds.size === data.length) {
      onSelectionChange?.(new Set());
    } else {
      onSelectionChange?.(new Set(data.map(getRowId)));
    }
  };

  const handleSelectRow = (item: T) => {
    const id = getRowId(item);
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    onSelectionChange?.(newSet);
  };

  return (
    <div className="bg-white rounded shadow-sm overflow-hidden border border-neutral-200">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-neutral-50 border-b border-neutral-200 sticky top-0">
            <tr>
              {selectable && (
                <th className="px-4 py-3 text-left w-12">
                  <input
                    type="checkbox"
                    checked={data.length > 0 && selectedIds.size === data.length}
                    onChange={handleSelectAll}
                    className="rounded border-neutral-300 text-primary focus:ring-primary"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`px-6 py-3 text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider ${
                    column.sortable ? 'cursor-pointer select-none hover:bg-neutral-100' : ''
                  }`}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.label}</span>
                    {column.sortable && (
                      <span className="text-neutral-400">
                        {sortKey === column.key ? (
                          sortDirection === 'asc' ? (
                            <ArrowUp className="w-3 h-3" />
                          ) : (
                            <ArrowDown className="w-3 h-3" />
                          )
                        ) : (
                          <ArrowUp className="w-3 h-3 opacity-0" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {sortedData.map((item) => {
              const rowId = getRowId(item);
              const isSelected = selectedIds.has(rowId);

              return (
                <tr
                  key={rowId}
                  className={`transition-colors duration-150 ${
                    isSelected ? 'bg-primary/5' : 'hover:bg-neutral-50'
                  } ${onRowClick ? 'cursor-pointer' : ''}`}
                >
                  {selectable && (
                    <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleSelectRow(item)}
                        className="rounded border-neutral-300 text-primary focus:ring-primary"
                      />
                    </td>
                  )}
                  {columns.map((column) => {
                    const isEditing =
                      editingCell?.row === rowId && editingCell?.field === column.key;

                    return (
                      <td
                        key={column.key}
                        className="px-6 py-4 text-sm text-neutral-700"
                        onDoubleClick={() => {
                          if (column.editable && onCellEdit) {
                            setEditingCell({ row: rowId, field: column.key });
                            setEditValue(item[column.key]);
                          }
                        }}
                        onClick={() => !column.editable && onRowClick?.(item)}
                      >
                        {isEditing ? (
                          <input
                            autoFocus
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => handleCellEdit(item, column.key, editValue)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                handleCellEdit(item, column.key, editValue);
                              }
                              if (e.key === 'Escape') {
                                setEditingCell(null);
                              }
                            }}
                            className="w-full px-2 py-1 border border-primary rounded focus:outline-none focus:ring-2 focus:ring-primary/20"
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : column.render ? (
                          column.render(item)
                        ) : (
                          item[column.key]
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between">
          <div className="text-sm text-neutral-700">
            Affichage de <span className="font-medium">{startItem}</span> à{' '}
            <span className="font-medium">{endItem}</span> sur{' '}
            <span className="font-medium">{pagination.total}</span> résultats
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
              className="p-2 rounded border border-neutral-300 hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
            >
              <ChevronLeft className="h-4 w-4 text-neutral-700" />
            </button>
            <span className="text-sm text-neutral-700">
              Page <span className="font-medium">{pagination.page}</span> sur{' '}
              <span className="font-medium">{totalPages}</span>
            </span>
            <button
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page === totalPages}
              className="p-2 rounded border border-neutral-300 hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
            >
              <ChevronRight className="h-4 w-4 text-neutral-700" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
