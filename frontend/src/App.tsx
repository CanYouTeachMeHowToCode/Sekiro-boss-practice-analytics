import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import AdminPage from "./pages/AdminPage";
import AuthPage from "./pages/AuthPage";
import BossSelectionPage from "./pages/BossSelectionPage";
import BossDashboardPage from "./pages/BossDashboardPage";
import HomePage from "./pages/HomePage";
import RecordingReportPage from "./pages/RecordingReportPage";
import RecordingsPage from "./pages/RecordingsPage";
import UploadRecordingPage from "./pages/UploadRecordingPage";

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
        <Route path="/recordings" element={<RecordingsPage />} />
        <Route path="/recordings/upload" element={<UploadRecordingPage />} />
        <Route path="/recordings/:recordingId" element={<RecordingReportPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/recordings/:recordingId" element={<RecordingReportPage admin />} />
      </Routes>
    </>
  );
}
