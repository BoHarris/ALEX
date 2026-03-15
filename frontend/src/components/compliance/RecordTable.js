export default function RecordTable({
  columns,
  rows,
  keyField = "id",
  onRowClick,
  selectedRowKey = null,
  getRowClassName,
  getRowAriaLabel,
}) {
  return (
    <div className="surface-card overflow-hidden rounded-3xl">
      <div className={`grid gap-4 border-b border-app px-5 py-4 text-xs font-semibold uppercase tracking-[0.2em] text-app-muted`} style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}>
        {columns.map((column) => (
          <div key={column.key}>{column.label}</div>
        ))}
      </div>
      <div>
        {rows.map((row) => {
          const rowKey = row[keyField];
          const selected = selectedRowKey != null && rowKey === selectedRowKey;
          const customClassName = getRowClassName?.(row, { selected }) || "";

          return (
            <button
              key={rowKey}
              type="button"
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              aria-label={getRowAriaLabel?.(row)}
              aria-pressed={onRowClick ? selected : undefined}
              className={`grid w-full gap-4 border-t border-app px-5 py-4 text-left text-sm text-app-secondary transition ${onRowClick ? "hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/80" : ""} ${selected ? "bg-cyan-400/10 ring-1 ring-inset ring-cyan-300/40" : ""} ${customClassName}`}
              style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}
            >
              {columns.map((column) => (
                <div key={column.key} className={column.className || ""}>
                  {column.render ? column.render(row) : row[column.key]}
                </div>
              ))}
            </button>
          );
        })}
      </div>
    </div>
  );
}
