import { Link, NavLink, Outlet, useNavigate } from "react-router";
import { useEnsureCsrf, useLogout, useMe } from "../lib/auth";
import { Button } from "./ui";

const navLink = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-teal-50 text-teal-800" : "text-slate-600 hover:text-slate-900"}`;

export function Layout() {
  useEnsureCsrf();
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          <Link to="/" className="text-lg font-bold text-teal-800">
            HolidayOps
          </Link>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navLink}>
              Playground
            </NavLink>
            <NavLink to="/app" className={navLink}>
              My calendars
            </NavLink>
            <a className={navLink({ isActive: false })} href="/api/v1/docs/">
              API docs
            </a>
          </nav>
          <div className="ms-auto flex items-center gap-3 text-sm">
            {me ? (
              <>
                <span className="text-slate-600">{me.email}</span>
                <Button
                  variant="ghost"
                  onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/") })}
                >
                  Log out
                </Button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-slate-700 hover:underline">
                  Log in
                </Link>
                <Link to="/signup">
                  <Button>Sign up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
