import React, { useState, useEffect } from 'react';
import { apiGet, apiPost } from '../lib/api';

interface TranslateMessageProps {
  messageId: string;
  sourceText: string;
}

export function TranslateMessage({ messageId, sourceText }: TranslateMessageProps) {
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [selectedLang, setSelectedLang] = useState<string>('es'); // Default Spanish
  const [loading, setLoading] = useState(false);

  const languages: Record<string, string> = {
    es: 'Spanish',
    fr: 'French',
    de: 'German',
    ja: 'Japanese',
    zh: 'Chinese',
    pt: 'Portuguese',
    hi: 'Hindi',
    ru: 'Russian',
  };

  async function handleTranslate(targetLang: string) {
    if (translations[targetLang]) {
      setSelectedLang(targetLang);
      return;
    }

    try {
      setLoading(true);
      // In real implementation, call a translation API
      const mockTranslation = `[${languages[targetLang]} translation of]: ${sourceText}`;
      
      await apiPost(`/api/v1/chats/messages/${messageId}/translate`, {
        target_language: targetLang,
        translated_text: mockTranslation,
      });

      setTranslations((prev) => ({ ...prev, [targetLang]: mockTranslation }));
      setSelectedLang(targetLang);
    } catch (err) {
      console.error('Translation error:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="translate-message">
      <div className="translate-languages">
        {Object.entries(languages).map(([code, name]) => (
          <button
            key={code}
            onClick={() => handleTranslate(code)}
            className={`translate-btn ${selectedLang === code ? 'active' : ''}`}
            title={`Translate to ${name}`}
          >
            {code.toUpperCase()}
          </button>
        ))}
      </div>
      {selectedLang && translations[selectedLang] && (
        <div className="translate-result">
          <p className="translate-label">{languages[selectedLang]} Translation:</p>
          <p className="translate-text">{translations[selectedLang]}</p>
        </div>
      )}
    </div>
  );
}
