import React, { useRef } from 'react';

// A bare <video> paused at time 0 renders as a black box in most browsers —
// no frame has been decoded yet. Seeking a hair forward once metadata loads
// forces a real frame to paint, giving a "poster" for free with no server-side
// thumbnail generation (preload="metadata" keeps this to a small byte range,
// not the whole video).
const ExploreThumbnail = ({ src }) => {
  const videoRef = useRef(null);

  const handleLoadedMetadata = () => {
    const v = videoRef.current;
    if (v) v.currentTime = Math.min(0.5, (v.duration || 1) / 2);
  };

  return (
    <video
      ref={videoRef}
      src={src}
      preload="metadata"
      muted
      playsInline
      onLoadedMetadata={handleLoadedMetadata}
      className="w-full h-full object-cover"
    />
  );
};

export default ExploreThumbnail;
