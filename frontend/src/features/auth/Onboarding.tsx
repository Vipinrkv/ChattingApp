import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../ui/Card';
import { Avatar } from '../../ui/Avatar';
import { Button } from '../../ui/Button';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState('');
  const [bio, setBio] = useState('');
  const navigate = useNavigate();

  const next = () => setStep((s) => s + 1);
  const prev = () => setStep((s) => Math.max(1, s - 1));

  return (
    <div className="onboarding-page">
      <Card>
        <h2>Welcome — Step {step} of 4</h2>

        {step === 1 && (
          <div>
            <p>Choose your avatar</p>
            <Avatar size={80} src="/assets/default-avatar.png" />
            <div className="onboarding-avatar-upload">
              <label>
                Upload avatar
                <input type="file" accept="image/*" aria-label="Upload avatar" />
              </label>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <p>Pick a username</p>
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
          </div>
        )}

        {step === 3 && (
          <div>
            <p>Tell us about yourself</p>
            <label>
              Your bio
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                rows={4}
                placeholder="Tell us a bit about yourself"
              />
            </label>
          </div>
        )}

        {step === 4 && (
          <div>
            <p>Suggested friends</p>
            <div className="suggestions-grid">Placeholder suggestions...</div>
          </div>
        )}

        <div className="onboarding-step-actions">
          {step > 1 && <Button variant="ghost" onClick={prev}>Back</Button>}
          {step < 4 && <Button onClick={next}>Next</Button>}
          {step === 4 && <Button onClick={() => navigate('/')}>Finish</Button>}
        </div>
      </Card>
    </div>
  );
}
