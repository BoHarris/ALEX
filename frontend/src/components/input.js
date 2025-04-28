export function Input({ id, type = "text", placeholder, accept, onChange }) {
  return (
    <input
      id={id}
      type={type}
      placeholder={placeholder}
      accept={accept}
      onChange={onChange}
      className="border border-gray-300 rounded px-3 py-2 w-full"
    />
  );
}
