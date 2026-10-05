import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import AuthPage from "./pages/AuthPage";
import BossSelectionPage from "./pages/BossSelectionPage";
import BossDashboardPage from "./pages/BossDashboardPage";
import HomePage from "./pages/HomePage";

export default function App() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/bosses" element={<BossSelectionPage />} />
        <Route path="/bosses/:bossId" element={<BossDashboardPage />} />
      </Routes>
    </>
  );
}
