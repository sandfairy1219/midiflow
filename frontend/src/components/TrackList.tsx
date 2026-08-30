import type { Track } from "../types";
import { audioUrl } from "../api";

interface Props {
  projectId: string;
  tracks: Track[];
}

export function TrackList({ projectId, tracks }: Props) {
  if (tracks.length === 0) return <p className="muted">No tracks yet.</p>;

  return (
    <div className="card">
      <h3>Tracks</h3>
      <div className="track-list">
        {tracks.map((track) => {
          const filename = track.path.split("\\").pop()?.split("/").pop() || "";
          return (
            <div key={track.track_id} className="track-item">
              <span className="track-name">{track.name}</span>
              <span className="track-type">{track.type}</span>
              {track.type === "audio" && (
                <audio controls src={audioUrl(projectId, filename)} />
              )}
              {track.type === "midi" && (
                <span className="muted" style={{ flex: 1 }}>{filename}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
