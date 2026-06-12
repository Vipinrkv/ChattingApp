import { FormEvent, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiGetWithoutAuthLogout, apiPostWithoutAuthLogout } from '../../lib/api';
import { getPhoneConfirmationResult } from '../../firebase';
import type { ConfirmationResult } from 'firebase/auth';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const navigate = useNavigate();
  const { configError, login, loginWithGoogle } = useAuth();

  const [phoneNumber, setPhoneNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [phoneStep, setPhoneStep] = useState<'enter' | 'otp'>('enter');
  const [otpSending, setOtpSending] = useState(false);
  const [otpVerifying, setOtpVerifying] = useState(false);
  const [confirmation, setConfirmation] = useState<ConfirmationResult | null>(null);
  const submitInFlightRef = useRef(false);
  const googleInFlightRef = useRef(false);
  const phoneVerifyInFlightRef = useRef(false);

  const isMissingBackendProfile = (err: unknown) => {
    const msg = err instanceof Error ? err.message.toLowerCase() : '';
    return msg.includes('profile not found') || msg.includes('not found') || msg.includes('unauthorized');
  };

  const registerBackendUser = async (payload: { username: string; phone?: string | null; email?: string | null; bio?: string | null }) => {
    await apiPostWithoutAuthLogout('/api/v1/users/register', payload);
  };

  const startPhoneOtp = async () => {
    setError('');
    if (!phoneNumber.trim()) return;

    setOtpSending(true);
    try {
      const result = await getPhoneConfirmationResult(phoneNumber.trim(), 'phone-recaptcha-container');
      setConfirmation(result);
      setPhoneStep('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send OTP');
    } finally {
      setOtpSending(false);
    }
  };

  const verifyPhoneOtp = async () => {
    setError('');
    if (!confirmation) return;
    if (!otp.trim()) return;
    if (phoneVerifyInFlightRef.current) return;

    setOtpVerifying(true);
    phoneVerifyInFlightRef.current = true;
    try {
      const credentialUser = await confirmation.confirm(otp.trim());
      const firebaseUser = credentialUser.user;

      const idToken = await firebaseUser.getIdToken();
      localStorage.setItem('authToken', idToken);

      const phone = phoneNumber.trim();
      const digitsOnly = phone.replace(/\D/g, '');
      const tail = digitsOnly.slice(-6) || 'user';
      const uidTail = firebaseUser.uid.slice(-6).replace(/[^a-zA-Z0-9_]/g, '');
      const username = `user_${tail}_${uidTail}`;

      await registerBackendUser({ username, phone, email: null, bio: null });

      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Phone sign-in failed. Please try again.');
    } finally {
      phoneVerifyInFlightRef.current = false;
      setOtpVerifying(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (submitInFlightRef.current) return;
    submitInFlightRef.current = true;

    try {
      await login(email, password);
      // After Firebase login, fetch user from backend
      try {
        await apiGetWithoutAuthLogout('/api/v1/users/me');
      } catch (err) {
        if (isMissingBackendProfile(err)) {
          navigate('/register');
          return;
        }
        throw err;
      }
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Unable to sign in. Please check your credentials.');
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
      const firebaseUser = await loginWithGoogle();
      const baseName = firebaseUser.email?.split('@')[0]?.replace(/[^a-zA-Z0-9_]/g, '_') || 'user';
      const uidTail = firebaseUser.uid.slice(-6).replace(/[^a-zA-Z0-9_]/g, '');

      await registerBackendUser({
        username: `${baseName}_${uidTail}`,
        email: firebaseUser.email || null,
        bio: null,
      });

      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Google sign-in failed. Please try again.');
      console.error(err);
    } finally {
      googleInFlightRef.current = false;
    }
  };

  return (
    <div className="auth-page">
      <section className="auth-panel glass-panel">
        <div className="hero-badge">Sign In</div>
        <h2>Welcome back</h2>
        <p>Sign in with your Firebase account to continue.</p>
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
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              name="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              required
            />
          </label>
          {error && <p className="form-error">{error}</p>}

          <button className="primary-button" type="submit" disabled={Boolean(configError)}>
            Sign In
          </button>
          <button type="button" className="secondary-button" onClick={handleGoogleSignIn} disabled={Boolean(configError)}>
            Continue with Google
          </button>
        </form>

        <div className="divider-row">
          <span className="divider-label">or</span>
        </div>

        <div className="phone-auth-block">
          <h3 className="auth-subtitle">Sign in with phone</h3>

          {phoneStep === 'enter' ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void startPhoneOtp();
              }}
              className="phone-auth-form"
            >
              <label>
                Phone number (with country code)
                <input
                  type="tel"
                  name="phoneNumber"
                  value={phoneNumber}
                  onChange={(event) => setPhoneNumber(event.target.value)}
                  placeholder="+14155552671"
                  required
                />
              </label>

              <div id="phone-recaptcha-container" />

              <button className="primary-button" type="submit" disabled={Boolean(configError) || otpSending}>
                {otpSending ? 'Sending OTP...' : 'Send OTP'}
              </button>
            </form>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void verifyPhoneOtp();
              }}
              className="phone-auth-form"
            >
              <label>
                Enter OTP
                <input
                  type="text"
                  name="otp"
                  value={otp}
                  onChange={(event) => setOtp(event.target.value)}
                  placeholder="123456"
                  required
                />
              </label>

              <div className="phone-actions">
                <button className="primary-button" type="submit" disabled={Boolean(configError) || otpVerifying}>
                  {otpVerifying ? 'Verifying...' : 'Verify & Sign In'}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={otpVerifying}
                  onClick={() => {
                    setPhoneStep('enter');
                    setOtp('');
                    setConfirmation(null);
                  }}
                >
                  Change number
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="small-note">
          Don’t have an account? <Link to="/register">Create one.</Link>
        </p>
      </section>
    </div>
  );
}

export default Login;
