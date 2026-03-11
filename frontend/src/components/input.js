export function Input({ id, type = "text", placeholder, accept, onChange, className = "", ...props }) {
  return (
    <input
      id={id}
      type={type}
      placeholder={placeholder}
      accept={accept}
      onChange={onChange}
      className={`w-full rounded-xl border border-app bg-app px-3 py-2 text-app placeholder:text-app-muted focus-visible:outline-none ${className}`}
      {...props}
    />
  );
}
