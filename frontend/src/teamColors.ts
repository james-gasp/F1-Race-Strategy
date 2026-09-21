export const TEAM_COLORS: Record<string, string> = {
  "Red Bull Racing": "#3671C6",
  "Red Bull": "#3671C6",
  Mercedes: "#27F4D2",
  Ferrari: "#E8002D",
  McLaren: "#FF8000",
  "Aston Martin": "#229971",
  Alpine: "#FF87BC",
  Williams: "#64C4FF",
  "Kick Sauber": "#52E252",
  "Alfa Romeo": "#52E252",
  RB: "#6692FF",
  AlphaTauri: "#6692FF",
  Haas: "#B6BABD",
  "Haas F1 Team": "#B6BABD",
};

export function teamColor(team: string | undefined | null): string {
  if (!team) return "#8891a3";
  return TEAM_COLORS[team] ?? "#8891a3";
}
