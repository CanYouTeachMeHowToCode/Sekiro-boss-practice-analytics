import { Route, Routes } from "react-router-dom";
import BossSelectionPage from "./pages/BossSelectionPage";
import BossDashboardPage from "./pages/BossDashboardPage";
import SekiroDashboardPage from "./pages/SekiroDashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SekiroDashboardPage />} />
      <Route path="/bosses" element={<BossSelectionPage />} />
      <Route path="/bosses/:bossId" element={<BossDashboardPage />} />
    </Routes>
  );
}
