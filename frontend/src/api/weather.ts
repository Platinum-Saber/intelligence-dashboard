import { get } from "./client";
import type { WeatherLatest } from "../types";

export const fetchWeatherLatest = () => get<WeatherLatest[]>("/api/v1/weather/latest");
export const fetchHighRisk = () => get<WeatherLatest[]>("/api/v1/weather/high-risk");
