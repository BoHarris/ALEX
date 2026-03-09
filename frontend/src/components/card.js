export function Card({ children, className = "" }) {
  // This component is a simple wrapper for a card UI element.
  return (
    <div className={`rounded-md shadow p-4 bg-white ${className}`}>
      {children}
    </div>
  );
}

export function CardContent({ children, className = "" }) {
  // This is a wrapper for the content inside the card.
  return <div className={`p-4 ${className}`}>{children}</div>;
}
