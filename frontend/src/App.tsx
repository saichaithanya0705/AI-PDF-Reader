import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import ReaderPage from './pages/ReaderPage';
import SignupPage from './pages/SignupPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import EvalsPage from './pages/EvalsPage';
import { AuthProvider } from './context/AuthContext';
import { PDFProvider } from './context/PDFContext';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <PDFProvider>
          <Router>
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
              <Routes>
                {/* Public routes */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                
                {/* Protected routes - require authentication */}
                <Route 
                  path="/library" 
                  element={
                    <ProtectedRoute>
                      <HomePage />
                    </ProtectedRoute>
                  } 
                />
                <Route
                  path="/evals"
                  element={
                    <ProtectedRoute>
                      <EvalsPage />
                    </ProtectedRoute>
                  }
                />
                <Route 
                  path="/reader/:pdfId" 
                  element={
                    <ProtectedRoute>
                      <ReaderPage />
                    </ProtectedRoute>
                  } 
                />
              </Routes>
            </div>
          </Router>
        </PDFProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;