import { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  ArrowRight,
  BriefcaseBusiness,
  CalendarCheck,
  CalendarDays,
  CheckCircle2,
  Clock,
  Filter,
  Mail,
  MapPin,
  Phone,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  Users
} from "lucide-react";

import { api } from "./api";
import type { Appointment, Dashboard, Service, Settings as BusinessSettings, Staff } from "./types";
import { appointmentLabel, money, readableDate, serviceSummary, statusTone, todayIso, tomorrowIso } from "./utils";
import "./styles.css";

type View = "book" | "admin" | "services";

const statuses = ["Booked", "Confirmed", "Completed", "Cancelled", "No-show"];

function App() {
  const [view, setView] = useState<View>("book");
  const [settings, setSettings] = useState<BusinessSettings | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [selectedService, setSelectedService] = useState<number | "">("");
  const [selectedStaff, setSelectedStaff] = useState<number | "">("");
  const [selectedDate, setSelectedDate] = useState(tomorrowIso());
  const [slots, setSlots] = useState<string[]>([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [settingsData, servicesData, staffData, appointmentsData, dashboardData] = await Promise.all([
          api<BusinessSettings>("/settings"),
          api<Service[]>("/services?active=true"),
          api<Staff[]>("/staff?active=true"),
          api<Appointment[]>("/appointments"),
          api<Dashboard>("/dashboard")
        ]);
        setSettings(settingsData);
        setServices(servicesData);
        setStaff(staffData);
        setAppointments(appointmentsData);
        setDashboard(dashboardData);
        const initialServiceId = selectedService || servicesData[0]?.id || "";
        if (!selectedService && initialServiceId) {
          setSelectedService(initialServiceId);
        }
        if (!selectedStaff && initialServiceId) {
          const firstCompatibleStaff = staffData.find((person) => person.services?.some((service) => service.id === initialServiceId));
          if (firstCompatibleStaff || staffData[0]) {
            setSelectedStaff((firstCompatibleStaff || staffData[0]).id);
          }
        }
        setError("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load ReserveHub data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [refreshKey]);

  useEffect(() => {
    async function loadSlots() {
      if (!selectedService || !selectedStaff || !selectedDate) {
        setSlots([]);
        return;
      }
      try {
        const data = await api<{ slots: string[] }>(`/slots?service_id=${selectedService}&staff_id=${selectedStaff}&appointment_date=${selectedDate}`);
        setSlots(data.slots);
        setSelectedSlot(data.slots[0] || "");
      } catch {
        setSlots([]);
        setSelectedSlot("");
      }
    }
    loadSlots();
  }, [selectedService, selectedStaff, selectedDate, refreshKey]);

  const staffForService = useMemo(() => {
    if (!selectedService) return staff;
    return staff.filter((person) => person.services?.some((service) => service.id === selectedService));
  }, [staff, selectedService]);

  const filteredAppointments = useMemo(() => {
    return appointments.filter((item) => {
      const matchesSearch = !search || [item.customer_name, item.customer_email, item.service_name, item.staff_name].join(" ").toLowerCase().includes(search.toLowerCase());
      const matchesStatus = !statusFilter || item.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [appointments, search, statusFilter]);

  const selectedServiceRecord = services.find((service) => service.id === selectedService);
  const selectedStaffRecord = staff.find((person) => person.id === selectedStaff);

  async function book(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedService || !selectedStaff || !selectedSlot) {
      setError("Choose a service, staff member, date, and time.");
      return;
    }
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const created = await api<Appointment>("/appointments", {
        method: "POST",
        body: JSON.stringify({
          customer_name: form.get("customer_name"),
          customer_email: form.get("customer_email"),
          customer_phone: form.get("customer_phone"),
          service_id: selectedService,
          staff_id: selectedStaff,
          appointment_date: selectedDate,
          start_time: selectedSlot,
          notes: form.get("notes") || null
        })
      });
      setSuccess(`Appointment booked for ${readableDate(created.appointment_date)} at ${created.start_time}.`);
      setError("");
      event.currentTarget.reset();
      setRefreshKey((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Booking failed");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(appointment: Appointment, status: string) {
    try {
      await api(`/appointments/${appointment.id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
      setRefreshKey((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Status update failed");
    }
  }

  async function restoreSampleRecords() {
    if (!confirm("Restore ReserveHub sample records? This will replace current local records.")) return;
    await api("/admin/restore-sample-records", { method: "POST" });
    setSuccess("ReserveHub sample records restored.");
    setRefreshKey((value) => value + 1);
  }

  return (
    <main>
      <header className="hero-shell">
        <nav className="top-nav" aria-label="Primary navigation">
          <a className="brand" href="#"><span>RH</span>ReserveHub</a>
          <div className="nav-actions">
            <button className={view === "book" ? "active" : ""} onClick={() => setView("book")}>Book</button>
            <button className={view === "admin" ? "active" : ""} onClick={() => setView("admin")}>Schedule</button>
            <button className={view === "services" ? "active" : ""} onClick={() => setView("services")}>Services</button>
          </div>
        </nav>

        <section className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow"><Sparkles size={16} /> Appointment booking for service businesses</p>
            <h1>Scheduling workspace for service teams.</h1>
            <p>ReserveHub connects customer bookings, services, staff availability, appointment status, and business metrics in one clean full-stack workflow.</p>
            <div className="hero-pills">
              <span><CalendarCheck size={16} /> {dashboard?.upcoming_appointments ?? "-"} upcoming</span>
              <span><BriefcaseBusiness size={16} /> {services.length || "-"} services</span>
              <span><Users size={16} /> {staff.length || "-"} staff</span>
            </div>
          </div>
          <aside className="business-card">
            <b>{settings?.business_name || "ReserveHub Studio"}</b>
            <p>{settings?.booking_notice || "Appointments are confirmed after review."}</p>
            <span><MapPin size={16} /> {settings?.address || "Tbilisi"}</span>
            <span><Phone size={16} /> {settings?.phone || "+1 555 014 2086"}</span>
            <span><Mail size={16} /> {settings?.email || "hello@reservehub.local"}</span>
          </aside>
        </section>
      </header>

      {loading && <p className="state">Loading schedule data...</p>}
      {error && <p className="alert error" role="alert"><AlertCircle size={18} /> {error}</p>}
      {success && <p className="alert success" role="status"><CheckCircle2 size={18} /> {success}</p>}

      {view === "book" && (
        <section className="booking-layout" aria-labelledby="booking-title">
          <div className="booking-main">
            <div className="section-title">
              <p className="eyebrow"><CalendarDays size={16} /> Online booking</p>
              <h2 id="booking-title">Choose a service and reserve a time.</h2>
            </div>
            <div className="service-grid">
              {services.map((service) => (
                <button
                  className={`service-card color-${service.color} ${selectedService === service.id ? "selected" : ""}`}
                  key={service.id}
                  onClick={() => {
                    setSelectedService(service.id);
                    const firstStaff = staff.find((person) => person.services?.some((item) => item.id === service.id));
                    if (firstStaff) setSelectedStaff(firstStaff.id);
                  }}
                >
                  <span>{service.category}</span>
                  <strong>{service.name}</strong>
                  <small>{service.description}</small>
                  <b>{serviceSummary(service)}</b>
                </button>
              ))}
            </div>
          </div>

          <aside className="booking-panel">
            <h3>Booking details</h3>
            <form onSubmit={book}>
              <label>Staff member
                <select value={selectedStaff} onChange={(event) => setSelectedStaff(Number(event.target.value))}>
                  {staffForService.map((person) => <option value={person.id} key={person.id}>{person.name} - {person.role}</option>)}
                </select>
              </label>
              <label>Date
                <input type="date" min={todayIso()} value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
              </label>
              <div className="slot-grid" aria-label="Available times">
                {slots.length === 0 ? <p className="empty">No available times for this selection.</p> : slots.slice(0, 12).map((slot) => (
                  <button className={selectedSlot === slot ? "selected" : ""} type="button" key={slot} onClick={() => setSelectedSlot(slot)}>{slot}</button>
                ))}
              </div>
              <input name="customer_name" placeholder="Full name" required />
              <input name="customer_email" type="email" placeholder="Email" required />
              <input name="customer_phone" placeholder="Phone" required />
              <textarea name="notes" placeholder="Notes for the appointment" rows={3}></textarea>
              <button className="primary" disabled={saving || !selectedSlot}>{saving ? "Booking..." : "Book appointment"} <ArrowRight size={16} /></button>
            </form>
            {selectedServiceRecord && selectedStaffRecord && (
              <div className="summary-box">
                <b>{selectedServiceRecord.name}</b>
                <span>{selectedStaffRecord.name}</span>
                <span>{selectedDate} at {selectedSlot || "choose time"}</span>
                <strong>{money(selectedServiceRecord.price)}</strong>
              </div>
            )}
          </aside>
        </section>
      )}

      {view === "admin" && (
        <section className="admin-layout">
          <div className="section-title">
            <p className="eyebrow"><Settings size={16} /> Schedule operations</p>
            <h2>Appointments, status, and daily capacity.</h2>
          </div>
          <div className="dashboard-row">
            <Stat label="Today" value={dashboard?.today_appointments ?? 0} />
            <Stat label="Upcoming" value={dashboard?.upcoming_appointments ?? 0} />
            <Stat label="Completed" value={dashboard?.completed_appointments ?? 0} />
            <Stat label="Completed revenue" value={money(dashboard?.completed_revenue ?? 0)} />
          </div>
          <div className="toolbar">
            <label><Search size={16} /><input placeholder="Search customer, service, staff..." value={search} onChange={(event) => setSearch(event.target.value)} /></label>
            <label><Filter size={16} /><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{statuses.map((status) => <option key={status}>{status}</option>)}</select></label>
            <button className="secondary" onClick={restoreSampleRecords}><RefreshCw size={16} /> Restore sample records</button>
          </div>
          <div className="appointment-list">
            {filteredAppointments.length === 0 ? <p className="empty">No appointments match the current filters.</p> : filteredAppointments.map((appointment) => (
              <article className="appointment-card" key={appointment.id}>
                <div>
                  <strong>{appointmentLabel(appointment)}</strong>
                  <span>{appointment.service_name} with {appointment.staff_name}</span>
                  <small>{readableDate(appointment.appointment_date)} - {appointment.customer_email}</small>
                </div>
                <Badge text={appointment.status} />
                <select value={appointment.status} onChange={(event) => changeStatus(appointment, event.target.value)}>
                  {statuses.map((status) => <option key={status}>{status}</option>)}
                </select>
              </article>
            ))}
          </div>
          <div className="activity-panel">
            <h3>Recent activity</h3>
            {dashboard?.recent_activity.map((item) => <p key={item.id}><b>{item.event_type}</b> {item.description}</p>)}
          </div>
        </section>
      )}

      {view === "services" && (
        <section className="services-page">
          <div className="section-title">
            <p className="eyebrow"><BriefcaseBusiness size={16} /> Service catalog</p>
            <h2>Services and staff coverage.</h2>
          </div>
          <div className="catalog-grid">
            {services.map((service) => (
              <article className={`catalog-card color-${service.color}`} key={service.id}>
                <span>{service.category}</span>
                <h3>{service.name}</h3>
                <p>{service.description}</p>
                <b>{serviceSummary(service)}</b>
              </article>
            ))}
          </div>
          <div className="staff-grid">
            {staff.map((person) => (
              <article className="staff-card" key={person.id}>
                <h3>{person.name}</h3>
                <strong>{person.role}</strong>
                <p>{person.bio}</p>
                <div>{person.services?.map((service) => <span key={service.id}>{service.name}</span>)}</div>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return <span className="stat"><small>{label}</small><b>{value}</b></span>;
}

function Badge({ text }: { text: string }) {
  return <span className={`badge ${statusTone(text)}`}>{text}</span>;
}

createRoot(document.getElementById("root")!).render(<App />);
