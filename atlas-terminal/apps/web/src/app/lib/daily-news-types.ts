export interface FTHeadline {
  url: string;
  title_en: string;
  title_ko?: string | null;
  lede_en?: string | null;
  lede_ko?: string | null;
  section?: string | null;
  published_at: string;
  image?: string | null;
}

export interface FTBookmark extends FTHeadline {
  date_key: string;
  saved_at: string;
}
