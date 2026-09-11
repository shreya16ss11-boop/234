import type { Appointment, Service } from "./types";

export function money(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export function readableDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function tomorrowIso(offset = 1): string {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

export function serviceSummary(service: Service): string {
  return `${service.duration_minutes} min - ${money(service.price)}`;
}

export function statusTone(status: string): string {
  const key = status.toLowerCase();
  if (key === "confirmed" || key === "completed") return "positive";
  if (key === "cancelled" || key === "no-show") return "danger";
  if (key === "booked") return "info";
  return "neutral";
}

export function appointmentLabel(appointment: Appointment): string {
  return `${appointment.start_time}-${appointment.end_time} ${appointment.customer_name}`;
}
