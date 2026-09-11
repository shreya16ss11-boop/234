import { describe, expect, it } from "vitest";

import { appointmentLabel, money, serviceSummary, statusTone } from "./utils";

describe("ReserveHub helpers", () => {
  it("formats money", () => {
    expect(money(120)).toBe("$120.00");
  });

  it("summarizes services", () => {
    expect(serviceSummary({ id: 1, name: "Consult", category: "Business", description: "Planning", duration_minutes: 60, price: 150, active: true, color: "blue" })).toBe("60 min - $150.00");
  });

  it("maps status tones", () => {
    expect(statusTone("Completed")).toBe("positive");
    expect(statusTone("Cancelled")).toBe("danger");
    expect(statusTone("Booked")).toBe("info");
  });

  it("builds appointment labels", () => {
    expect(appointmentLabel({ id: 1, customer_name: "Ana", customer_email: "a@b.com", customer_phone: "1", service_id: 1, staff_id: 1, appointment_date: "2026-07-29", start_time: "09:00", end_time: "10:00", status: "Booked", service_name: "Consult", staff_name: "Mariam", staff_role: "Consultant", price: 120, duration_minutes: 60 })).toContain("Ana");
  });
});
