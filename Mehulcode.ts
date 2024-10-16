private getMimeType(extension: string): string {
  switch (extension) {
    // Common video formats
    case 'mp4': return 'video/mp4';         // MPEG-4 Part 14
    case 'webm': return 'video/webm';       // WebM video
    case 'ogg': return 'video/ogg';         // Ogg video
    case 'ts': return 'video/mp2t';         // MPEG-2 Transport Stream
    case 'mkv': return 'video/x-matroska';  // Matroska video
    case 'mov': return 'video/quicktime';   // QuickTime video
    case 'avi': return 'video/x-msvideo';   // AVI (Microsoft)
    case 'wmv': return 'video/x-ms-wmv';    // Windows Media Video
    case 'flv': return 'video/x-flv';       // Flash Video
    case '3gp': return 'video/3gpp';        // 3GP video container
    case 'm4v': return 'video/x-m4v';       // iTunes video
    case 'm3u8': return 'application/vnd.apple.mpegurl';  // HTTP Live Streaming (HLS)
    case 'mpd': return 'application/dash+xml';  // MPEG-DASH Streaming

    // Common audio formats
    case 'mp3': return 'audio/mpeg';        // MP3 audio
    case 'wav': return 'audio/wav';         // Waveform Audio
    case 'ogg': return 'audio/ogg';         // Ogg audio
    case 'aac': return 'audio/aac';         // Advanced Audio Coding
    case 'flac': return 'audio/flac';       // Free Lossless Audio Codec
    case 'm4a': return 'audio/x-m4a';       // MPEG-4 Audio
    case 'wma': return 'audio/x-ms-wma';    // Windows Media Audio
    case 'opus': return 'audio/opus';       // Opus audio codec

    // Fallback for unknown formats
    default: return '';
  }
}