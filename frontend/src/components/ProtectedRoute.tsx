import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg">
        <div className="flex items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface px-phi-5 py-phi-3 shadow-subtle">
          <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} />
          <p className="text-phi-sm text-ink-secondary">Checking session</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
