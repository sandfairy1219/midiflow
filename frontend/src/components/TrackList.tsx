import type { Track } from "../types";
import { audioUrl } from "../api";

interface Props {
  projectId: string;
  tracks: Track[];
}

export function TrackList({ projectId, tracks }: Props) {
  if (tracks.length === 0) return <p>No tracks yet.</p>;

  return (
    <div style={{ padding: 16, border: "1px solid #ccc", borderRadius: 8, marginBottom: 16 }}>
      <h3>Tracks</h3>
      {tracks.map((track) => {
        const filename = track.path.split("\\").pop()?.split("/").pop() || "";
        return (
          <div key={track.track_id} style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ minWidth: 120, fontWeight: "bold" }}>{track.name}</span>
            <span style={{ fontSize: 12, color: "#666" }}>({track.type})</span>
            {track.type === "audio" && (
              <audio controls src={audioUrl(projectId, filename)} style={{ flex: 1 }} />
            )}
            {track.type === "midi" && (
              <span style={{ flex: 1, fontSize: 12 }}>{filename}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
