export function Button({ children, type = "button", className = "", ...props }) {
  return (
    <button
      type={type}
      className={`btn-primary-app disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
