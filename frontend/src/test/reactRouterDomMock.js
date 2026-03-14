const React = require("react");

function passThrough(children) {
  return React.createElement(React.Fragment, null, children);
}

module.exports = {
  BrowserRouter: ({ children }) => passThrough(children),
  MemoryRouter: ({ children }) => passThrough(children),
  Routes: ({ children }) => React.createElement(React.Fragment, null, React.Children.toArray(children)[0] || null),
  Route: ({ element }) => element || null,
  Link: ({ to, children, ...props }) => React.createElement("a", { href: to, ...props }, children),
  Navigate: ({ to }) => React.createElement("a", { href: to }, `Navigate to ${to}`),
};
