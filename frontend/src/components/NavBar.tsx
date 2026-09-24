import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/authContext";

export default function NavBar() {
  const { status, user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout().catch(() => undefined);
    navigate("/");
  }

  return (
    <header className="nav-bar">
      <nav aria-label="Main">
        <Link to="/" className="nav-brand">
          Sekiro Practice
        </Link>
        <Link to="/bosses">Bosses</Link>
      </nav>
      {status === "ready" && (
        <div className="nav-account">
          {user ? (
            <>
              <span className="nav-username">{user.username}</span>
              <button type="button" className="btn" onClick={handleLogout}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Log In</Link>
              <Link to="/register" className="btn btn-primary">
                Register
              </Link>
            </>
          )}
        </div>
      )}
    </header>
  );
}
