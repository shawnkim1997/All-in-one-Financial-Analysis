import type { ReactNode } from "react";

interface Column<T> {
  key: string;
  header: ReactNode;
  align?: "left" | "right" | "center";
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  emptyMessage?: string;
  className?: string;
}

const alignClass = {
  left: "text-left",
  right: "text-right",
  center: "text-center",
} as const;

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyMessage = "No rows to display.",
  className = "",
}: DataTableProps<T>) {
  return (
    <div className={`atlas-table-shell ${className}`}>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead className="bg-surface-sunken">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`border-b border-border-strong px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-navy ${alignClass[column.align ?? "left"]}`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-6 text-center text-text-muted">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={rowKey(row, index)} className="border-b border-border last:border-b-0">
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`px-4 py-3 align-top text-text-primary ${alignClass[column.align ?? "left"]}`}
                    >
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
