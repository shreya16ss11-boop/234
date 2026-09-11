export type Service = {
  id: number;
  name: string;
  category: string;
  description: string;
  duration_minutes: number;
  price: number;
  active: number | boolean;
  color: string;
};

export type Staff = {
  id: number;
  name: string;
  role: string;
  email: string;
  phone: string;
  active: number | boolean;
  bio: string;
  services?: Service[];
};

export type Appointment = {
  id: number;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  service_id: number;
  staff_id: number;
  appointment_date: string;
  start_time: string;
  end_time: string;
  status: string;
  notes?: string;
  service_name: string;
  staff_name: string;
  staff_role: string;
  price: number;
  duration_minutes: number;
  activity?: Activity[];
};

export type Activity = {
  id: number;
  event_type: string;
  description: string;
  appointment_id?: number;
  created_at: string;
};

export type Dashboard = {
  today_appointments: number;
  upcoming_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  completed_revenue: number;
  status_counts: { status: string; count: number }[];
  service_mix: { name: string; count: number }[];
  recent_activity: Activity[];
};

export type Settings = {
  business_name: string;
  phone: string;
  email: string;
  address: string;
  timezone: string;
  booking_notice: string;
  slot_interval: number;
};
