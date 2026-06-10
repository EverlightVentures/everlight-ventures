import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: ReactNode;
  cell: (row: T, idx: number) => ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
  width?: string;
};

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, idx: number) => string;
  empty?: ReactNode;
  caption?: ReactNode;
  dense?: boolean;
};

export function DataTable<T>({ columns, rows, rowKey, empty, caption, dense }: Props<T>) {
  return (
    <div className="card p-0 overflow-hidden">
      {caption && (
        <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
          {caption}
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.02] border-b border-white/[0.04] sticky top-0">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  style={c.width ? { width: c.width } : undefined}
                  className={cn(
                    "px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium",
                    c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : "text-left",
                    c.className
                  )}
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="text-center py-8 text-gray-500 text-sm">
                  {empty ?? "No data"}
                </td>
              </tr>
            )}
            {rows.map((row, i) => (
              <tr
                key={rowKey(row, i)}
                className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors"
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={cn(
                      dense ? "px-3 py-1.5" : "px-4 py-2.5",
                      c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : "text-left",
                      c.className
                    )}
                  >
                    {c.cell(row, i)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
