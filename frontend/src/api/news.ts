import { get } from "./client";
import type { NewsItem, SentimentSummary } from "../types";

export const fetchNews = (days = 7, topic?: string) => {
  const params = new URLSearchParams({ days: String(days) });
  if (topic) params.set("topic", topic);
  return get<NewsItem[]>(`/api/v1/news/?${params}`);
};

export const fetchSentimentSummary = (days = 7) =>
  get<SentimentSummary[]>(`/api/v1/news/sentiment-summary?days=${days}`);
