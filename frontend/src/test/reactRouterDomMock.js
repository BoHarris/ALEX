const React = require("react");

const RouterContext = React.createContext({
  pathname: "/",
  state: null,
  navigate: () => {},
});

function normalizeEntry(entry) {
  if (typeof entry === "string") {
    return { pathname: entry, state: null };
  }

  return {
    pathname: entry?.pathname || "/",
    state: entry?.state || null,
  };
}

function RouterProvider({ initialEntry, children }) {
  const [location, setLocation] = React.useState(() => normalizeEntry(initialEntry));

  const navigate = React.useCallback((to, options = {}) => {
    const nextLocation = typeof to === "string"
      ? { pathname: to, state: options.state || null }
      : normalizeEntry(to);

    setLocation(nextLocation);
  }, []);

  const value = React.useMemo(() => ({
    pathname: location.pathname,
    state: location.state,
    navigate,
  }), [location.pathname, location.state, navigate]);

  return React.createElement(RouterContext.Provider, { value }, children);
}

function BrowserRouter({ children }) {
  return React.createElement(
    RouterProvider,
    {
      initialEntry: {
        pathname: window.location.pathname || "/",
        state: window.history.state || null,
      },
    },
    children,
  );
}

function MemoryRouter({ initialEntries = ["/"], children }) {
  return React.createElement(RouterProvider, { initialEntry: initialEntries[0] }, children);
}

function Routes({ children }) {
  const { pathname } = React.useContext(RouterContext);
  const childArray = React.Children.toArray(children);
  const exactMatch = childArray.find((child) => child.props.path === pathname);
  const rootMatch = childArray.find((child) => child.props.path === "/" && pathname === "/");
  const match = exactMatch || rootMatch || null;

  return match ? match.props.element || null : null;
}

function Route() {
  return null;
}

function Navigate({ to, replace, state }) {
  const navigate = useNavigate();

  React.useEffect(() => {
    navigate(to, { replace, state });
  }, [navigate, replace, state, to]);

  return null;
}

function Link({ to, children, ...props }) {
  const navigate = useNavigate();

  return React.createElement(
    "a",
    {
      ...props,
      href: to,
      onClick: (event) => {
        event.preventDefault();
        navigate(to);
      },
    },
    children,
  );
}

function useNavigate() {
  return React.useContext(RouterContext).navigate;
}

function useLocation() {
  const context = React.useContext(RouterContext);
  return {
    pathname: context.pathname,
    state: context.state,
  };
}

module.exports = {
  BrowserRouter,
  Link,
  MemoryRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
};
