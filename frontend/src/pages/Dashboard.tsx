//frontend/src/pages/Dashboard.tsx
import { apiGet } from '../lib/api';
import { useEffect, useState } from 'react';

let healthCheckPromise: Promise<unknown> | null = null;

function checkBackendHealth() {
  if (!healthCheckPromise) {
    healthCheckPromise = apiGet('/health').finally(() => {
      healthCheckPromise = null;
    });
  }

  return healthCheckPromise;
}

function Dashboard() {
  const [status, setStatus] = useState('Checking backend...');

  useEffect(() => {
    checkBackendHealth()
      .then(() => setStatus('Backend connected'))
      .catch(() => setStatus('Backend unreachable'));
  }, []);

  return (
    <div className="dashboard-grid">
      <section className="glass-panel hero-panel">
        <div className="hero-label">Welcome to the matrix</div>
        <h2>ChattingApp HQ</h2>
        <p>Fast social chat with futuristic style and flexible control.</p>
        <div className="status-pill">{status}</div>
      </section>
      <section className="glass-panel info-panel">
        <h3>Live channels</h3>
        <div className="widget-card">
          <span>Messages</span>
          <strong>72</strong>
        </div>
        <div className="widget-card">
          <span>Active friends</span>
          <strong>14</strong>
        </div>
        <div className="widget-card">
          <span>Group rooms</span>
          <strong>6</strong>
        </div>
      </section>
      <section className="glass-panel feed-panel">
        <h3>Trending feed</h3>
        <article>
          <p className="pill">#bluewave</p>
          <h4>Launch your next chatroom</h4>
          <p>Build a safe space with friends, follow communities, and keep the vibe alive.</p>
        </article>
        <article>
          <p className="pill">#cyberpulse</p>
          <h4>Dark mode, bright ideas</h4>
          <p>Switch themes on the fly, maintain focus, and move through notifications smoothly.</p>
        </article>
      </section>
    </div>
  );
}

export default Dashboard;
