import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (isRegister && password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const result = isRegister
        ? await api.register(email, password)
        : await api.login(email, password);
      login(result.user);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  function toggleMode() {
    setIsRegister(!isRegister);
    setError('');
    setConfirm('');
  }

  return (
    <main className="login-page">
      <section className="login-form-section">
        <div className="login-form-container">
          <div className="brand" aria-label="Legal Metrology">
            <span className="brand-mark" aria-hidden="true">LM</span>
            <span>METROLOGY / INDIA</span>
          </div>

          <p className="eyebrow">INSPECTOR WORKSPACE</p>
          <h1>{isRegister ? 'Create your workspace' : 'Welcome back'}</h1>
          <p className="login-subtitle">
            {isRegister
              ? 'Set up access to your compliance screening workspace.'
              : 'Sign in to continue your inspection work.'}
          </p>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label className="form-label" htmlFor="login-email">Email address</label>
              <input
                id="login-email"
                className="form-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="login-password">Password</label>
              <input
                id="login-password"
                className="form-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
            </div>

            {isRegister && (
              <div className="form-group">
                <label className="form-label" htmlFor="login-confirm">Confirm password</label>
                <input
                  id="login-confirm"
                  className="form-input"
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  minLength={8}
                  required
                  autoComplete="new-password"
                />
              </div>
            )}

            {error && (
              <div className="alert alert-error" role="alert">{error}</div>
            )}

            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading
                ? 'Signing in…'
                : isRegister
                  ? 'Create account'
                  : 'Sign in'}
              {!loading && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <p className="login-switch">
            {isRegister ? 'Already have access? ' : 'New to the workspace? '}
            <button onClick={toggleMode}>
              {isRegister ? 'Sign in' : 'Create an account'}
            </button>
          </p>
        </div>
      </section>

      <aside className="login-aside">
        <div>
          <span className="eyebrow">AI-ASSISTED SCREENING</span>
          <h2>Evidence before decisions.</h2>
          <p>Trace every package label from detected declaration to applicable rule.</p>
        </div>
        <span className="login-aside-footer">LEGAL METROLOGY COMPLIANCE / v1</span>
      </aside>
    </main>
  );
}
