//src/pages/Register.tsx
import { FormEvent, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiPost, apiPostWithoutAuthLogout } from '../lib/api';

function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [bio, setBio] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { configError, register, login, loginWithGoogle, user } = useAuth();
  const submitInFlightRef = useRef(false);
  const googleInFlightRef = useRef(false);

  const createBackendProfile = async () => {
    try {
      await apiPost('/api/v1/users/register', {
        username,
        email: user?.email ?? email,
        bio: bio || null,
      });
    } catch (err: any) {
      const message = String(err?.message ?? '');
      if (message.toLowerCase().includes('already exists')) {
        return;
      }
      throw err;
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (submitInFlightRef.current) return;
    submitInFlightRef.current = true;

    try {
      // First, register with Firebase unless the user is already signed in
      // and only needs a backend profile row.
      if (!user) {
        try {
          await register(email, password);
        } catch (err: any) {
          if (err?.code === 'auth/email-already-in-use') {
            await login(email, password);
          } else {
            throw err;
          }
        }
      }

      // Then, register with backend. This is needed even if the Firebase
      // account already existed, because Firebase Auth and our DB are separate.
      await createBackendProfile();

      navigate('/');
    } catch (err: any) {
      if (err?.code === 'auth/wrong-password' || err?.code === 'auth/invalid-credential') {
        setError('This email already exists in Firebase. Enter the correct password to create the missing database profile.');
      } else {
        setError(err.message || 'Unable to create an account. Please try again.');
      }
      console.error(err);
    } finally {
      submitInFlightRef.current = false;
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    if (googleInFlightRef.current) return;
    googleInFlightRef.current = true;

    try {
      const user = await loginWithGoogle();
      const baseName = user.email?.split('@')[0]?.replace(/[^a-zA-Z0-9_]/g, '_') || 'user';
      const uidTail = user.uid.slice(-6).replace(/[^a-zA-Z0-9_]/g, '');

      await apiPostWithoutAuthLogout('/api/v1/users/register', {
        username: `${baseName}_${uidTail}`,
        email: user.email || '',
        bio: null,
      });
      navigate('/');
    } catch (err: any) {
      setError('Google sign-in failed. Please try again.');
      console.error(err);
    } finally {
      googleInFlightRef.current = false;
    }
  };

  return (
    <div className="auth-page">
      <section className="auth-panel glass-panel">
        <div className="hero-badge">Register</div>
        <h2>Create an account</h2>
        <p>Sign up with email/password or Google to start using ChattingApp.</p>
        {configError ? <p className="form-error">{configError}</p> : null}

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Email
            <input
              type="email"
              name="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@example.com"
              required={!user}
              disabled={Boolean(user)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              name="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Create a strong password"
              required={!user}
              disabled={Boolean(user)}
            />
          </label>
          <label>
            Username
            <input
              type="text"
              name="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Choose a unique username"
              required
            />
          </label>
          <label>
            Bio (optional)
            <textarea
              name="bio"
              value={bio}
              onChange={(event) => setBio(event.target.value)}
              placeholder="Tell us about yourself"
              rows={3}
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" type="submit" disabled={Boolean(configError)}>
            Create account
          </button>
          <button type="button" className="secondary-button" onClick={handleGoogleSignIn} disabled={Boolean(configError)}>
            Continue with Google
          </button>
        </form>

        <p className="small-note">
          Already have an account? <Link to="/login">Sign in.</Link>
        </p>
      </section>
    </div>
  );
}

export default Register;
