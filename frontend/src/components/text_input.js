export default function TextField({
  label,
  id,
  type = "text",
  value,
  onChange,
  placeholder,
}) {
  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={id}
        className="text-sm font-medium text-gray-700 text-white"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="border border-gray-600 rounded px-3 py-2 bg-gray-800 text-white"
      />
    </div>
  );
}
