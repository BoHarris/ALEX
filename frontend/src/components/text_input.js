export default function TextField({
  label,
  id,
  type = "text",
  value,
  onChange,
  placeholder,
  className = "",
  ...props
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-app">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={`w-full rounded-xl border border-app bg-app px-3 py-2 text-app placeholder:text-app-muted focus-visible:outline-none ${className}`}
        {...props}
      />
    </div>
  );
}
