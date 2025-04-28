export function Button({ children, onClick, disabled }) {
  //This is a simple button component.
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50`}
    >
      {children}
    </button>
  );
}
