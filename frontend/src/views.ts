export const VIEWS = [
  { slug: "library", label: "Library" },
  { slug: "review", label: "Review" },
  { slug: "history", label: "History" },
  { slug: "members", label: "Members" },
] as const;

export type View = (typeof VIEWS)[number]["slug"];

export function isView(slug: string | undefined): slug is View {
  return VIEWS.some((view) => view.slug === slug);
}
