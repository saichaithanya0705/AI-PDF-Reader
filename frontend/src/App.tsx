import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import ReaderPage from './pages/ReaderPage';
import SignupPage from './pages/SignupPage';
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