import { useEffect, useRef, useState, useCallback } from "react";
import type { Note } from "../types";

interface Props {
  notes: Note[];
  onChange: (notes: Note[]) => void;
}

const NOTE_HEIGHT = 12;
const PPS = 80; // pixels per second
const MIN_PITCH = 40;
const MAX_PITCH = 90;

export function PianoRoll({ notes, onChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [width, setWidth] = useState(800);
  const [height] = useState((MAX_PITCH - MIN_PITCH + 1) * NOTE_HEIGHT);

  const notesRef = useRef(notes);
  useEffect(() => {
    notesRef.current = notes;
  }, [notes]);

  const getNoteId = (note: Note, index: number) => `${note.pitch}-${note.start}-${index}`;

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = "#e0e0e0";
    ctx.lineWidth = 1;

    // Horizontal pitch lines
    for (let pitch = MIN_PITCH; pitch <= MAX_PITCH; pitch++) {
      const y = (MAX_PITCH - pitch) * NOTE_HEIGHT;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Vertical time lines (per second)
    const maxTime = Math.max(5, ...notesRef.current.map((n) => n.end));
    for (let t = 0; t <= maxTime; t += 1) {
      const x = t * PPS;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // Draw notes
    notesRef.current.forEach((note, idx) => {
      const id = getNoteId(note, idx);
      const x = note.start * PPS;
      const y = (MAX_PITCH - note.pitch) * NOTE_HEIGHT + 1;
      const w = Math.max(2, (note.end - note.start) * PPS);
      const h = NOTE_HEIGHT - 2;

      ctx.fillStyle = selectedIds.has(idx) ? "#ff7043" : "#42a5f5";
      ctx.fillRect(x, y, w, h);

      // Resize handle
      ctx.fillStyle = "#1e88e5";
      ctx.fillRect(x + w - 4, y, 4, h);
    });
  }, [selectedIds, width, height]);

  useEffect(() => {
    draw();
  }, [draw, notes]);

  // Mouse interaction state
  const dragRef = useRef<{
    mode: "none" | "move" | "resize";
    index: number;
    startX: number;
    startY: number;
    origNote: Note;
  }>({ mode: "none", index: -1, startX: 0, startY: 0, origNote: notes[0] });

  const hitTest = (x: number, y: number): { index: number; resize: boolean } | null => {
    // Iterate in reverse to select top notes first
    for (let i = notesRef.current.length - 1; i >= 0; i--) {
      const note = notesRef.current[i];
      const nx = note.start * PPS;
      const ny = (MAX_PITCH - note.pitch) * NOTE_HEIGHT + 1;
      const nw = Math.max(2, (note.end - note.start) * PPS);
      const nh = NOTE_HEIGHT - 2;
      if (x >= nx && x <= nx + nw && y >= ny && y <= ny + nh) {
        const resize = x >= nx + nw - 6;
        return { index: i, resize };
      }
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const hit = hitTest(x, y);

    if (hit) {
      const newSelected = new Set([hit.index]);
      setSelectedIds(newSelected);
      dragRef.current = {
        mode: hit.resize ? "resize" : "move",
        index: hit.index,
        startX: x,
        startY: y,
        origNote: { ...notesRef.current[hit.index] },
      };
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragRef.current.mode === "none") return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - dragRef.current.startX;
    const dy = y - dragRef.current.startY;
    const idx = dragRef.current.index;
    const orig = dragRef.current.origNote;

    const newNotes = [...notesRef.current];
    if (dragRef.current.mode === "move") {
      const dPitch = Math.round(-dy / NOTE_HEIGHT);
      const dTime = dx / PPS;
      newNotes[idx] = {
        ...orig,
        pitch: Math.min(MAX_PITCH, Math.max(MIN_PITCH, orig.pitch + dPitch)),
        start: Math.max(0, orig.start + dTime),
        end: Math.max(orig.start + dTime + 0.1, orig.end + dTime),
      };
    } else if (dragRef.current.mode === "resize") {
      const dTime = dx / PPS;
      newNotes[idx] = {
        ...orig,
        end: Math.max(orig.start + 0.1, orig.end + dTime),
      };
    }

    onChange(newNotes);
  };

  const handleMouseUp = () => {
    dragRef.current = { mode: "none", index: -1, startX: 0, startY: 0, origNote: notesRef.current[0] };
  };

  const handleDoubleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (hitTest(x, y)) return;

    const start = Math.max(0, x / PPS);
    const pitch = Math.min(MAX_PITCH, Math.max(MIN_PITCH, MAX_PITCH - Math.floor(y / NOTE_HEIGHT)));
    const newNote: Note = {
      pitch,
      start,
      end: start + 0.5,
      velocity: 80,
      instrument: 0,
    };
    onChange([...notes, newNote]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === "Delete" || e.key === "Backspace") && selectedIds.size > 0) {
      const newNotes = notes.filter((_, idx) => !selectedIds.has(idx));
      onChange(newNotes);
      setSelectedIds(new Set());
    }
  };

  return (
    <div style={{ marginBottom: 16 }} onKeyDown={handleKeyDown} tabIndex={0}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ border: "1px solid #999", cursor: "crosshair", display: "block" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={handleDoubleClick}
      />
      <p style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
        Click to select · Drag to move · Drag right edge to resize · Double-click empty area to add · Delete to remove
      </p>
    </div>
  );
}
