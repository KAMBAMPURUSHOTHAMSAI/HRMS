
import { useCallback, useEffect, useState } from "react";
import { Download, RefreshCw } from "lucide-react";
import {
  downloadSalarySlip,
  getAllSalarySlips,
  getMySalarySlips,
} from "../../../api/salarySlipApi";

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 10);
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function getDownloadFilename(disposition, fallback) {
  if (!disposition) return fallback;

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);

  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/"/g, ""));
    } catch {
      // Use the ordinary filename below if decoding fails.
    }
  }

  const ordinaryMatch = disposition.match(/filename="?([^";]+)"?/i);

  return ordinaryMatch?.[1] || fallback;
}

export default function MySalarySlips({ mode = "employee" }) {
  const isAdmin = mode === "admin";

  const [slips, setSlips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadSlips = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = isAdmin
        ? await getAllSalarySlips()
        : await getMySalarySlips();

      setSlips(getArray(response));
    } catch (err) {
      setSlips([]);
      setError(
        err.response?.data?.detail ||
          "Unable to load salary slips."
      );
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    loadSlips();
  }, [loadSlips]);

  async function handleDownload(slip) {
    setDownloadingId(slip.id);
    setError("");
    setMessage("");

    let objectUrl;

    try {
      const result = await downloadSalarySlip(slip.id);

      if (!(result.blob instanceof Blob) || result.blob.size === 0) {
        throw new Error("The downloaded PDF file is empty.");
      }

      objectUrl = URL.createObjectURL(result.blob);

      const fallbackName =
        slip.file_name || `salary-slip-${slip.id}.pdf`;

      const filename = getDownloadFilename(
        result.contentDisposition,
        fallbackName
      );

      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage(`Download requested for ${filename}.`);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to download the salary slip."
      );
    } finally {
      if (objectUrl) {
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      }

      setDownloadingId(null);
    }
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">
            {isAdmin ? "Salary Slip Management" : "My Salary Slips"}
          </h2>

          <p className="text-muted mb-0">
            {isAdmin
              ? "View and download available employee salary slips."
              : "View and download your generated salary slip PDFs."}
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadSlips}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Available Salary Slips</h5>

          {loading ? (
            <p>Loading salary slips...</p>
          ) : slips.length === 0 ? (
            <p className="text-muted mb-0">
              No salary slips are available yet.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Slip ID</th>
                    {isAdmin && <th>Employee</th>}
                    <th>Payroll Record</th>
                    <th>PDF File</th>
                    <th>Generated At</th>
                    <th>Download</th>
                  </tr>
                </thead>

                <tbody>
                  {slips.map((slip) => {
                    const employeeName =
                      slip.employee_name ||
                      slip.payroll_record?.employee_name ||
                      slip.employee?.full_name ||
                      "—";

                    return (
                      <tr key={slip.id}>
                        <td>{slip.id}</td>

                        {isAdmin && (
                          <td>
                            <div>{employeeName}</div>

                            {slip.employee_code && (
                              <small className="text-muted">
                                {slip.employee_code}
                              </small>
                            )}
                          </td>
                        )}

                        <td>{slip.payroll_record_id ?? "—"}</td>

                        <td>{slip.file_name || "Salary Slip PDF"}</td>

                        <td>{formatDate(slip.generated_at)}</td>

                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            onClick={() => handleDownload(slip)}
                            disabled={downloadingId === slip.id}
                          >
                            <Download size={15} className="me-1" />
                            {downloadingId === slip.id
                              ? "Downloading..."
                              : "Download PDF"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
