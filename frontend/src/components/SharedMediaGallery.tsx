import React, { useState, useEffect } from 'react';
import { apiPost, apiGet } from '../lib/api';

interface SharedMediaGalleryProps {
  receiverId: string;
  conversationId: string;
}

export function SharedMediaGallery({ receiverId, conversationId }: SharedMediaGalleryProps) {
  const [galleries, setGalleries] = useState<any[]>([]);
  const [selectedGallery, setSelectedGallery] = useState<string | null>(null);
  const [media, setMedia] = useState<any[]>([]);
  const [title, setTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  async function createGallery() {
    if (!title.trim()) return;
    try {
      const response = await apiPost(`/api/v1/chats/${receiverId}/galleries`, { title });
      setGalleries((prev) => [...prev, response]);
      setTitle('');
    } catch (err) {
      console.error('Gallery creation error:', err);
    }
  }

  async function loadGalleryMedia(galleryId: string) {
    try {
      const response = await apiGet(`/api/v1/chats/galleries/${galleryId}/media`);
      setMedia(response.media || []);
    } catch (err) {
      console.error('Failed to load media:', err);
    }
  }

  return (
    <div className="shared-media-gallery">
      <div className="gallery-header">
        <h3>📸 Shared Media</h3>
        <button
          onClick={() => setIsCreating(!isCreating)}
          className="create-gallery-btn"
        >
          + New Gallery
        </button>
      </div>

      {isCreating && (
        <div className="create-gallery-form">
          <input
            type="text"
            placeholder="Gallery name"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <button onClick={createGallery} disabled={!title.trim()}>
            Create
          </button>
        </div>
      )}

      <div className="gallery-list">
        {galleries.map((gallery) => (
          <button
            key={gallery.gallery_id}
            onClick={() => {
              setSelectedGallery(gallery.gallery_id);
              loadGalleryMedia(gallery.gallery_id);
            }}
            className={`gallery-item ${selectedGallery === gallery.gallery_id ? 'active' : ''}`}
          >
            {gallery.title} ({gallery.media_count})
          </button>
        ))}
      </div>

      {selectedGallery && (
        <div className="gallery-media-grid">
          {media.map((item) => (
            <div key={item.item_id} className="gallery-media-item">
              {item.media_type?.startsWith('image') ? (
                <img src={item.media_url} alt="Media" className="gallery-image" />
              ) : (
                <video src={item.media_url} className="gallery-video" controls />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
