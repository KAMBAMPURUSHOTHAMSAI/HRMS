
import { useEffect, useState } from "react";
import {
  BadgeCheck,
  Building2,
  CalendarDays,
  CheckCircle2,
  Mail,
  Phone,
  Save,
  ShieldCheck,
  UserRound,
  Wallet,
  BriefcaseBusiness,
  IdCard,
} from "lucide-react";

import {
  getMyEmployeeProfile,
  updateMyEmployeeProfile,
} from "../../../api/employeeApi";

import { useAuth } from "../../../hooks/useAuth";


function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}


function formatDate(value) {
  if (!value) return "—";

  const [year, month, day] = String(value).split("-");

  if (!year || !month || !day) return String(value);

  return `${day}-${month}-${year}`;
}


function initials(firstName, lastName) {
  const first = String(firstName || "").trim()[0] || "";
  const last = String(lastName || "").trim()[0] || "";

  return `${first}${last}`.toUpperCase() || "EM";
}


function InfoItem({ icon: Icon, label, value, positive }) {
  return (
    <div className="hr-info-item">
      <span className="hr-info-icon">
        <Icon size={17} />
      </span>

      <div className="hr-info-content">
        <span>{label}</span>
        <strong
          className={
            positive === true
              ? "hr-value-positive"
              : positive === false
                ? "hr-value-inactive"
                : ""
          }
        >
          {value || "—"}
        </strong>
      </div>
    </div>
  );
}


export default function MyProfile() {
  const { user, updateAuthenticatedUser } = useAuth();

  const [profile, setProfile] = useState(null);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      setLoading(true);
      setError("");

      try {
        const data = await getMyEmployeeProfile();

        if (cancelled) return;

        setProfile(data);

        setForm({
          first_name: data.first_name || "",
          last_name: data.last_name || "",
          phone: data.phone || "",
        });
      } catch (err) {
        if (cancelled) return;

        setError(
          err.response?.data?.detail ||
            "Unable to load your profile."
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));

    setSuccess("");
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updatedProfile = await updateMyEmployeeProfile({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim() || null,
      });

      setProfile(updatedProfile);

      setForm({
        first_name: updatedProfile.first_name || "",
        last_name: updatedProfile.last_name || "",
        phone: updatedProfile.phone || "",
      });

      updateAuthenticatedUser?.({
        first_name: updatedProfile.first_name,
        last_name: updatedProfile.last_name,
      });

      setSuccess("Your profile has been updated successfully.");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to update your profile. Please try again."
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="page-loading" role="status">
        Loading your profile...
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="dashboard-page">
        <div className="page-heading-row">
          <div>
            <p className="section-kicker">MY ACCOUNT</p>
            <h2>My Profile</h2>
          </div>
        </div>

        <div className="alert alert-warning" role="alert">
          {error || "Employee profile is not available."}
        </div>
      </div>
    );
  }

  const fullName =
    `${profile.first_name || ""} ${profile.last_name || ""}`.trim() ||
    "Employee";

  const active = Boolean(profile.is_active);

  return (
    <div className="dashboard-page hr-my-profile">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">MY ACCOUNT</p>
          <h2>My Profile</h2>
          <p>
            Manage your personal information and review your employment details.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {success && (
        <div className="alert alert-success" role="status">
          <CheckCircle2 size={17} className="me-2" />
          {success}
        </div>
      )}

      <section className="hr-profile-hero">
        <div className="hr-profile-hero-main">
          <div className="hr-profile-avatar" aria-hidden="true">
            {initials(profile.first_name, profile.last_name)}
          </div>

          <div className="hr-profile-identity">
            <div className="hr-profile-eyebrow">
              <BadgeCheck size={15} />
              Employee profile
            </div>

            <h2>{fullName}</h2>

            <p>
              {profile.designation_name || "Employee"}
              {profile.department_name
                ? ` · ${profile.department_name}`
                : ""}
            </p>

            <div className="hr-profile-meta">
              <span className="hr-profile-code">
                <IdCard size={14} />
                {profile.employee_code || "Code unavailable"}
              </span>

              <span
                className={`status-pill ${
                  active ? "status-active" : "status-inactive"
                }`}
              >
                {active ? "Active employee" : "Inactive employee"}
              </span>
            </div>

            <div className="hr-profile-contact-row">
              <span className="hr-profile-contact">
                <Mail size={15} />
                {profile.email || user?.email || "Email unavailable"}
              </span>

              <span className="hr-profile-contact">
                <Phone size={15} />
                {profile.phone || "Phone not added"}
              </span>
            </div>
          </div>
        </div>

        <div className="hr-profile-hero-side">
          <span>Account status</span>
          <strong>
            <ShieldCheck
              size={16}
              style={{ display: "inline", marginRight: 6 }}
            />
            {active ? "Account active" : "Account inactive"}
          </strong>

          <span style={{ marginTop: 15 }}>Employee since</span>
          <strong>{formatDate(profile.joining_date)}</strong>
        </div>
      </section>

      <div className="hr-profile-layout">
        <section className="content-card hr-profile-edit-card">
          <div className="hr-section-heading">
            <span className="hr-section-icon">
              <UserRound size={21} />
            </span>

            <div>
              <h3>Personal Information</h3>
              <p>
                Update your name and contact details.
              </p>
            </div>
          </div>

          <form
            className="hr-profile-form"
            onSubmit={handleSubmit}
          >
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="first_name">First Name *</label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  autoComplete="given-name"
                  value={form.first_name}
                  onChange={handleChange}
                  minLength={1}
                  maxLength={100}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="last_name">Last Name *</label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  autoComplete="family-name"
                  value={form.last_name}
                  onChange={handleChange}
                  minLength={1}
                  maxLength={100}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">Email Address</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={profile.email || user?.email || ""}
                  readOnly
                  aria-readonly="true"
                />
                <small>
                  Contact HR if your login email needs to change.
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="phone">Phone Number</label>
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  autoComplete="tel"
                  value={form.phone}
                  onChange={handleChange}
                  maxLength={20}
                  placeholder="Add your phone number"
                />
              </div>
            </div>

            <div className="form-actions">
              <button
                className="primary-button"
                type="submit"
                disabled={saving}
              >
                <Save size={17} />
                {saving ? "Saving changes..." : "Save Changes"}
              </button>
            </div>
          </form>
        </section>

        <section className="content-card hr-profile-employment-card">
          <div className="hr-section-heading">
            <span className="hr-section-icon">
              <BriefcaseBusiness size={21} />
            </span>

            <div>
              <h3>Employment Details</h3>
              <p>
                Your official work and compensation information.
              </p>
            </div>
          </div>

          <div className="hr-employment-grid">
            <InfoItem
              icon={IdCard}
              label="Employee Code"
              value={profile.employee_code}
            />

            <InfoItem
              icon={Building2}
              label="Department"
              value={profile.department_name}
            />

            <InfoItem
              icon={BriefcaseBusiness}
              label="Designation"
              value={profile.designation_name}
            />

            <InfoItem
              icon={CalendarDays}
              label="Joining Date"
              value={formatDate(profile.joining_date)}
            />

            <InfoItem
              icon={Wallet}
              label="Monthly Salary"
              value={formatCurrency(profile.monthly_salary)}
            />

            <InfoItem
              icon={ShieldCheck}
              label="Employment Status"
              value={profile.employment_status || (active ? "ACTIVE" : "INACTIVE")}
              positive={active}
            />
          </div>

          <div className="alert alert-info mt-4 mb-0">
            Employment information is maintained by your HR/Admin team.
            Contact HR if any official details need correction.
          </div>
        </section>
      </div>
    </div>
  );
}
