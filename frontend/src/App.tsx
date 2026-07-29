import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Execution from './pages/Execution';
import Workspace from './pages/Workspace';
import Memory from './pages/Memory';
import Metrics from './pages/Metrics';
import Settings from './pages/Settings';
import ErrorSnackbar from './components/ErrorSnackbar';
import { AuthProvider, useAuth } from './context/AuthContext';
import AccessKeyGate from './components/AccessKeyGate';

function AppContent() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <AccessKeyGate />;
  }

  return (
    <>
      <Router>
        <Routes>
          <Route path="/" element={<DashboardLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="chat" element={<Chat />} />
            <Route path="execution" element={<Execution />} />
            <Route path="workspace" element={<Workspace />} />
            <Route path="memory" element={<Memory />} />
            <Route path="metrics" element={<Metrics />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
      <ErrorSnackbar />
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
