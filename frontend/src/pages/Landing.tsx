import { Link } from 'react-router-dom';
import { useTheme } from '../ui/theme';

const features = [
  ['Messaging', 'Fast one-to-one conversations with media, replies, reactions, and read flow built in.'],
  ['Groups', 'Community rooms for public, private, and organization spaces.'],
  ['Communities', 'Shared spaces that keep people, topics, and context easy to scan.'],
  ['Social feed', 'A dense, modern stream for posts, trends, comments, likes, and reposts.'],
  ['Media sharing', 'Images, video, audio, documents, captions, and shared galleries.'],
  ['Realtime', 'Presence, typing, delivery states, and live conversation updates.'],
];

const trust = [
  ['Security', 'Protected authenticated routes and careful session handling.'],
  ['Privacy', 'Profile visibility, block controls, and account-level preferences.'],
  ['Encryption', 'Transport-ready architecture for private communication flows.'],
  ['Reliability', 'Stable loading states, cached feed data, and resilient UI fallbacks.'],
];

function Landing() {
  const { theme, toggle } = useTheme();

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <Link to="/" className="brand-block landing-brand" aria-label="ChattingApp home">
          <span className="brand-mark">C</span>
          <span className="brand-text">
            <strong>ChattingApp</strong>
            <span className="brand-sub">Social communication platform</span>
          </span>
        </Link>

        <nav className="landing-links" aria-label="Landing navigation">
          <a href="#features">Features</a>
          <a href="#trust">Trust</a>
          <a href="#contact">Contact</a>
        </nav>

        <div className="landing-actions">
          <button className="ghost-button compact-button" type="button" onClick={toggle} aria-label="Toggle theme">
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <Link className="secondary-button compact-button" to="/login">Sign in</Link>
          <Link className="primary-button compact-button" to="/register">Create account</Link>
        </div>
      </header>

      <main>
        <section className="landing-hero" id="top">
          <div className="landing-copy reveal-up">
            <span className="hero-label">Realtime social messaging</span>
            <h1>ChattingApp</h1>
            <p>
              A premium communication workspace for private chats, community rooms,
              social posts, and live media sharing.
            </p>
            <div className="hero-actions">
              <Link className="primary-button" to="/register">Start chatting</Link>
              <Link className="secondary-button" to="/login">I already have an account</Link>
            </div>
            <div className="hero-metrics" aria-label="Platform highlights">
              <span><strong>Live</strong> presence</span>
              <span><strong>Media</strong> ready</span>
              <span><strong>Mobile</strong> first</span>
            </div>
          </div>

          <div className="hero-visual reveal-up" aria-label="ChattingApp interface preview">
            <div className="visual-phone">
              <div className="visual-topline" />
              <div className="visual-message inbound">Morning sync at 10?</div>
              <div className="visual-message outbound">Yes, sending the notes now.</div>
              <div className="visual-media-grid">
                <span />
                <span />
                <span />
              </div>
              <div className="visual-composer">
                <span />
                <strong>Send</strong>
              </div>
            </div>
            <div className="visual-feed-card">
              <span className="pill soft">#community</span>
              <strong>Design team launched a new room</strong>
              <p>42 replies - 18 media items - live now</p>
            </div>
          </div>
        </section>

        <section className="landing-section" id="features">
          <div className="section-heading reveal-up">
            <span className="hero-label">Features</span>
            <h2>Everything a social chat platform needs, arranged for speed.</h2>
          </div>
          <div className="feature-grid">
            {features.map(([title, body]) => (
              <article className="feature-card reveal-up" key={title}>
                <span className="feature-icon" aria-hidden="true" />
                <h3>{title}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section trust-section" id="trust">
          <div className="section-heading reveal-up">
            <span className="hero-label">Trust</span>
            <h2>Private by posture, polished in the details.</h2>
          </div>
          <div className="trust-grid">
            {trust.map(([title, body]) => (
              <article className="trust-card reveal-up" key={title}>
                <h3>{title}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section contact-section" id="contact">
          <div className="section-heading reveal-up">
            <span className="hero-label">Contact</span>
            <h2>Support that is easy to find before and after sign in.</h2>
          </div>
          <div className="contact-grid">
            <a className="contact-card" href="mailto:support@chattingapp.local">support@chattingapp.local</a>
            <a className="contact-card" href="/help">Help center</a>
            <a className="contact-card" href="/status">System status</a>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <span>ChattingApp</span>
        <nav aria-label="Footer links">
          <a href="#features">Product</a>
          <a href="/terms">Terms</a>
          <a href="/privacy">Privacy</a>
          <a href="#contact">Contact</a>
        </nav>
      </footer>
    </div>
  );
}

export default Landing;
